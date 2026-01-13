-- Migration: Add conversation_history column to chat_session table
-- Date: 2026-01-09
-- Description: 질답 내용(conversation_history)을 저장하기 위한 JSON 컬럼 추가

ALTER TABLE chat_session 
ADD COLUMN conversation_history JSON NULL COMMENT 'Q-A 쌍 리스트 (질답 내용)';

-- 기존 데이터는 NULL로 유지 (자동으로 채워짐)
