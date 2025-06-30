from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import socket
import redis
from google.cloud import secretmanager
import json
from datetime import datetime


# 🔑 GCP Secret Manager에서 시크릿 불러오기 함수
def get_secret(project_id, secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()
    name = client.secret_version_path(project_id, secret_id, version_id)
    response = client.access_secret_version(request={"name": name})
    return json.loads(response.payload.data.decode("UTF-8"))


# 🔐 시크릿 로드 (프로젝트 ID와 시크릿 이름 설정)
PROJECT_ID = "hifrodo-05"  # GCP 프로젝트 ID로 변경
secret = get_secret(PROJECT_ID, "flask-app-config")

# Flask 앱 설정
app = Flask(__name__)
app.secret_key = secret['flask_secret']

# Redis 세션 설정
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.StrictRedis(host=secret['redis_host'], port=6379,ssl=True,
    ssl_cert_reqs=None)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'session:'
Session(app)

# MySQL 설정
app.config['MYSQL_HOST'] = secret['mysql_host']
app.config['MYSQL_USER'] = secret['mysql_user']
app.config['MYSQL_PASSWORD'] = secret['mysql_password']
app.config['MYSQL_DB'] = secret['mysql_db']

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
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(id=user[0], username=user[1], password=user[2])
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
    server_ip = socket.gethostbyname(server_name)
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
    
    if not post or post[3] != current_user.id:  # post[3] is author_id
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

# 세션 정보를 JSON으로 반환 (Local Storage용)
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
            }
        }
        
        return jsonify(session_data)
    except Exception as e:
        return jsonify({'error': 'Session info unavailable', 'message': str(e)}), 500

@app.route('/healthz')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
