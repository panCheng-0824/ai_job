-- =============================================================================
-- ROLE005 模拟面试官 — 业务主库表结构（MySQL 8）
--
-- 职责：server_job 为面试业务唯一 Source of Truth；ai_job 不写本库。
-- 执行：在目标库执行本脚本一次；已有库升级见 interview_schema_upgrade_mysql8.sql
-- V2 关系型表结构见 interview_schema_v2_mysql8.sql；V1→V2 迁移见 interview_schema_v2_upgrade_mysql8.sql
-- V1 interview_plans 已废弃，迁移完成后执行 interview_drop_v1_plans_mysql8.sql
-- 字符集：utf8mb4_unicode_ci
-- =============================================================================

SET NAMES utf8mb4;

-- -----------------------------------------------------------------------------
-- 1. 面试会话（可变状态 + 乐观锁）
-- 大纲数据见 interview_schema_v2_mysql8.sql 中 interview_plan_basics 等表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_sessions (
  interview_session_id VARCHAR(64)  NOT NULL COMMENT '面试业务会话 ID',
  student_id           VARCHAR(64)  NOT NULL COMMENT '学号，租户隔离键',
  chat_session_id      VARCHAR(128) NULL COMMENT '关联聊天 UI 会话（t_chat_session.session_id）',
  plan_id              VARCHAR(64)  NOT NULL COMMENT '引用 interview_plan_basics.plan_id',
  plan_version         INT          NOT NULL DEFAULT 1 COMMENT '引用大纲版本',
  status               VARCHAR(32)  NOT NULL DEFAULT 'planning'
    COMMENT 'planning|ready|in_progress|completed|abandoned',
  phase                VARCHAR(32)  NOT NULL DEFAULT 'self_intro'
    COMMENT 'self_intro|question|summary',
  current_question_index INT        NOT NULL DEFAULT 0 COMMENT '当前题索引（0-based）',
  lock_version         INT          NOT NULL DEFAULT 0 COMMENT '乐观锁版本',
  snapshots_json       JSON         NULL COMMENT '岗位/企业/简历快照 JobSnapshot 等',
  answers_json         JSON         NOT NULL COMMENT 'AnswerRecord[] 作答历史',
  report_id            VARCHAR(64)  NULL COMMENT '关联 interview_reports.report_id',
  token_budget_used    INT          NOT NULL DEFAULT 0 COMMENT '累计 token 消耗',
  scorer_version       VARCHAR(32)  NOT NULL DEFAULT 'v1',
  graph_checkpoint_id  VARCHAR(128) NULL COMMENT 'ai_job LangGraph checkpoint 提示 ID',
  meta_json            JSON         NULL COMMENT '扩展元数据',
  created_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  completed_at         DATETIME(3)  NULL,
  PRIMARY KEY (interview_session_id),
  KEY idx_student_status (student_id, status, updated_at DESC),
  KEY idx_chat_session (chat_session_id),
  KEY idx_plan (plan_id, plan_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试会话：进度、评分、报告关联';

-- -----------------------------------------------------------------------------
-- 3. 面试回合（幂等核心）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_turns (
  turn_id              VARCHAR(64)  NOT NULL COMMENT '回合 ID，客户端生成 UUID',
  interview_session_id VARCHAR(64)  NOT NULL,
  student_id           VARCHAR(64)  NOT NULL COMMENT '冗余学号，便于幂等索引',
  idempotency_key      VARCHAR(192) NOT NULL COMMENT '幂等键，建议 student_id:session:action:seq',
  action               VARCHAR(32)  NOT NULL COMMENT 'answer|clarify|hint|timeout|abandon|start',
  payload_json         JSON         NULL COMMENT '请求 payload',
  result_snapshot_json JSON         NULL COMMENT '处理后的状态摘要 / TurnResult',
  processed_at         DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (turn_id),
  UNIQUE KEY uk_idempotency (student_id, idempotency_key),
  KEY idx_session_processed (interview_session_id, processed_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试回合：幂等写入';

-- -----------------------------------------------------------------------------
-- 4. 面试报告（完成后写入，immutable）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_reports (
  report_id            VARCHAR(64)  NOT NULL,
  interview_session_id VARCHAR(64)  NOT NULL,
  student_id           VARCHAR(64)  NOT NULL,
  payload_json         JSON         NOT NULL COMMENT 'InterviewReport 完整 JSON',
  rubric_version       VARCHAR(32)  NOT NULL DEFAULT 'v1',
  scorer_model         VARCHAR(128) NOT NULL DEFAULT '',
  total_score          DECIMAL(6,2) NULL COMMENT '总分，便于列表排序',
  generated_at         DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (report_id),
  UNIQUE KEY uk_session_report (interview_session_id),
  KEY idx_student_generated (student_id, generated_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试总结报告';

-- -----------------------------------------------------------------------------
-- 5. 审计日志（状态变更、缓存命中、异常）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_audit_logs (
  id                   BIGINT       NOT NULL AUTO_INCREMENT,
  interview_session_id VARCHAR(64)  NULL,
  student_id           VARCHAR(64)  NOT NULL DEFAULT '',
  event_type           VARCHAR(64)  NOT NULL COMMENT '如 session.started, turn.processed, plan.confirmed',
  actor                VARCHAR(64)  NOT NULL DEFAULT 'system' COMMENT 'student|system|ai_job_a|ai_job_b',
  detail_json          JSON         NULL,
  trace_id             VARCHAR(64)  NULL COMMENT '贯穿 HTTP/MQ 的追踪 ID',
  created_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_session_created (interview_session_id, created_at DESC),
  KEY idx_student_created (student_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试审计日志';

-- -----------------------------------------------------------------------------
-- 6. 学生面试画像（Reflection 异步写入）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_interview_profiles (
  id                   BIGINT       NOT NULL AUTO_INCREMENT,
  student_id           VARCHAR(64)  NOT NULL,
  profile_json         JSON         NOT NULL COMMENT '优势/薄弱/沟通风格等',
  last_interview_session_id VARCHAR(64) NULL,
  reflection_model     VARCHAR(128) NOT NULL DEFAULT '',
  confidence           DECIMAL(4,3) NULL COMMENT '画像置信度 0~1',
  updated_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_student (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生面试画像资产';

-- -----------------------------------------------------------------------------
-- 7. 追问模式资产（Reflection 产出，供 Planner/Interviewer 检索）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_followup_patterns (
  id                   BIGINT       NOT NULL AUTO_INCREMENT,
  pattern_id           VARCHAR(64)  NOT NULL COMMENT '业务 ID',
  trigger_json         JSON         NOT NULL COMMENT '触发条件，如 answer_contains',
  followup_text        VARCHAR(1024) NOT NULL DEFAULT '',
  dimension            VARCHAR(64)  NOT NULL DEFAULT '',
  source_session_id    VARCHAR(64)  NULL,
  milvus_collection    VARCHAR(128) NULL,
  milvus_vector_id     VARCHAR(128) NULL,
  confidence           DECIMAL(4,3) NULL,
  created_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_pattern_id (pattern_id),
  KEY idx_dimension (dimension)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='追问模式资产库';

-- -----------------------------------------------------------------------------
-- 8. 人群洞察（Reflection 产出，注入 Planner）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_cohort_insights (
  id                   BIGINT       NOT NULL AUTO_INCREMENT,
  insight_id           VARCHAR(64)  NOT NULL,
  insight_type         VARCHAR(64)  NOT NULL COMMENT '如 weak_skill, role_match',
  pattern_json         JSON         NOT NULL,
  suggested_action     VARCHAR(512) NOT NULL DEFAULT '',
  confidence           DECIMAL(4,3) NOT NULL DEFAULT 0.000,
  target_role          VARCHAR(256) NOT NULL DEFAULT '',
  created_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_insight_id (insight_id),
  KEY idx_type_role (insight_type, target_role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='人群洞察资产';

-- -----------------------------------------------------------------------------
-- 9. 人工复核队列（P2，评分异议）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_review_queue (
  id                   BIGINT       NOT NULL AUTO_INCREMENT,
  interview_session_id VARCHAR(64)  NOT NULL,
  report_id            VARCHAR(64)  NOT NULL,
  student_id           VARCHAR(64)  NOT NULL,
  reason               VARCHAR(512) NOT NULL DEFAULT '',
  status               VARCHAR(32)  NOT NULL DEFAULT 'pending' COMMENT 'pending|approved|rejected',
  reviewer             VARCHAR(64)  NULL,
  detail_json          JSON         NULL,
  created_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_status_created (status, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试报告人工复核队列';

-- -----------------------------------------------------------------------------
-- 10. MQ 消费幂等（防止 interview_ai_result 重复入库）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_mq_consume_log (
  id                   BIGINT       NOT NULL AUTO_INCREMENT,
  message_id           VARCHAR(64)  NOT NULL COMMENT 'MQ message_id',
  idempotency_key      VARCHAR(192) NOT NULL DEFAULT '',
  event_type           VARCHAR(128) NOT NULL,
  consumer_group       VARCHAR(128) NOT NULL,
  payload_digest       VARCHAR(64)  NOT NULL DEFAULT '' COMMENT 'payload SHA256 摘要',
  processed_at         DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_message_id (message_id),
  KEY idx_idempotency (idempotency_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='RocketMQ 消费去重表';

-- -----------------------------------------------------------------------------
-- 11. Milvus 向量元数据索引（向量本体在 Milvus，本表仅存关联）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_milvus_index_meta (
  id                   BIGINT       NOT NULL AUTO_INCREMENT,
  plan_id              VARCHAR(64)  NOT NULL,
  plan_version         INT          NOT NULL,
  milvus_collection    VARCHAR(128) NOT NULL,
  milvus_vector_id     VARCHAR(128) NOT NULL,
  material_hash        VARCHAR(64)  NOT NULL DEFAULT '',
  summary              VARCHAR(1024) NOT NULL DEFAULT '',
  created_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_plan_vector (plan_id, plan_version, milvus_collection),
  KEY idx_material_hash (material_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试大纲向量索引元数据';
