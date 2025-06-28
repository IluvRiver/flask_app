-- posts 테이블 구조 수정
-- user_id 컬럼이 없다면 추가

-- 현재 테이블 구조 확인
DESCRIBE posts;

-- user_id 컬럼 추가 (없는 경우)
ALTER TABLE posts 
ADD COLUMN user_id INT NOT NULL AFTER content;

-- 외래키 제약조건 추가
ALTER TABLE posts 
ADD CONSTRAINT fk_posts_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 인덱스 추가
CREATE INDEX idx_user_id ON posts(user_id);

-- 수정된 테이블 구조 확인
DESCRIBE posts;

-- 기존 데이터가 있다면 임시로 user_id 업데이트 (첫 번째 사용자로 설정)
-- UPDATE posts SET user_id = 1 WHERE user_id = 0 OR user_id IS NULL;
