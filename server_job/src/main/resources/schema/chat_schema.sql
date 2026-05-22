-- 聊天会话与消息（由 server_job 维护；执行一次即可）
CREATE TABLE IF NOT EXISTS t_chat_session (
    session_id   VARCHAR(128) NOT NULL PRIMARY KEY,
    student_id   VARCHAR(64)  NOT NULL,
    usercode     VARCHAR(128) NOT NULL,
    username     VARCHAR(256) NOT NULL DEFAULT '',
    role_name    VARCHAR(256) NOT NULL DEFAULT '',
    model_level  VARCHAR(64)  NOT NULL DEFAULT '',
    created_at   DATETIME(3)  NOT NULL,
    updated_at   DATETIME(3)  NOT NULL,
    KEY idx_student_updated (student_id, updated_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS t_chat_message (
    id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL,
    role       VARCHAR(32)  NOT NULL,
    content    MEDIUMTEXT,
    extra_json MEDIUMTEXT   NULL COMMENT 'message_context、context_cards、job_recommend 等扩展字段 JSON',
    msg_ts     VARCHAR(64)  NOT NULL,
    seq_no     INT          NOT NULL,
    KEY idx_session_seq (session_id, seq_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 已有库升级（若列已存在可忽略报错）:
-- ALTER TABLE t_chat_message ADD COLUMN extra_json MEDIUMTEXT NULL COMMENT 'message_context、context_cards 等' AFTER content;
