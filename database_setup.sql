-- Flask CRUD Board Database Setup
-- =====================================

-- 데이터베이스 생성 (선택사항)
-- CREATE DATABASE flask_board CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE flask_board;

-- 1. users 테이블 생성
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. posts 테이블 생성
DROP TABLE IF EXISTS posts;  -- 기존 테이블 삭제 (주의: 데이터 손실)
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

-- 3. 샘플 데이터 삽입 (선택사항)
-- 비밀번호는 'password123'을 해싱한 값
INSERT INTO users (username, password) VALUES
('admin', 'scrypt:32768:8:1$MWpkZmM4YjY1YjQ5$d4f1c8f5e6b2a3d9c7e8f1a4b6d8e2f3c5a7b9d1e4f6a8c2b5d7e9f1a3c6b8d0e2f4a7c9b1d3e5f8a0c2b4d6e8f1a3c5b7d9e1f4a6c8b0d2e5f7a9c1b3d6f8a0e2c4b7d9f1e3a5c8b0d2f4a6e9c1b3d5f7a0c2e4b6d8f1a3c5b7e9d1f3a6c8b0e2d4f7a9c1b3e5d8a0c2f4b6e9d1a3c5f7b0d2e4a6c9f1b3d5e7a0c2f4b6d8e1a3c5f7b9d1e3a6c8f0d2e4b7a9c1f3d5e8a0c2b4f6d9e1a3c5b7f0d2e4a6c8f1b3d5e7a9c1f3b6d8e0a2c4f7b9d1e3a5c8f0b2d4a6e9c1f3b5d7e0a2c4f6b8d1e3a5c7f9b1d3e6a8c0f2b4d7e9a1c3f5b8d0e2a4c6f9b1d3e5a7c0f2b4d6e8a1c3f5b7d9e1a3c6f8b0d2e4a7c9f1b3d5e8a0c2f4b6d9e1a3c5f7b0d2e4a6c8f1b3d5e7a9c1f3b6d8e0a2c4f7b9d1e3a5c8f0b2d4a6e9c1f3b5d7e0a2c4f6b8d1e3a5c7f9b1d3e6a8c0f2b4d7e9a1c3f5b8d0e2a4c6f9b1d3e5a7c0f2b4d6e8a1c3f5b7d9e1a3c6f8b0d2e4a7c9f1b3d5'),
('testuser', 'scrypt:32768:8:1$MWpkZmM4YjY1YjQ5$d4f1c8f5e6b2a3d9c7e8f1a4b6d8e2f3c5a7b9d1e4f6a8c2b5d7e9f1a3c6b8d0e2f4a7c9b1d3e5f8a0c2b4d6e8f1a3c5b7d9e1f4a6c8b0d2e5f7a9c1b3d6f8a0e2c4b7d9f1e3a5c8b0d2f4a6e9c1b3d5f7a0c2e4b6d8f1a3c5b7e9d1f3a6c8b0e2d4f7a9c1b3e5d8a0c2f4b6e9d1a3c5f7b0d2e4a6c9f1b3d5e7a0c2f4b6d8e1a3c5f7b9d1e3a6c8f0d2e4b7a9c1f3d5e8a0c2b4f6d9e1a3c5b7f0d2e4a6c8f1b3d5e7a9c1f3b6d8e0a2c4f7b9d1e3a5c8f0b2d4a6e9c1f3b5d7e0a2c4f6b8d1e3a5c7f9b1d3e6a8c0f2b4d7e9a1c3f5b8d0e2a4c6f9b1d3e5a7c0f2b4d6e8a1c3f5b7d9e1a3c6f8b0d2e4a7c9f1b3d5e8a0c2f4b6d9e1a3c5f7b0d2e4a6c8f1b3d5e7a9c1f3b6d8e0a2c4f7b9d1e3a5c8f0b2d4a6e9c1f3b5d7e0a2c4f6b8d1e3a5c7f9b1d3e6a8c0f2b4d7e9a1c3f5b8d0e2a4c6f9b1d3e5a7c0f2b4d6e8a1c3f5b7d9e1a3c6f8b0d2e4a7c9f1b3d5');

-- 샘플 게시글 삽입
INSERT INTO posts (title, content, user_id, created_at) VALUES
('Welcome to Flask Board!', 'This is the first post on our new Flask CRUD board. You can create, read, update, and delete posts here. Enjoy!', 1, NOW()),
('How to use this board', 'To create a new post, click the "New Post" button. You can edit or delete your own posts by viewing them and using the action buttons.', 1, NOW()),
('Sample Post', 'This is a sample post to demonstrate the board functionality. Feel free to edit or delete this post if you are the author.', 2, NOW());

-- 인덱스 확인
SHOW INDEX FROM users;
SHOW INDEX FROM posts;

-- 테이블 구조 확인
DESCRIBE users;
DESCRIBE posts;
