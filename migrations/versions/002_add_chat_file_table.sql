-- 파일 첨부 테이블 추가
-- 채팅 세션에 첨부된 파일 정보를 저장

CREATE TABLE IF NOT EXISTS chat_file (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL COMMENT '파일 크기 (bytes)',
    file_type VARCHAR(50) COMMENT 'MIME type',
    file_extension VARCHAR(10) COMMENT '파일 확장자 (.pdf, .jpg 등)',
    description TEXT COMMENT '사용자가 입력한 파일 설명',
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_session(session_id) ON DELETE CASCADE,
    INDEX idx_file_session (session_id),
    INDEX idx_file_uploaded (uploaded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

