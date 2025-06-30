# Flask CRUD Board - Local Development

간단하고 깔끔한 Flask 기반 CRUD 게시판 애플리케이션입니다.

## ✨ 주요 기능

- 🔐 **사용자 인증**: 로그인/회원가입
- 📝 **게시판**: 글 작성, 읽기, 수정, 삭제 (CRUD)
- 🎯 **세션 관리**: Local Storage 연동
- 📱 **반응형 디자인**: 모바일 친화적 UI

## 🚀 빠른 시작

### 1. 필수 조건
- Python 3.8+
- MySQL 8.0+
- 가상환경 권장

### 2. MySQL 설정
```bash
# MySQL 시작
brew services start mysql

# MySQL 로그인
mysql -u root -p

# 데이터베이스 생성 (자동으로 생성되지만 수동으로도 가능)
CREATE DATABASE flask_board;
```

### 3. 실행
```bash
# 프로젝트 디렉토리로 이동
cd /Users/ichungmin/Desktop/flask_crud_app

# 실행 스크립트에 권한 부여
chmod +x run_local.sh

# 앱 실행
./run_local.sh
```

### 4. 접속
- **URL**: http://localhost:8080
- **테스트 계정**:
  - admin / password123
  - testuser / password123

## 📁 프로젝트 구조

```
flask_crud_app/
├── app_local.py              # 메인 애플리케이션
├── init_database.sql         # 데이터베이스 초기화
├── run_local.sh             # 실행 스크립트
├── requirements_local.txt    # Python 패키지 목록
├── .env                     # 환경설정
├── templates/               # HTML 템플릿
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── board.html
│   └── ...
└── old_files/              # 사용하지 않는 파일들
```

## ⚙️ 환경설정

`.env` 파일에서 설정을 변경할 수 있습니다:

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=12345678
MYSQL_DB=flask_board
FLASK_SECRET_KEY=your-super-secret-key-change-this
```

## 🛠️ 수동 실행

스크립트 없이 수동으로 실행하려면:

```bash
# 가상환경 활성화
source venv/bin/activate

# 패키지 설치
pip install -r requirements_local.txt

# 데이터베이스 초기화 (처음 한 번만)
mysql -u root -p12345678 < init_database.sql

# Flask 앱 실행
python app_local.py
```

## 🔧 문제해결

### MySQL 연결 오류
1. MySQL이 실행 중인지 확인: `brew services start mysql`
2. 비밀번호가 올바른지 확인
3. 데이터베이스가 존재하는지 확인

### 포트 충돌
다른 애플리케이션이 8080 포트를 사용 중이면 `app_local.py`에서 포트를 변경하세요:

```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8081)  # 포트 변경
```

## 📝 라이선스

MIT License
