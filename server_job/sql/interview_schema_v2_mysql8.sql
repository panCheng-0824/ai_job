-- =============================================================================
-- ROLE005 模拟面试官 — 业务主库表结构 V2（MySQL 8）
--
-- 职责：server_job 为面试业务唯一 Source of Truth；ai_job 不写本库。
-- 变更（相对 V1 interview_schema_mysql8.sql）：
--   - 大纲拆为关系表（interview_plan_basics + 题目及附属表），不再使用 payload_json
--   - 行业分类单表树形（interview_industry_category），大纲直绑 level=2 的 category_id
--   - 学生记录拆为 student_interview_records + student_interview_answers
--   - interview_sessions 去掉 answers_json（答题历史改查 student_interview_answers）
--
-- 执行：全新库直接执行本脚本；已有 V1 库升级见 interview_schema_v2_upgrade_mysql8.sql
-- 字符集：utf8mb4_unicode_ci
-- =============================================================================

SET NAMES utf8mb4;

-- -----------------------------------------------------------------------------
-- A. 行业分类（一级 / 二级同表，parent_id + level 表达树形）
-- 大纲仅绑定 level=2 的 category_id（最终层级）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_industry_category (
  category_id          VARCHAR(32)   NOT NULL COMMENT '行业类目 ID',
  parent_id            VARCHAR(32)   NULL     COMMENT '一级为 NULL；二级指向上级 category_id',
  level                TINYINT       NOT NULL COMMENT '1=一级类目 2=二级类目（最终层级）',
  category_code        VARCHAR(64)   NOT NULL COMMENT '稳定编码，同级唯一',
  category_name        VARCHAR(128)  NOT NULL COMMENT '展示名称',
  description          VARCHAR(2000) NOT NULL DEFAULT '' COMMENT '具体描述，供 LLM 分类与意图识别',
  intent_keywords      VARCHAR(1000) NOT NULL DEFAULT '' COMMENT '意图识别关键词，逗号分隔',
  enabled_for_intent   TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否参与生成前意图识别',
  enabled_for_classify TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否参与生成后大纲分类',
  sort_no              INT           NOT NULL DEFAULT 0 COMMENT '同级排序',
  status               VARCHAR(16)   NOT NULL DEFAULT 'active' COMMENT 'active|disabled',
  created_at           DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at           DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (category_id),
  KEY idx_parent_sort (parent_id, sort_no),
  KEY idx_level_intent (level, enabled_for_intent, status),
  KEY idx_level_classify (level, enabled_for_classify, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试行业分类（单表树形）';

-- -----------------------------------------------------------------------------
-- B. 面试大纲 — 基础信息（版本化不可变；修改 = 新版本 INSERT）
-- 逻辑主键：(plan_id, version)；物理主键 plan_row_id = plan_id#version
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_plan_basics (
  plan_row_id                  VARCHAR(96)   NOT NULL COMMENT '物理主键 plan_id#version',
  plan_id                      VARCHAR(64)   NOT NULL COMMENT '大纲业务 ID（可自定义）',
  version                      INT           NOT NULL DEFAULT 1 COMMENT '版本号，从 1 递增',
  title                        VARCHAR(256)  NOT NULL DEFAULT '' COMMENT '大纲标题',
  target_role                  VARCHAR(256)  NOT NULL DEFAULT '' COMMENT '目标岗位名称',
  introduction                 VARCHAR(2000) NOT NULL DEFAULT '' COMMENT '大纲简介',
  suitable_audience            VARCHAR(1000) NOT NULL DEFAULT '' COMMENT '适合人群',
  industry_category_id         VARCHAR(32)   NULL     COMMENT '最终行业 ID，仅 level=2',
  industry_classify_confidence DECIMAL(4,3)  NULL     COMMENT '自动分类置信度 0~1',
  industry_classify_reason     VARCHAR(1000) NOT NULL DEFAULT '' COMMENT '分类理由',
  industry_classify_source     VARCHAR(32)   NOT NULL DEFAULT 'auto' COMMENT 'auto|manual',
  industry_classified_at       DATETIME(3)   NULL     COMMENT '最近一次行业分类时间',
  source_material_hash         VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '简历+岗位素材 SHA256',
  rubric_version               VARCHAR(32)   NOT NULL DEFAULT 'v1' COMMENT '评分量表版本',
  planner_model                VARCHAR(128)  NOT NULL DEFAULT '' COMMENT '生成大纲的模型',
  question_count               INT           NOT NULL DEFAULT 0 COMMENT '题目数（冗余）',
  estimated_minutes            INT           NOT NULL DEFAULT 0 COMMENT '预估时长（分钟）',
  visibility                   VARCHAR(32)   NOT NULL DEFAULT 'private' COMMENT 'private|shared|template',
  status                       VARCHAR(32)   NOT NULL DEFAULT 'draft' COMMENT 'draft|published|archived',
  cache_hit_id                 VARCHAR(64)   NULL     COMMENT '语义缓存命中 ID',
  student_id                   VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '创建者学号',
  created_at                   DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at                   DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (plan_row_id),
  UNIQUE KEY uk_plan_id_version (plan_id, version),
  KEY idx_student_created (student_id, created_at DESC),
  KEY idx_industry (industry_category_id, status),
  KEY idx_material_hash (source_material_hash),
  KEY idx_status_created (status, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试大纲基础信息';

-- -----------------------------------------------------------------------------
-- C. 大纲面试模块标签（如「技术基础」「项目深挖」；与行业分类不同）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_plan_module_tags (
  id           BIGINT       NOT NULL AUTO_INCREMENT,
  plan_row_id  VARCHAR(96)  NOT NULL COMMENT '所属大纲版本',
  tag_name     VARCHAR(128) NOT NULL COMMENT '模块标签名',
  sort_no      INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_plan_row (plan_row_id, sort_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='大纲面试模块标签';

-- -----------------------------------------------------------------------------
-- D. 大纲题目
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_plan_questions (
  iq_row_id        VARCHAR(128)  NOT NULL COMMENT '题目物理主键',
  plan_row_id      VARCHAR(96)   NOT NULL COMMENT '所属大纲版本',
  plan_id          VARCHAR(64)   NOT NULL COMMENT '冗余 plan_id',
  plan_version     INT           NOT NULL COMMENT '冗余 version',
  question_id      VARCHAR(64)   NOT NULL COMMENT '大纲内题目业务 ID',
  seq_no           INT           NOT NULL COMMENT '题目顺序（0-based）',
  question_text    TEXT          NOT NULL COMMENT '题干',
  weight           DECIMAL(6,3)  NOT NULL DEFAULT 1.000 COMMENT '权重',
  thinking_hint    VARCHAR(1024) NOT NULL DEFAULT '' COMMENT '思考提示',
  timeout_seconds  INT           NOT NULL DEFAULT 300 COMMENT '超时秒数',
  reference_answer TEXT          NOT NULL COMMENT '参考答案',
  created_at       DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (iq_row_id),
  UNIQUE KEY uk_plan_question (plan_row_id, question_id),
  UNIQUE KEY uk_plan_seq (plan_row_id, seq_no),
  KEY idx_plan_id_version (plan_id, plan_version, seq_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试大纲题目';

-- -----------------------------------------------------------------------------
-- E. 题目附属表（替代 payload_json 内嵌数组 / 对象）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_plan_question_dimensions (
  id             BIGINT       NOT NULL AUTO_INCREMENT,
  iq_row_id      VARCHAR(128) NOT NULL COMMENT '所属题目',
  dimension_code VARCHAR(64)  NOT NULL COMMENT '考察维度编码',
  sort_no        INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_iq (iq_row_id, sort_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='题目考察维度';

CREATE TABLE IF NOT EXISTS interview_plan_question_followups (
  id            BIGINT        NOT NULL AUTO_INCREMENT,
  iq_row_id     VARCHAR(128)  NOT NULL COMMENT '所属题目',
  seq_no        INT           NOT NULL COMMENT '追问顺序',
  followup_text VARCHAR(1024) NOT NULL COMMENT '预设追问文案',
  PRIMARY KEY (id),
  KEY idx_iq (iq_row_id, seq_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='题目预设追问';

CREATE TABLE IF NOT EXISTS interview_plan_question_criteria (
  id              BIGINT       NOT NULL AUTO_INCREMENT,
  iq_row_id       VARCHAR(128) NOT NULL COMMENT '所属题目',
  criterion_key   VARCHAR(64)  NOT NULL COMMENT '评分项键',
  criterion_value VARCHAR(512) NOT NULL COMMENT '评分项描述',
  sort_no         INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_iq (iq_row_id, sort_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='题目评分标准键值';

-- -----------------------------------------------------------------------------
-- F. 学生面试总结记录（「我的面试记录」列表）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_interview_records (
  record_id             VARCHAR(64)  NOT NULL COMMENT '记录 ID，建议 irec_*',
  student_id            VARCHAR(64)  NOT NULL COMMENT '学号',
  interview_session_id  VARCHAR(64)  NOT NULL COMMENT '面试会话 ID',
  chat_session_id       VARCHAR(128) NULL     COMMENT '聊天 UI 会话',
  plan_id               VARCHAR(64)  NOT NULL COMMENT '使用的大纲 ID',
  plan_version          INT          NOT NULL COMMENT '大纲版本',
  industry_category_id  VARCHAR(32)  NULL     COMMENT '冗余：来自大纲行业',
  target_role           VARCHAR(256) NOT NULL DEFAULT '' COMMENT '冗余：目标岗位',
  plan_title            VARCHAR(256) NOT NULL DEFAULT '' COMMENT '冗余：大纲标题',
  session_status        VARCHAR(32)  NOT NULL DEFAULT 'ready'
    COMMENT 'planning|ready|in_progress|completed|abandoned',
  summary_status        VARCHAR(32)  NOT NULL DEFAULT 'pending' COMMENT 'pending=未总结 summarized=已总结',
  total_score           DECIMAL(6,2) NULL     COMMENT '总分，报告生成后写入',
  report_id             VARCHAR(64)  NULL     COMMENT '关联 interview_reports',
  question_total        INT          NOT NULL DEFAULT 0 COMMENT '总题数',
  question_answered     INT          NOT NULL DEFAULT 0 COMMENT '已答题数',
  created_at            DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '记录创建时间',
  summary_at            DATETIME(3)  NULL     COMMENT '总结完成时间',
  completed_at          DATETIME(3)  NULL     COMMENT '面试结束时间',
  PRIMARY KEY (record_id),
  UNIQUE KEY uk_session (interview_session_id),
  KEY idx_student_created (student_id, created_at DESC),
  KEY idx_student_summary (student_id, summary_status, created_at DESC),
  KEY idx_industry (student_id, industry_category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生面试总结记录';

-- -----------------------------------------------------------------------------
-- G. 学生逐题答题（映射大纲题目）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_interview_answers (
  answer_row_id         VARCHAR(64)   NOT NULL COMMENT '答题行 ID，建议 ians_*',
  interview_session_id  VARCHAR(64)   NOT NULL COMMENT '面试会话',
  student_id            VARCHAR(64)   NOT NULL COMMENT '学号',
  record_id             VARCHAR(64)   NOT NULL COMMENT '所属总结记录',
  plan_id               VARCHAR(64)   NOT NULL COMMENT '冗余 plan_id',
  plan_version          INT           NOT NULL COMMENT '冗余 version',
  iq_row_id             VARCHAR(128)  NOT NULL COMMENT '映射 interview_plan_questions',
  question_id           VARCHAR(64)   NOT NULL COMMENT '冗余题目业务 ID',
  seq_no                INT           NOT NULL COMMENT '题目序号',
  answer_status         VARCHAR(32)   NOT NULL DEFAULT 'pending'
    COMMENT 'pending=未答题 answered=已答题 summarized=已总结',
  answer_text           TEXT          NULL     COMMENT '学生作答文本',
  score                 DECIMAL(6,2)  NULL     COMMENT '单题得分',
  evaluator_comment     VARCHAR(2000) NOT NULL DEFAULT '' COMMENT '单题评语',
  turn_id               VARCHAR(64)   NULL     COMMENT '最后一次有效 turn_id',
  created_at            DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '记录创建时间',
  answered_at           DATETIME(3)   NULL     COMMENT '答题时间',
  summarized_at         DATETIME(3)   NULL     COMMENT '单题总结时间',
  PRIMARY KEY (answer_row_id),
  UNIQUE KEY uk_session_question (interview_session_id, question_id),
  KEY idx_record_seq (record_id, seq_no),
  KEY idx_student_status (student_id, answer_status, answered_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生逐题答题记录';

-- -----------------------------------------------------------------------------
-- H. 面试会话（可变状态 + 乐观锁；V2 去掉 answers_json）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_sessions (
  interview_session_id   VARCHAR(64)  NOT NULL COMMENT '面试业务会话 ID',
  student_id             VARCHAR(64)  NOT NULL COMMENT '学号，租户隔离键',
  chat_session_id        VARCHAR(128) NULL     COMMENT '关联 t_chat_session.session_id',
  plan_id                VARCHAR(64)  NOT NULL COMMENT '引用 interview_plan_basics.plan_id',
  plan_version           INT          NOT NULL DEFAULT 1 COMMENT '引用大纲版本',
  status                 VARCHAR(32)  NOT NULL DEFAULT 'planning'
    COMMENT 'planning|ready|in_progress|completed|abandoned',
  phase                  VARCHAR(32)  NOT NULL DEFAULT 'self_intro'
    COMMENT 'self_intro|question|summary',
  current_question_index INT          NOT NULL DEFAULT 0 COMMENT '当前题索引（0-based）',
  lock_version           INT          NOT NULL DEFAULT 0 COMMENT '乐观锁版本',
  snapshots_json         JSON         NULL     COMMENT '岗位/企业/简历快照',
  report_id              VARCHAR(64)  NULL     COMMENT '关联 interview_reports.report_id',
  token_budget_used      INT          NOT NULL DEFAULT 0 COMMENT '累计 token 消耗',
  scorer_version         VARCHAR(32)  NOT NULL DEFAULT 'v1',
  graph_checkpoint_id    VARCHAR(128) NULL     COMMENT 'ai_job LangGraph checkpoint 提示 ID',
  meta_json              JSON         NULL     COMMENT '扩展元数据',
  created_at             DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at             DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  completed_at           DATETIME(3)  NULL,
  PRIMARY KEY (interview_session_id),
  KEY idx_student_status (student_id, status, updated_at DESC),
  KEY idx_chat_session (chat_session_id),
  KEY idx_plan (plan_id, plan_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试会话：进度、评分、报告关联';

-- -----------------------------------------------------------------------------
-- I. 面试回合（幂等核心）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_turns (
  turn_id              VARCHAR(64)  NOT NULL COMMENT '回合 ID',
  interview_session_id VARCHAR(64)  NOT NULL,
  student_id           VARCHAR(64)  NOT NULL COMMENT '冗余学号',
  idempotency_key      VARCHAR(192) NOT NULL COMMENT '幂等键',
  action               VARCHAR(32)  NOT NULL COMMENT 'answer|clarify|hint|timeout|abandon|start',
  payload_json         JSON         NULL     COMMENT '请求 payload',
  result_snapshot_json JSON         NULL     COMMENT 'TurnResult 摘要',
  processed_at         DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (turn_id),
  UNIQUE KEY uk_idempotency (student_id, idempotency_key),
  KEY idx_session_processed (interview_session_id, processed_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试回合：幂等写入';

-- -----------------------------------------------------------------------------
-- J. 面试报告（完成后 immutable）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_reports (
  report_id            VARCHAR(64)  NOT NULL,
  interview_session_id VARCHAR(64)  NOT NULL,
  student_id           VARCHAR(64)  NOT NULL,
  payload_json         JSON         NOT NULL COMMENT 'InterviewReport 完整 JSON',
  rubric_version       VARCHAR(32)  NOT NULL DEFAULT 'v1',
  scorer_model         VARCHAR(128) NOT NULL DEFAULT '',
  total_score          DECIMAL(6,2) NULL     COMMENT '总分，便于列表排序',
  generated_at         DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (report_id),
  UNIQUE KEY uk_session_report (interview_session_id),
  KEY idx_student_generated (student_id, generated_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试总结报告';

-- -----------------------------------------------------------------------------
-- K. 审计日志
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_audit_logs (
  id                   BIGINT       NOT NULL AUTO_INCREMENT,
  interview_session_id VARCHAR(64)  NULL,
  student_id           VARCHAR(64)  NOT NULL DEFAULT '',
  event_type           VARCHAR(64)  NOT NULL COMMENT '如 session.started, plan.confirmed',
  actor                VARCHAR(64)  NOT NULL DEFAULT 'system' COMMENT 'student|system|ai_job_a|...',
  detail_json          JSON         NULL,
  trace_id             VARCHAR(64)  NULL,
  created_at           DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_session_created (interview_session_id, created_at DESC),
  KEY idx_student_created (student_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试审计日志';

-- -----------------------------------------------------------------------------
-- L~P. 画像 / 资产 / MQ / Milvus（与 V1 保持一致）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_interview_profiles (
  id                        BIGINT       NOT NULL AUTO_INCREMENT,
  student_id                VARCHAR(64)  NOT NULL,
  profile_json              JSON         NOT NULL COMMENT '优势/薄弱/沟通风格等',
  last_interview_session_id VARCHAR(64)  NULL,
  reflection_model          VARCHAR(128) NOT NULL DEFAULT '',
  confidence                DECIMAL(4,3) NULL COMMENT '画像置信度 0~1',
  updated_at                DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_student (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生面试画像资产';

CREATE TABLE IF NOT EXISTS interview_followup_patterns (
  id                BIGINT        NOT NULL AUTO_INCREMENT,
  pattern_id        VARCHAR(64)   NOT NULL COMMENT '业务 ID',
  trigger_json      JSON          NOT NULL COMMENT '触发条件',
  followup_text     VARCHAR(1024) NOT NULL DEFAULT '',
  dimension         VARCHAR(64)   NOT NULL DEFAULT '',
  source_session_id VARCHAR(64)   NULL,
  milvus_collection VARCHAR(128)  NULL,
  milvus_vector_id  VARCHAR(128)  NULL,
  confidence        DECIMAL(4,3)  NULL,
  created_at        DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_pattern_id (pattern_id),
  KEY idx_dimension (dimension)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='追问模式资产库';

CREATE TABLE IF NOT EXISTS interview_cohort_insights (
  id               BIGINT       NOT NULL AUTO_INCREMENT,
  insight_id       VARCHAR(64)  NOT NULL,
  insight_type     VARCHAR(64)  NOT NULL COMMENT '如 weak_skill, role_match',
  pattern_json     JSON         NOT NULL,
  suggested_action VARCHAR(512) NOT NULL DEFAULT '',
  confidence       DECIMAL(4,3) NOT NULL DEFAULT 0.000,
  target_role      VARCHAR(256) NOT NULL DEFAULT '',
  created_at       DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_insight_id (insight_id),
  KEY idx_type_role (insight_type, target_role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='人群洞察资产';

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

CREATE TABLE IF NOT EXISTS interview_mq_consume_log (
  id             BIGINT       NOT NULL AUTO_INCREMENT,
  message_id     VARCHAR(64)  NOT NULL COMMENT 'MQ message_id',
  idempotency_key VARCHAR(192) NOT NULL DEFAULT '',
  event_type     VARCHAR(128) NOT NULL,
  consumer_group VARCHAR(128) NOT NULL,
  payload_digest VARCHAR(64)  NOT NULL DEFAULT '' COMMENT 'payload SHA256',
  processed_at   DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_message_id (message_id),
  KEY idx_idempotency (idempotency_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='RocketMQ 消费去重表';

CREATE TABLE IF NOT EXISTS interview_milvus_index_meta (
  id                BIGINT        NOT NULL AUTO_INCREMENT,
  plan_id           VARCHAR(64)   NOT NULL,
  plan_version      INT           NOT NULL,
  milvus_collection VARCHAR(128)  NOT NULL,
  milvus_vector_id  VARCHAR(128)  NOT NULL,
  material_hash     VARCHAR(64)   NOT NULL DEFAULT '',
  summary           VARCHAR(1024) NOT NULL DEFAULT '',
  created_at        DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_plan_vector (plan_id, plan_version, milvus_collection),
  KEY idx_material_hash (material_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试大纲向量索引元数据';

-- -----------------------------------------------------------------------------
-- 可选：行业分类初始数据（按需取消注释）
-- -----------------------------------------------------------------------------
-- INSERT INTO interview_industry_category
--   (category_id, parent_id, level, category_code, category_name, description, intent_keywords, sort_no)
-- VALUES
--   ('ind_internet', NULL, 1, 'internet', '互联网', '面向互联网产品/研发/运营类岗位', '', 10),
--   ('ind_finance',  NULL, 1, 'finance',  '金融',   '银行/证券/保险/金融科技', '', 20),
--   ('ind_backend',  'ind_internet', 2, 'backend_dev',  '后端开发',
--    'Java/Go/Python 服务端、数据库、缓存、微服务', '后端,java,go,spring', 10),
--   ('ind_frontend', 'ind_internet', 2, 'frontend_dev', '前端开发',
--    'Web/H5/小程序，Vue/React 工程化', '前端,vue,react', 20);
