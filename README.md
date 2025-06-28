# Flask CRUD Board Application 🚀

**Modern Flask web application with CRUD functionality and beautiful UI**

![Flask](https://img.shields.io/badge/Flask-2.3.3-green?style=flat-square&logo=flask)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange?style=flat-square&logo=mysql)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

## ✨ Features

- 🔐 **User Authentication** - Secure login/register system
- 📝 **CRUD Operations** - Create, Read, Update, Delete posts
- 🎨 **Modern UI** - Beautiful gradient design with animations
- 📱 **Responsive** - Works perfectly on mobile and desktop
- 🔒 **Permission System** - Users can only edit their own posts
- 📊 **Dashboard** - Real-time server information display
- ⚡ **Fast & Secure** - Password hashing and session management

## 🎯 Demo

![Dashboard Preview](https://via.placeholder.com/800x400/667eea/white?text=Flask+CRUD+Board+Dashboard)

## 🛠️ Tech Stack

- 🔐 사용자 로그인/회원가입
- 📝 게시글 작성, 수정, 삭제, 조회
- 🎨 모던한 UI/UX 디자인
- 🔒 사용자별 게시글 권한 관리
- 📊 대시보드 (서버 정보 표시)

## 📋 필요 요구사항

### 인프라
- MySQL 데이터베이스
- Redis 서버
- AWS Secrets Manager

### Python 패키지
```bash
pip install -r requirements.txt
```

## 🛠️ 설정

### 1. AWS Secrets Manager 설정

`flask/app` 시크릿에 다음 값들을 설정하세요:

```json
{
  "flask_secret": "your-flask-secret-key",
  "host": "mysql-host",
  "username": "mysql-username", 
  "password": "mysql-password",
  "dbname": "your-database-name",
  "redis_host": "redis-host"
}
```

### 2. 데이터베이스 테이블 생성

```sql
-- users 테이블 (이미 존재한다고 가정)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- posts 테이블 생성
CREATE TABLE posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    user_id INT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_created_at (created_at DESC),
    INDEX idx_user_id (user_id)
);
```

## 🏃‍♂️ 실행 방법

1. **가상환경 생성 (권장)**
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 또는
venv\Scripts\activate  # Windows
```

2. **의존성 설치**
```bash
pip install -r requirements.txt
```

3. **애플리케이션 실행**
```bash
python app.py
```

4. **브라우저에서 접속**
```
http://localhost:5000
```

## 📁 프로젝트 구조

```
flask_crud_app/
├── app.py                 # 메인 Flask 애플리케이션
├── requirements.txt       # Python 의존성
├── README.md             # 프로젝트 설명서
└── templates/            # Jinja2 템플릿
    ├── base.html         # 기본 템플릿
    ├── login.html        # 로그인 페이지
    ├── register.html     # 회원가입 페이지
    ├── dashboard.html    # 대시보드
    ├── board.html        # 게시판 목록
    ├── new_post.html     # 새 게시글 작성
    ├── view_post.html    # 게시글 상세보기
    └── edit_post.html    # 게시글 수정
```

## 🔧 개발 환경 설정 (로컬 테스트용)

실제 AWS 인프라 없이 로컬에서 테스트하려면 `app.py`를 다음과 같이 수정:

```python
# AWS Secrets Manager 대신 하드코딩된 설정 사용
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'flask_board'

# Redis 세션 대신 기본 세션 사용
app.config['SESSION_TYPE'] = 'filesystem'
```

## 🎨 주요 특징

- **반응형 디자인**: 모바일과 데스크톱에서 모두 잘 작동
- **모던 UI**: 그라디언트와 카드 레이아웃 사용
- **사용자 인증**: Flask-Login으로 세션 관리
- **보안**: 패스워드 해싱, CSRF 보호
- **권한 관리**: 작성자만 자신의 글 수정/삭제 가능

## 🚀 배포

이 앱은 다음 환경에서 배포 가능합니다:
- AWS EC2 + RDS + ElastiCache
- Docker 컨테이너
- 클라우드 플랫폼 (Heroku, DigitalOcean 등)

## 📝 라이센스

MIT License

## 🤝 기여

Pull Request를 환영합니다!
