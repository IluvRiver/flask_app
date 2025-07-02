from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import socket
import redis
import json
from datetime import datetime
import logging
import os
import time
import threading

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수로 우선순위 결정 (GCP: primary, AWS: secondary)
PREFERRED_CLOUD = os.getenv('PREFERRED_CLOUD', 'GCP')

class CloudProvider:
    """클라우드 제공업체별 설정 관리"""
    
    def __init__(self):
        self.gcp_available = True
        self.aws_available = True
        self.current_provider = PREFERRED_CLOUD
        self.last_health_check = time.time()
        self.current_config = None
        
    def get_gcp_config(self):
        """GCP Secret Manager에서 설정 로드"""
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = client.secret_version_path("hifrodo-05", "project-secrets", "latest")
            response = client.access_secret_version(request={"name": name})
            config = json.loads(response.payload.data.decode("UTF-8"))
            
            return {
                'flask_secret': config['flask_secret'],
                'redis_host': config['redis_host'],
                'mysql_host': config['mysql_host'],
                'mysql_user': config['mysql_user'],
                'mysql_password': config['mysql_password'],
                'mysql_db': config['mysql_db'],
                'provider': 'GCP'
            }
        except Exception as e:
            logger.error(f"GCP config load failed: {e}")
            self.gcp_available = False
            return None
    
    def get_aws_config(self):
        """AWS Secrets Manager에서 설정 로드"""
        try:
            import boto3
            session_aws = boto3.session.Session()
            client = session_aws.client('secretsmanager', region_name="us-east-2")
            response = client.get_secret_value(SecretId='flask/app')
            config = json.loads(response['SecretString'])
            
            return {
                'flask_secret': config['flask_secret'],
                'redis_host': config['redis_host'],
                'mysql_host': config['host'],
                'mysql_user': config['username'],
                'mysql_password': config['password'],
                'mysql_db': config['dbname'],
                'provider': 'AWS'
            }
        except Exception as e:
            logger.error(f"AWS config load failed: {e}")
            self.aws_available = False
            return None
    
    def test_database_connection(self, config):
        """데이터베이스 연결 테스트"""
        if not config:
            return False
        try:
            import mysql.connector
            connection = mysql.connector.connect(
                host=config['mysql_host'],
                user=config['mysql_user'],
                password=config['mysql_password'],
                database=config['mysql_db'],
                connect_timeout=5
            )
            connection.close()
            return True
        except Exception as e:
            logger.error(f"Database connection test failed for {config['provider']}: {e}")
            return False
    
    def get_active_config(self):
        """활성 설정 반환 (우선순위: GCP -> AWS)"""
        # GCP 우선 시도
        if PREFERRED_CLOUD == 'GCP' and self.gcp_available:
            gcp_config = self.get_gcp_config()
            if gcp_config and self.test_database_connection(gcp_config):
                self.current_provider = 'GCP'
                self.current_config = gcp_config
                logger.info("Using GCP configuration")
                return gcp_config
            else:
                logger.warning("GCP health check failed, falling back to AWS")
                self.gcp_available = False
        
        # AWS 대체 시도
        if self.aws_available:
            aws_config = self.get_aws_config()
            if aws_config and self.test_database_connection(aws_config):
                self.current_provider = 'AWS'
                self.current_config = aws_config
                logger.info("Using AWS configuration")
                return aws_config
            else:
                logger.error("AWS health check also failed")
                self.aws_available = False
        
        # 모든 클라우드 실패
        raise Exception("Both GCP and AWS are unavailable")

# 전역 클라우드 프로바이더 인스턴스
cloud_provider = CloudProvider()

# 활성 설정 로드
try:
    active_config = cloud_provider.get_active_config()
except Exception as e:
    logger.critical(f"Failed to initialize any cloud provider: {e}")
    raise

# Flask 앱 설정
app = Flask(__name__)
app.secret_key = active_config['flask_secret']

# Redis 세션 설정 (GCP, AWS 모두 SSL 없이)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.StrictRedis(
    host=active_config['redis_host'], 
    port=6379
)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'session:'
Session(app)

# MySQL 설정
app.config['MYSQL_HOST'] = active_config['mysql_host']
app.config['MYSQL_USER'] = active_config['mysql_user']
app.config['MYSQL_PASSWORD'] = active_config['mysql_password']
app.config['MYSQL_DB'] = active_config['mysql_db']

mysql = MySQL(app)

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 사용자 클래스
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# 사용자 로드 함수
@login_manager.user_loader
def load_user(user_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            return User(id=user[0], username=user[1], password=user[2])
        return None
    except Exception as e:
        logger.error(f"User load failed: {e}")
        return None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        mysql.connection.commit()
        cursor.close()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        if user and check_password_hash(user[2], password):
            login_user(User(id=user[0], username=user[1], password=user[2]))
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    client_ip = request.remote_addr
    server_name = socket.gethostname()
    try:
        server_ip = socket.gethostbyname(server_name)
    except Exception:
        server_ip = 'Unknown'
    xff = request.headers.get('X-Forwarded-For', 'Not Available')
    
    return render_template(
        'dashboard.html',
        current_user=current_user,
        client_ip=client_ip,
        server_name=server_name,
        server_ip=server_ip,
        xff=xff
    )

@app.route('/board')
@login_required
def board():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT p.id, p.title, p.content, p.created_at, u.username 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        ORDER BY p.created_at DESC
    """)
    posts = cursor.fetchall()
    cursor.close()
    return render_template('board.html', posts=posts)

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO posts (title, content, author_id, created_at) VALUES (%s, %s, %s, %s)",
            (title, content, current_user.id, datetime.now())
        )
        mysql.connection.commit()
        cursor.close()
        flash('Post created successfully!')
        return redirect(url_for('board'))
    return render_template('new_post.html')

@app.route('/post/<int:id>')
@login_required
def view_post(id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT p.id, p.title, p.content, p.created_at, u.username, p.author_id
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.id = %s
    """, (id,))
    post = cursor.fetchone()
    cursor.close()
    if not post:
        flash('Post not found.')
        return redirect(url_for('board'))
    return render_template('view_post.html', post=post)

@app.route('/post/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, title, content, author_id, created_at FROM posts WHERE id = %s", (id,))
    post = cursor.fetchone()
    
    if not post or post[3] != current_user.id:
        flash('You can only edit your own posts.')
        return redirect(url_for('board'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor.execute(
            "UPDATE posts SET title = %s, content = %s WHERE id = %s",
            (title, content, id)
        )
        mysql.connection.commit()
        cursor.close()
        flash('Post updated successfully!')
        return redirect(url_for('view_post', id=id))
    
    cursor.close()
    return render_template('edit_post.html', post=post)

@app.route('/post/<int:id>/delete', methods=['POST'])
@login_required
def delete_post(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT author_id FROM posts WHERE id = %s", (id,))
    post = cursor.fetchone()
    
    if not post or post[0] != current_user.id:
        flash('You can only delete your own posts.')
        return redirect(url_for('board'))
    
    cursor.execute("DELETE FROM posts WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash('Post deleted successfully!')
    return redirect(url_for('board'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 세션 정보를 JSON으로 반환
@app.route('/api/session-info')
@login_required
def session_info_api():
    from flask import jsonify
    import time
    
    try:
        session_data = {
            'user_id': current_user.id,
            'username': current_user.username,
            'session_id': session.get('_id', 'N/A'),
            'user_session_id': session.get('_user_id', 'N/A'),
            'fresh_login': session.get('_fresh', False),
            'is_authenticated': current_user.is_authenticated,
            'login_timestamp': time.time(),
            'session_keys': list(session.keys()),
            'request_info': {
                'ip': request.remote_addr,
                'user_agent': str(request.user_agent),
                'url': request.url
            },
            'cloud_provider': {
                'current': cloud_provider.current_provider,
                'gcp_available': cloud_provider.gcp_available,
                'aws_available': cloud_provider.aws_available
            }
        }
        
        return jsonify(session_data)
    except Exception as e:
        return jsonify({'error': 'Session info unavailable', 'message': str(e)}), 500

@app.route('/api/cloud-status')
def cloud_status_api():
    """클라우드 제공업체 상태 API"""
    from flask import jsonify
    
    return jsonify({
        'current_provider': cloud_provider.current_provider,
        'gcp_available': cloud_provider.gcp_available,
        'aws_available': cloud_provider.aws_available,
        'last_health_check': cloud_provider.last_health_check,
        'timestamp': time.time()
    })

@app.route('/healthz')
def health_check():
    return "OK", 200

# 백그라운드 헬스체크 (간단 버전)
def background_health_check():
    """백그라운드에서 주기적으로 헬스체크 수행"""
    while True:
        try:
            time.sleep(60)  # 60초마다 체크
            # 간단한 가용성 체크만 수행
            if cloud_provider.current_provider == 'GCP':
                if not cloud_provider.test_database_connection(cloud_provider.current_config):
                    logger.warning("GCP connection lost, checking AWS...")
                    cloud_provider.gcp_available = False
                    try:
                        new_config = cloud_provider.get_active_config()
                        if new_config['provider'] == 'AWS':
                            logger.info("Switched to AWS in background")
                    except:
                        pass
        except Exception as e:
            logger.error(f"Background health check failed: {e}")

# 백그라운드 헬스체크 스레드 시작
health_thread = threading.Thread(target=background_health_check, daemon=True)
health_thread.start()

if __name__ == '__main__':
    logger.info(f"Starting Flask app with {cloud_provider.current_provider} configuration")
    app.run(host='0.0.0.0', port=5000, debug=False)
