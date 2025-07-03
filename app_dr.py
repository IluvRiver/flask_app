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
from functools import wraps

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수로 우선순위 결정 (GCP: primary, AWS: secondary)
PREFERRED_CLOUD = os.getenv('PREFERRED_CLOUD', 'GCP')  # GCP 또는 AWS

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
            # import를 try 블록 안에서 수행하여 AWS 환경에서 오류 방지
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
        except ImportError as ie:
            logger.warning(f"GCP library not available (running on AWS?): {ie}")
            self.gcp_available = False
            return None
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
        except ImportError as ie:
            logger.warning(f"AWS library not available (running on GCP?): {ie}")
            self.aws_available = False
            return None
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
    
    def test_redis_connection(self, config):
        """Redis 연결 테스트"""
        if not config:
            return False
        try:
            # GCP는 SSL 없이, AWS는 SSL 사용
            if config['provider'] == 'GCP':
                r = redis.StrictRedis(
                    host=config['redis_host'], 
                    port=6379,
                    socket_connect_timeout=5
                )
            else:  # AWS
                r = redis.StrictRedis(
                    host=config['redis_host'], 
                    port=6379,
                    ssl=True,
                    ssl_cert_reqs=None,
                    socket_connect_timeout=5
                )
            r.ping()
            return True
        except Exception as e:
            logger.error(f"Redis connection test failed for {config['provider']}: {e}")
            return False
    
    def get_active_config(self):
        """활성 설정 반환 (AWS 환경에서는 AWS 우선)"""
        
        # AWS 환경에서 실행 중인지 감지 (환경 변수 또는 메타데이터로 확인)
        running_on_aws = self._detect_aws_environment()
        
        if running_on_aws:
            logger.info("Detected AWS environment, prioritizing AWS configuration")
            # AWS 환경에서는 AWS 우선
            if self.aws_available:
                aws_config = self.get_aws_config()
                if aws_config and self.test_database_connection(aws_config) and self.test_redis_connection(aws_config):
                    self.current_provider = 'AWS'
                    self.current_config = aws_config
                    logger.info("Using AWS configuration")
                    return aws_config
                else:
                    logger.error("AWS configuration failed")
                    self.aws_available = False
            
            # AWS 실패 시 GCP 시도하지 않음 (라이브러리 없음)
            raise Exception("AWS configuration unavailable in AWS environment")
        
        else:
            logger.info("Detected GCP environment, prioritizing GCP configuration")
            # GCP 환경에서는 원래 로직대로
            if PREFERRED_CLOUD == 'GCP' and self.gcp_available:
                gcp_config = self.get_gcp_config()
                if gcp_config and self.test_database_connection(gcp_config) and self.test_redis_connection(gcp_config):
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
                if aws_config and self.test_database_connection(aws_config) and self.test_redis_connection(aws_config):
                    self.current_provider = 'AWS'
                    self.current_config = aws_config
                    logger.info("Using AWS configuration")
                    return aws_config
                else:
                    logger.error("AWS health check also failed")
                    self.aws_available = False
            
            # 모든 클라우드 실패
            raise Exception("Both GCP and AWS are unavailable")
    
    def _detect_aws_environment(self):
        """AWS 환경에서 실행 중인지 감지"""
        # 방법 1: 환경 변수 확인
        if os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION'):
            return True
        
        # 방법 2: EC2 메타데이터 확인 (간단한 방법)
        try:
            import urllib.request
            urllib.request.urlopen('http://169.254.169.254/latest/meta-data/', timeout=1)
            return True
        except:
            pass
        
        # 방법 3: boto3 사용 가능 여부로 판단
        try:
            import boto3
            boto3.Session().region_name  # AWS 환경에서만 작동
            return True
        except:
            pass
        
        return False
    
    def switch_provider(self, app_instance, mysql_instance):
        """프로바이더 전환 로직"""
        try:
            new_config = self.get_active_config()
            if new_config and new_config['provider'] != self.current_config['provider']:
                logger.info(f"Switching from {self.current_config['provider']} to {new_config['provider']}")
                
                # Flask 앱 재설정
                self.current_config = new_config
                app_instance.config['MYSQL_HOST'] = new_config['mysql_host']
                app_instance.config['MYSQL_USER'] = new_config['mysql_user']
                app_instance.config['MYSQL_PASSWORD'] = new_config['mysql_password']
                app_instance.config['MYSQL_DB'] = new_config['mysql_db']
                
                # Redis 연결 재설정 (클라우드별 SSL 설정)
                if new_config['provider'] == 'GCP':
                    app_instance.config['SESSION_REDIS'] = redis.StrictRedis(
                        host=new_config['redis_host'], 
                        port=6379
                    )
                else:  # AWS
                    app_instance.config['SESSION_REDIS'] = redis.StrictRedis(
                        host=new_config['redis_host'], 
                        port=6379,
                        ssl=True,
                        ssl_cert_reqs=None
                    )
                
                # MySQL 연결 재초기화
                mysql_instance.__init__(app_instance)
                
                # 세션 재초기화
                Session(app_instance)
                
                return True
            return False
        except Exception as e:
            logger.error(f"Provider switch failed: {e}")
            return False

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

# Redis 세션 설정 (클라우드별 SSL 설정)
app.config['SESSION_TYPE'] = 'redis'
if active_config['provider'] == 'GCP':
    app.config['SESSION_REDIS'] = redis.StrictRedis(
        host=active_config['redis_host'], 
        port=6379
    )
else:  # AWS
    app.config['SESSION_REDIS'] = redis.StrictRedis(
        host=active_config['redis_host'], 
        port=6379,
        ssl=True,
        ssl_cert_reqs=None
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

# 헬스체크 데코레이터
def health_check_wrapper(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 30초마다 헬스체크 수행
        current_time = time.time()
        if current_time - cloud_provider.last_health_check > 30:
            try:
                # 현재 설정으로 연결 테스트
                if not cloud_provider.test_database_connection(cloud_provider.current_config):
                    logger.warning(f"Current {cloud_provider.current_config['provider']} database connection failed, attempting failover")
                    
                    # 프로바이더 전환 시도
                    if cloud_provider.switch_provider(app, mysql):
                        flash(f'Switched to {cloud_provider.current_provider} due to connection issues', 'info')
                        
                cloud_provider.last_health_check = current_time
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
        
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Route execution failed: {e}")
            # 데이터베이스 오류인 경우 대체 설정 시도
            if any(keyword in str(e).lower() for keyword in ["database", "mysql", "connection", "redis"]):
                try:
                    if cloud_provider.switch_provider(app, mysql):
                        flash(f'Switched to {cloud_provider.current_provider} due to connection issues', 'warning')
                        return redirect(request.url)
                except Exception as switch_error:
                    logger.error(f"Emergency failover failed: {switch_error}")
            raise e
    
    return decorated_function

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
@health_check_wrapper
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@health_check_wrapper
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 입력 검증
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
        
        try:
            hashed_password = generate_password_hash(password)
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            mysql.connection.commit()
            cursor.close()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            flash('Registration failed. Username may already exist.', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@health_check_wrapper
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')
        
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            
            if user and check_password_hash(user[2], password):
                login_user(User(id=user[0], username=user[1], password=user[2]))
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
        except Exception as e:
            logger.error(f"Login failed: {e}")
            flash('Login failed due to system error.', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
@health_check_wrapper
def dashboard():
    client_ip = request.remote_addr
    server_name = socket.gethostname()
    try:
        server_ip = socket.gethostbyname(server_name)
    except Exception:
        server_ip = 'Unknown'
    xff = request.headers.get('X-Forwarded-For', 'Not Available')
    
    return render_template(
        'dashboard_dr.html',
        current_user=current_user,
        client_ip=client_ip,
        server_name=server_name,
        server_ip=server_ip,
        xff=xff,
        current_provider=cloud_provider.current_provider,
        gcp_status='🟢 Online' if cloud_provider.gcp_available else '🔴 Offline',
        aws_status='🟢 Online' if cloud_provider.aws_available else '🔴 Offline'
    )

@app.route('/board')
@login_required
@health_check_wrapper
def board():
    try:
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
    except Exception as e:
        logger.error(f"Board loading failed: {e}")
        flash('Failed to load posts.', 'error')
        return render_template('board.html', posts=[])

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
@health_check_wrapper
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        if not title or not content:
            flash('Title and content are required.', 'error')
            return render_template('new_post.html')
        
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO posts (title, content, author_id, created_at) VALUES (%s, %s, %s, %s)",
                (title, content, current_user.id, datetime.now())
            )
            mysql.connection.commit()
            cursor.close()
            flash('Post created successfully!', 'success')
            return redirect(url_for('board'))
        except Exception as e:
            logger.error(f"Post creation failed: {e}")
            flash('Failed to create post.', 'error')
    
    return render_template('new_post.html')

@app.route('/post/<int:id>')
@login_required
@health_check_wrapper
def view_post(id):
    try:
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
            flash('Post not found.', 'error')
            return redirect(url_for('board'))
        
        return render_template('view_post.html', post=post)
    except Exception as e:
        logger.error(f"Post viewing failed: {e}")
        flash('Failed to load post.', 'error')
        return redirect(url_for('board'))

@app.route('/post/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@health_check_wrapper
def edit_post(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, title, content, author_id, created_at FROM posts WHERE id = %s", (id,))
        post = cursor.fetchone()
        
        if not post or post[3] != current_user.id:
            flash('You can only edit your own posts.', 'error')
            return redirect(url_for('board'))
        
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            
            if not title or not content:
                flash('Title and content are required.', 'error')
                return render_template('edit_post.html', post=post)
            
            cursor.execute(
                "UPDATE posts SET title = %s, content = %s WHERE id = %s",
                (title, content, id)
            )
            mysql.connection.commit()
            cursor.close()
            flash('Post updated successfully!', 'success')
            return redirect(url_for('view_post', id=id))
        
        cursor.close()
        return render_template('edit_post.html', post=post)
    except Exception as e:
        logger.error(f"Post editing failed: {e}")
        flash('Failed to edit post.', 'error')
        return redirect(url_for('board'))

@app.route('/post/<int:id>/delete', methods=['POST'])
@login_required
@health_check_wrapper
def delete_post(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT author_id FROM posts WHERE id = %s", (id,))
        post = cursor.fetchone()
        
        if not post or post[0] != current_user.id:
            flash('You can only delete your own posts.', 'error')
            return redirect(url_for('board'))
        
        cursor.execute("DELETE FROM posts WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()
        flash('Post deleted successfully!', 'success')
        return redirect(url_for('board'))
    except Exception as e:
        logger.error(f"Post deletion failed: {e}")
        flash('Failed to delete post.', 'error')
        return redirect(url_for('board'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/api/session-info')
@login_required
@health_check_wrapper
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
    """헬스체크 엔드포인트"""
    try:
        # 데이터베이스 연결 확인
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        
        status = {
            'status': 'healthy',
            'provider': cloud_provider.current_provider,
            'timestamp': time.time()
        }
        return status, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {'status': 'unhealthy', 'error': str(e)}, 503

# 정기적인 헬스체크를 위한 백그라운드 스레드
def background_health_check():
    """백그라운드에서 주기적으로 헬스체크 수행"""
    while True:
        try:
            time.sleep(60)  # 60초마다 체크 (부하 감소)
            cloud_provider.get_active_config()
        except Exception as e:
            logger.error(f"Background health check failed: {e}")

# 백그라운드 헬스체크 스레드 시작
health_thread = threading.Thread(target=background_health_check, daemon=True)
health_thread.start()

# 애플리케이션 에러 핸들러
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    logger.info(f"Starting Flask app with {cloud_provider.current_provider} configuration")
    app.run(host='0.0.0.0', port=5000, debug=False)