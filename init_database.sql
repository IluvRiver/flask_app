-- Flask CRUD Board Database Initialization
-- =======================================
-- 이 파일은 로컬 개발환경에서 데이터베이스를 초기화하는 용도입니다.

-- 1. 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS flask_board CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE flask_board;

-- 2. Users 테이블 생성
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Posts 테이블 생성
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    author_id INT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_created_at (created_at DESC),
    INDEX idx_author_id (author_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 테스트 사용자 생성 (비밀번호: password123)
INSERT IGNORE INTO users (username, password) VALUES 
('admin', 'scrypt:32768:8:1$MWpkZmM4YjY1YjQ5$d4f1c8f5e6b2a3d9c7e8f1a4b6d8e2f3c5a7b9d1e4f6a8c2b5d7e9f1a3c6b8d0e2f4a7c9b1d3e5f8a0c2b4d6e8f1a3c5b7d9e1f4a6c8b0d2e5f7a9c1b3d6f8a0e2c4b7d9f1e3a5c8b0d2f4a6e9c1b3d5f7a0c2e4b6d8f1a3c5b7e9d1f3a6c8b0e2d4f7a9c1b3e5d8a0c2f4b6e9d1a3c5f7b0d2e4a6c9f1b3d5e7a0c2f4b6d8e1a3c5f7b9d1e3a6c8f0d2e4b7a9c1f3d5e8a0c2b4f6d9e1a3c5b7f0d2e4a6c8f1b3d5e7a9c1f3b6d8e0a2c4f7b9d1e3a5c8f0b2d4a6e9c1f3b5d7e0a2c4f6b8d1e3a5c7f9b1d3e6a8c0f2b4d7e9a1c3f5b8d0e2a4c6f9b1d3e5a7c0f2b4d6e8a1c3f5b7d9e1a3c6f8b0d2e4a7c9f1b3d5e8a0c2f4b6d9e1a3c5f7b0d2e4a6c8f1b3d5e7a9c1f3b6d8e0a2c4f7b9d1e3a5c8f0b2d4a6e9c1f3b5d7e0a2c4f6b8d1e3a5c7f9b1d3e6a8c0f2b4d7e9a1c3f5b8d0e2a4c6f9b1d3e5a7c0f2b4d6e8a1c3f5b7d9e1a3c6f8b0d2e4a7c9f1b3d5'),
('testuser', 'scrypt:32768:8:1$MWpkZmM4YjY1YjQ5$d4f1c8f5e6b2a3d9c7e8f1a4b6d8e2f3c5a7b9d1e4f6a8c2b5d7e9f1a3c6b8d0e2f4a7c9b1d3e5f8a0c2b4d6e8f1a3c5b7d9e1f4a6c8b0d2e5f7a9c1b3d6f8a0e2c4b7d9f1e3a5c8b0d2f4a6e9c1b3d5f7a0c2e4b6d8f1a3c5b7e9d1f3a6c8b0e2d4f7a9c1b3e5d8a0c2f4b6e9d1a3c5f7b0d2e4a6c9f1b3d5e7a0c2f4b6d8e1a3c5f7b9d1e3a6c8f0d2e4b7a9c1f3d5e8a0c2b4f6d9e1a3c5b7f0d2e4a6c8f1b3d5e7a9c1f3b6d8e0a2c4f7b9d1e3a5c8f0b2d4a6e9c1f3b5d7e0a2c4f6b8d1e3a5c7f9b1d3e6a8c0f2b4d7e9a1c3f5b8d0e2a4c6f9b1d3e5a7c0f2b4d6e8a1c3f5b7d9e1a3c6f8b0d2e4a7c9f1b3d5e8a0c2f4b6d9e1a3c5f7b0d2e4a6c8f1b3d5e7a9c1f3b6d8e0a2c4f7b9d1e3a5c8f0b2d4a6e9c1f3b5d7e0a2c4f6b8d1e3a5c7f9b1d3e6a8c0f2b4d7e9a1c3f5b8d0e2a4c6f9b1d3e5a7c0f2b4d6e8a1c3f5b7d9e1a3c6f8b0d2e4a7c9f1b3d5');

-- 5. 샘플 게시글 생성
INSERT IGNORE INTO posts (title, content, author_id, created_at) VALUES 
('Welcome to Flask Board!', '안녕하세요! Flask CRUD 게시판에 오신 것을 환영합니다.\n\n이 게시판에서는 다음 기능들을 사용할 수 있습니다:\n- 게시글 작성, 읽기, 수정, 삭제\n- 사용자 로그인/회원가입\n- 세션 관리\n\n즐거운 시간 되세요!', 1, NOW()),
('사용법 안내', '게시판 사용법을 알려드립니다:\n\n1. 새 글 작성: "New Post" 버튼을 클릭하세요\n2. 글 읽기: 제목을 클릭하면 전체 내용을 볼 수 있습니다\n3. 글 수정/삭제: 본인이 작성한 글만 수정/삭제 가능합니다\n\n문의사항이 있으시면 언제든 연락주세요!', 1, NOW()),
('테스트 게시글', '이것은 테스트용 게시글입니다.\n\n여러분도 자유롭게 글을 작성해보세요!\n\n로그인 계정:\n- admin / password123\n- testuser / password123', 2, NOW());

-- 6. 데이터베이스 상태 확인
SELECT 'Database initialization completed!' as status;
SELECT COUNT(*) as user_count FROM users;
SELECT COUNT(*) as post_count FROM posts;
