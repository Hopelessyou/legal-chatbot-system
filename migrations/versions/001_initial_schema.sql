-- 초기 스키마 DDL (MySQL 버전)
-- RAG + LangGraph 기반 법률 상담문의 수집 챗봇 시스템

-- 1. chat_session 테이블 (상담 세션 마스터)
CREATE TABLE IF NOT EXISTS chat_session (
    session_id VARCHAR(50) PRIMARY KEY,
    channel VARCHAR(20) NOT NULL,
    user_hash VARCHAR(64),
    current_state VARCHAR(30) NOT NULL DEFAULT 'INIT',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    completion_rate INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_status CHECK (status IN ('ACTIVE', 'COMPLETED', 'ABORTED')),
    CONSTRAINT chk_completion_rate CHECK (completion_rate >= 0 AND completion_rate <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. chat_session_state_log 테이블 (LangGraph 상태 전이 로그)
CREATE TABLE IF NOT EXISTS chat_session_state_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    from_state VARCHAR(30),
    to_state VARCHAR(30) NOT NULL,
    condition_key VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_session(session_id) ON DELETE CASCADE,
    INDEX idx_state_log_session (session_id),
    INDEX idx_state_log_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. case_master 테이블 (법률 사건 마스터)
CREATE TABLE IF NOT EXISTS case_master (
    case_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    main_case_type VARCHAR(50),
    sub_case_type VARCHAR(50),
    case_stage VARCHAR(30) DEFAULT '상담전',
    urgency_level VARCHAR(20),
    estimated_value BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_session_id (session_id),
    CONSTRAINT chk_urgency_level CHECK (urgency_level IN ('LOW', 'MID', 'HIGH')),
    FOREIGN KEY (session_id) REFERENCES chat_session(session_id) ON DELETE CASCADE,
    INDEX idx_case_type (main_case_type, sub_case_type),
    INDEX idx_case_value (estimated_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. case_party 테이블 (사건 당사자 정보)
CREATE TABLE IF NOT EXISTS case_party (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id BIGINT NOT NULL,
    party_role VARCHAR(20) NOT NULL,
    party_type VARCHAR(20),
    party_description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_party_role CHECK (party_role IN ('의뢰인', '상대방')),
    CONSTRAINT chk_party_type CHECK (party_type IN ('개인', '법인')),
    FOREIGN KEY (case_id) REFERENCES case_master(case_id) ON DELETE CASCADE,
    INDEX idx_case_party_case (case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. case_fact 테이블 (핵심 사실관계)
CREATE TABLE IF NOT EXISTS case_fact (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id BIGINT NOT NULL,
    fact_type VARCHAR(50),
    incident_date DATE,
    location VARCHAR(255),
    description TEXT,
    amount BIGINT,
    confidence_score INTEGER,
    source_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_confidence_score CHECK (confidence_score >= 0 AND confidence_score <= 100),
    FOREIGN KEY (case_id) REFERENCES case_master(case_id) ON DELETE CASCADE,
    INDEX idx_case_fact_case (case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. case_evidence 테이블 (증거 정보)
CREATE TABLE IF NOT EXISTS case_evidence (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id BIGINT NOT NULL,
    evidence_type VARCHAR(50),
    description VARCHAR(255),
    available TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES case_master(case_id) ON DELETE CASCADE,
    INDEX idx_case_evidence_case (case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. case_emotion 테이블 (감정 정보)
CREATE TABLE IF NOT EXISTS case_emotion (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id BIGINT NOT NULL,
    emotion_type VARCHAR(50),
    intensity INTEGER NOT NULL,
    source_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_intensity CHECK (intensity >= 1 AND intensity <= 5),
    FOREIGN KEY (case_id) REFERENCES case_master(case_id) ON DELETE CASCADE,
    INDEX idx_case_emotion_case (case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. case_missing_field 테이블 (누락 정보 관리)
CREATE TABLE IF NOT EXISTS case_missing_field (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id BIGINT NOT NULL,
    field_key VARCHAR(50) NOT NULL,
    required TINYINT(1) NOT NULL DEFAULT 1,
    resolved TINYINT(1) NOT NULL DEFAULT 0,
    resolved_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES case_master(case_id) ON DELETE CASCADE,
    INDEX idx_missing_unresolved (case_id, resolved)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. case_summary 테이블 (최종 요약)
CREATE TABLE IF NOT EXISTS case_summary (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id BIGINT NOT NULL,
    summary_text TEXT NOT NULL,
    structured_json JSON,
    risk_level VARCHAR(20),
    ai_version VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_case_id (case_id),
    FOREIGN KEY (case_id) REFERENCES case_master(case_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. ai_process_log 테이블 (GPT / RAG 호출 로그)
CREATE TABLE IF NOT EXISTS ai_process_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    node_name VARCHAR(50),
    model VARCHAR(50),
    token_input INTEGER,
    token_output INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_session(session_id) ON DELETE CASCADE,
    INDEX idx_ai_log_session (session_id),
    INDEX idx_ai_log_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 추가 인덱스 (이미 테이블 정의에 포함되어 있으므로 주석 처리)
-- MySQL은 CREATE INDEX IF NOT EXISTS를 지원하지 않으므로
-- 인덱스는 테이블 생성 시 함께 생성됩니다
