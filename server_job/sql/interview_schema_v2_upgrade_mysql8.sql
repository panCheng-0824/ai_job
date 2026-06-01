-- =============================================================================
-- ROLE005 面试表 — V1 → V2 增量升级（MySQL 8）
--
-- 前置：已执行过 interview_schema_mysql8.sql（存在 interview_plans 等 V1 表）
-- 目标：
--   1. 新建 V2 关系表（行业 / 大纲 / 学生记录）
--   2. 从 interview_plans.payload_json、summary_json 迁移至新表
--   3. 从 interview_sessions 补建 student_interview_records / student_interview_answers
--   4. 移除 interview_sessions.answers_json
--
-- 注意：
--   - 本脚本可重复执行部分步骤会 INSERT IGNORE / 跳过已存在列
--   - 迁移完成后 interview_plans 保留只读备份，确认无误后可手动 DROP
--   - 建议在低峰期执行并先备份数据库
-- =============================================================================

SET NAMES utf8mb4;

-- =============================================================================
-- 第一步：创建 V2 新表（与 interview_schema_v2_mysql8.sql 中 A~G 段一致）
-- =============================================================================

CREATE TABLE IF NOT EXISTS interview_industry_category (
  category_id          VARCHAR(32)   NOT NULL COMMENT '行业类目 ID',
  parent_id            VARCHAR(32)   NULL,
  level                TINYINT       NOT NULL COMMENT '1=一级 2=二级',
  category_code        VARCHAR(64)   NOT NULL,
  category_name        VARCHAR(128)  NOT NULL,
  description          VARCHAR(2000) NOT NULL DEFAULT '',
  intent_keywords      VARCHAR(1000) NOT NULL DEFAULT '',
  enabled_for_intent   TINYINT(1)    NOT NULL DEFAULT 1,
  enabled_for_classify TINYINT(1)    NOT NULL DEFAULT 1,
  sort_no              INT           NOT NULL DEFAULT 0,
  status               VARCHAR(16)   NOT NULL DEFAULT 'active',
  created_at           DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at           DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (category_id),
  KEY idx_parent_sort (parent_id, sort_no),
  KEY idx_level_intent (level, enabled_for_intent, status),
  KEY idx_level_classify (level, enabled_for_classify, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试行业分类';

CREATE TABLE IF NOT EXISTS interview_plan_basics (
  plan_row_id                  VARCHAR(96)   NOT NULL,
  plan_id                      VARCHAR(64)   NOT NULL,
  version                      INT           NOT NULL DEFAULT 1,
  title                        VARCHAR(256)  NOT NULL DEFAULT '',
  target_role                  VARCHAR(256)  NOT NULL DEFAULT '',
  introduction                 VARCHAR(2000) NOT NULL DEFAULT '',
  suitable_audience            VARCHAR(1000) NOT NULL DEFAULT '',
  industry_category_id         VARCHAR(32)   NULL,
  industry_classify_confidence DECIMAL(4,3)  NULL,
  industry_classify_reason     VARCHAR(1000) NOT NULL DEFAULT '',
  industry_classify_source     VARCHAR(32)   NOT NULL DEFAULT 'auto',
  industry_classified_at       DATETIME(3)   NULL,
  source_material_hash         VARCHAR(64)   NOT NULL DEFAULT '',
  rubric_version               VARCHAR(32)   NOT NULL DEFAULT 'v1',
  planner_model                VARCHAR(128)  NOT NULL DEFAULT '',
  question_count               INT           NOT NULL DEFAULT 0,
  estimated_minutes            INT           NOT NULL DEFAULT 0,
  visibility                   VARCHAR(32)   NOT NULL DEFAULT 'private',
  status                       VARCHAR(32)   NOT NULL DEFAULT 'published',
  cache_hit_id                 VARCHAR(64)   NULL,
  student_id                   VARCHAR(64)   NOT NULL DEFAULT '',
  created_at                   DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at                   DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (plan_row_id),
  UNIQUE KEY uk_plan_id_version (plan_id, version),
  KEY idx_student_created (student_id, created_at DESC),
  KEY idx_industry (industry_category_id, status),
  KEY idx_material_hash (source_material_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试大纲基础信息';

CREATE TABLE IF NOT EXISTS interview_plan_module_tags (
  id           BIGINT       NOT NULL AUTO_INCREMENT,
  plan_row_id  VARCHAR(96)  NOT NULL,
  tag_name     VARCHAR(128) NOT NULL,
  sort_no      INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_plan_row (plan_row_id, sort_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='大纲面试模块标签';

CREATE TABLE IF NOT EXISTS interview_plan_questions (
  iq_row_id        VARCHAR(128)  NOT NULL,
  plan_row_id      VARCHAR(96)   NOT NULL,
  plan_id          VARCHAR(64)   NOT NULL,
  plan_version     INT           NOT NULL,
  question_id      VARCHAR(64)   NOT NULL,
  seq_no           INT           NOT NULL,
  question_text    TEXT          NOT NULL,
  weight           DECIMAL(6,3)  NOT NULL DEFAULT 1.000,
  thinking_hint    VARCHAR(1024) NOT NULL DEFAULT '',
  timeout_seconds  INT           NOT NULL DEFAULT 300,
  reference_answer TEXT          NOT NULL,
  created_at       DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (iq_row_id),
  UNIQUE KEY uk_plan_question (plan_row_id, question_id),
  UNIQUE KEY uk_plan_seq (plan_row_id, seq_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='面试大纲题目';

CREATE TABLE IF NOT EXISTS interview_plan_question_dimensions (
  id             BIGINT       NOT NULL AUTO_INCREMENT,
  iq_row_id      VARCHAR(128) NOT NULL,
  dimension_code VARCHAR(64)  NOT NULL,
  sort_no        INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_iq (iq_row_id, sort_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='题目考察维度';

CREATE TABLE IF NOT EXISTS interview_plan_question_followups (
  id            BIGINT        NOT NULL AUTO_INCREMENT,
  iq_row_id     VARCHAR(128)  NOT NULL,
  seq_no        INT           NOT NULL,
  followup_text VARCHAR(1024) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_iq (iq_row_id, seq_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='题目预设追问';

CREATE TABLE IF NOT EXISTS interview_plan_question_criteria (
  id              BIGINT       NOT NULL AUTO_INCREMENT,
  iq_row_id       VARCHAR(128) NOT NULL,
  criterion_key   VARCHAR(64)  NOT NULL,
  criterion_value VARCHAR(512) NOT NULL,
  sort_no         INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_iq (iq_row_id, sort_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='题目评分标准';

CREATE TABLE IF NOT EXISTS student_interview_records (
  record_id             VARCHAR(64)  NOT NULL,
  student_id            VARCHAR(64)  NOT NULL,
  interview_session_id  VARCHAR(64)  NOT NULL,
  chat_session_id       VARCHAR(128) NULL,
  plan_id               VARCHAR(64)  NOT NULL,
  plan_version          INT          NOT NULL,
  industry_category_id  VARCHAR(32)  NULL,
  target_role           VARCHAR(256) NOT NULL DEFAULT '',
  plan_title            VARCHAR(256) NOT NULL DEFAULT '',
  session_status        VARCHAR(32)  NOT NULL DEFAULT 'ready',
  summary_status        VARCHAR(32)  NOT NULL DEFAULT 'pending',
  total_score           DECIMAL(6,2) NULL,
  report_id             VARCHAR(64)  NULL,
  question_total        INT          NOT NULL DEFAULT 0,
  question_answered     INT          NOT NULL DEFAULT 0,
  created_at            DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  summary_at            DATETIME(3)  NULL,
  completed_at          DATETIME(3)  NULL,
  PRIMARY KEY (record_id),
  UNIQUE KEY uk_session (interview_session_id),
  KEY idx_student_created (student_id, created_at DESC),
  KEY idx_student_summary (student_id, summary_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生面试总结记录';

CREATE TABLE IF NOT EXISTS student_interview_answers (
  answer_row_id         VARCHAR(64)   NOT NULL,
  interview_session_id  VARCHAR(64)   NOT NULL,
  student_id            VARCHAR(64)   NOT NULL,
  record_id             VARCHAR(64)   NOT NULL,
  plan_id               VARCHAR(64)   NOT NULL,
  plan_version          INT           NOT NULL,
  iq_row_id             VARCHAR(128)  NOT NULL,
  question_id           VARCHAR(64)   NOT NULL,
  seq_no                INT           NOT NULL,
  answer_status         VARCHAR(32)   NOT NULL DEFAULT 'pending',
  answer_text           TEXT          NULL,
  score                 DECIMAL(6,2)  NULL,
  evaluator_comment     VARCHAR(2000) NOT NULL DEFAULT '',
  turn_id               VARCHAR(64)   NULL,
  created_at            DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  answered_at           DATETIME(3)   NULL,
  summarized_at         DATETIME(3)   NULL,
  PRIMARY KEY (answer_row_id),
  UNIQUE KEY uk_session_question (interview_session_id, question_id),
  KEY idx_record_seq (record_id, seq_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生逐题答题记录';

-- =============================================================================
-- 第二步：从 interview_plans 迁移大纲基础信息
-- =============================================================================

INSERT IGNORE INTO interview_plan_basics (
  plan_row_id, plan_id, version, title, target_role,
  introduction, suitable_audience,
  source_material_hash, rubric_version, planner_model,
  question_count, status, cache_hit_id, student_id, created_at, updated_at
)
SELECT
  p.plan_row_id,
  p.plan_id,
  p.version,
  COALESCE(NULLIF(p.target_role, ''), p.plan_id) AS title,
  COALESCE(p.target_role, ''),
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(p.summary_json, '$.introduction')), ''),
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(p.summary_json, '$.suitable_audience')), ''),
  COALESCE(p.source_material_hash, ''),
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(p.payload_json, '$.rubric_version')), 'v1'),
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(p.payload_json, '$.planner_model')), COALESCE(p.planner_model, '')),
  COALESCE(JSON_LENGTH(JSON_EXTRACT(p.payload_json, '$.questions')), 0),
  'published',
  p.cache_hit_id,
  COALESCE(p.student_id, ''),
  p.created_at,
  p.created_at
FROM interview_plans p;

-- =============================================================================
-- 第三步：迁移模块标签（summary_json.interview_categories）
-- =============================================================================

INSERT IGNORE INTO interview_plan_module_tags (plan_row_id, tag_name, sort_no)
SELECT
  p.plan_row_id,
  jt.tag_name,
  jt.sort_no - 1
FROM interview_plans p
CROSS JOIN JSON_TABLE(
  COALESCE(p.summary_json, JSON_OBJECT('interview_categories', JSON_ARRAY())),
  '$.interview_categories[*]'
  COLUMNS (
    sort_no FOR ORDINALITY,
    tag_name VARCHAR(128) PATH '$'
  )
) AS jt
WHERE p.summary_json IS NOT NULL
  AND JSON_TYPE(JSON_EXTRACT(p.summary_json, '$.interview_categories')) = 'ARRAY';

-- =============================================================================
-- 第四步：迁移题目主表（payload_json.questions）
-- iq_row_id 规则：plan_row_id + '#' + question_id
-- =============================================================================

INSERT IGNORE INTO interview_plan_questions (
  iq_row_id, plan_row_id, plan_id, plan_version,
  question_id, seq_no, question_text, weight,
  thinking_hint, timeout_seconds, reference_answer, created_at
)
SELECT
  CONCAT(p.plan_row_id, '#', jt.question_id) AS iq_row_id,
  p.plan_row_id,
  p.plan_id,
  p.version,
  jt.question_id,
  jt.seq_no - 1 AS seq_no,
  COALESCE(jt.question_text, ''),
  COALESCE(jt.weight, 1.000),
  COALESCE(jt.thinking_hint, ''),
  COALESCE(jt.timeout_seconds, 300),
  COALESCE(jt.reference_answer, ''),
  p.created_at
FROM interview_plans p
CROSS JOIN JSON_TABLE(
  p.payload_json,
  '$.questions[*]'
  COLUMNS (
    seq_no FOR ORDINALITY,
    question_id      VARCHAR(64)   PATH '$.id',
    question_text    TEXT          PATH '$.text',
    weight           DECIMAL(6,3)  PATH '$.weight',
    thinking_hint    VARCHAR(1024) PATH '$.thinking_hint',
    timeout_seconds  INT           PATH '$.timeout_seconds',
    reference_answer TEXT          PATH '$.reference_answer'
  )
) AS jt
WHERE JSON_TYPE(JSON_EXTRACT(p.payload_json, '$.questions')) = 'ARRAY';

-- =============================================================================
-- 第五步：迁移题目维度（questions[].dimensions）
-- =============================================================================

INSERT IGNORE INTO interview_plan_question_dimensions (iq_row_id, dimension_code, sort_no)
SELECT
  CONCAT(p.plan_row_id, '#', jt.question_id) AS iq_row_id,
  jt.dimension_code,
  jt.sort_no - 1
FROM interview_plans p
CROSS JOIN JSON_TABLE(
  p.payload_json,
  '$.questions[*]'
  COLUMNS (
    question_id VARCHAR(64) PATH '$.id',
    NESTED PATH '$.dimensions[*]' COLUMNS (
      sort_no FOR ORDINALITY,
      dimension_code VARCHAR(64) PATH '$'
    )
  )
) AS jt
WHERE jt.dimension_code IS NOT NULL AND jt.dimension_code != '';

-- =============================================================================
-- 第六步：迁移预设追问（questions[].preset_followups）
-- =============================================================================

INSERT IGNORE INTO interview_plan_question_followups (iq_row_id, seq_no, followup_text)
SELECT
  CONCAT(p.plan_row_id, '#', jt.question_id) AS iq_row_id,
  jt.sort_no - 1,
  jt.followup_text
FROM interview_plans p
CROSS JOIN JSON_TABLE(
  p.payload_json,
  '$.questions[*]'
  COLUMNS (
    question_id VARCHAR(64) PATH '$.id',
    NESTED PATH '$.preset_followups[*]' COLUMNS (
      sort_no FOR ORDINALITY,
      followup_text VARCHAR(1024) PATH '$'
    )
  )
) AS jt
WHERE jt.followup_text IS NOT NULL AND jt.followup_text != '';

-- =============================================================================
-- 第七步：迁移评分标准（questions[].eval_criteria 对象的 key-value）
-- MySQL JSON_TABLE 对动态 object key 需逐行展开；此处用常见结构迁移
-- =============================================================================

INSERT IGNORE INTO interview_plan_question_criteria (iq_row_id, criterion_key, criterion_value, sort_no)
SELECT
  iq_row_id,
  criterion_key,
  criterion_value,
  ROW_NUMBER() OVER (PARTITION BY iq_row_id ORDER BY criterion_key) - 1 AS sort_no
FROM (
  SELECT
    CONCAT(p.plan_row_id, '#', jt.question_id) AS iq_row_id,
    ck.criterion_key,
    COALESCE(JSON_UNQUOTE(JSON_EXTRACT(jt.eval_criteria, CONCAT('$.', ck.criterion_key))), '') AS criterion_value
  FROM interview_plans p
  CROSS JOIN JSON_TABLE(
    p.payload_json,
    '$.questions[*]'
    COLUMNS (
      question_id   VARCHAR(64) PATH '$.id',
      eval_criteria JSON        PATH '$.eval_criteria'
    )
  ) AS jt
  CROSS JOIN JSON_TABLE(
    JSON_KEYS(COALESCE(jt.eval_criteria, JSON_OBJECT())),
    '$[*]' COLUMNS (criterion_key VARCHAR(64) PATH '$')
  ) AS ck
  WHERE jt.eval_criteria IS NOT NULL
    AND JSON_TYPE(jt.eval_criteria) = 'OBJECT'
) AS expanded
WHERE criterion_value != '';

-- =============================================================================
-- 第八步：为已有 interview_sessions 补建 student_interview_records
-- record_id 规则：irec_ + session_id 去掉 isess_ 前缀后的部分（保持可追溯）
-- =============================================================================

INSERT IGNORE INTO student_interview_records (
  record_id, student_id, interview_session_id, chat_session_id,
  plan_id, plan_version, industry_category_id, target_role, plan_title,
  session_status, summary_status, total_score, report_id,
  question_total, question_answered, created_at, summary_at, completed_at
)
SELECT
  CONCAT('irec_', SUBSTRING(s.interview_session_id, 7)) AS record_id,
  s.student_id,
  s.interview_session_id,
  s.chat_session_id,
  s.plan_id,
  s.plan_version,
  b.industry_category_id,
  COALESCE(b.target_role, ''),
  COALESCE(b.title, b.target_role, s.plan_id),
  s.status,
  CASE WHEN s.report_id IS NOT NULL THEN 'summarized' ELSE 'pending' END,
  r.total_score,
  s.report_id,
  COALESCE(b.question_count, 0),
  0,
  s.created_at,
  r.generated_at,
  s.completed_at
FROM interview_sessions s
LEFT JOIN interview_plan_basics b
  ON b.plan_id = s.plan_id AND b.version = s.plan_version
LEFT JOIN interview_reports r
  ON r.interview_session_id = s.interview_session_id;

-- =============================================================================
-- 第九步：为每个 session 按大纲题目预生成答题行，并从 answers_json 回填
-- =============================================================================

-- 9a. 按大纲题目预生成 pending 行
INSERT IGNORE INTO student_interview_answers (
  answer_row_id, interview_session_id, student_id, record_id,
  plan_id, plan_version, iq_row_id, question_id, seq_no,
  answer_status, created_at
)
SELECT
  CONCAT('ians_', SUBSTRING(s.interview_session_id, 7), '_', q.question_id) AS answer_row_id,
  s.interview_session_id,
  s.student_id,
  CONCAT('irec_', SUBSTRING(s.interview_session_id, 7)) AS record_id,
  s.plan_id,
  s.plan_version,
  q.iq_row_id,
  q.question_id,
  q.seq_no,
  'pending',
  s.created_at
FROM interview_sessions s
JOIN interview_plan_questions q
  ON q.plan_id = s.plan_id AND q.plan_version = s.plan_version;

-- 9b. 从 answers_json 回填（兼容多种字段名：text / final_answer / answer_text）
-- 须在 DROP answers_json 之前执行
UPDATE student_interview_answers a
INNER JOIN interview_sessions s
  ON s.interview_session_id = a.interview_session_id
INNER JOIN JSON_TABLE(
  COALESCE(s.answers_json, JSON_ARRAY()),
  '$[*]'
  COLUMNS (
    question_id  VARCHAR(64) PATH '$.question_id',
    qid          VARCHAR(64) PATH '$.id',
    answer_text  TEXT        PATH '$.final_answer',
    text_val     TEXT        PATH '$.text',
    answer_val   TEXT        PATH '$.answer_text',
    score        DECIMAL(6,2) PATH '$.score'
  )
) AS jt ON COALESCE(jt.question_id, jt.qid) = a.question_id
LEFT JOIN interview_reports r
  ON r.interview_session_id = s.interview_session_id
SET
  a.answer_text = COALESCE(
    NULLIF(jt.answer_text, ''),
    NULLIF(jt.text_val, ''),
    jt.answer_val
  ),
  a.score = jt.score,
  a.answer_status = CASE WHEN s.report_id IS NOT NULL THEN 'summarized' ELSE 'answered' END,
  a.answered_at = COALESCE(a.answered_at, s.updated_at),
  a.summarized_at = CASE WHEN s.report_id IS NOT NULL THEN r.generated_at ELSE NULL END
WHERE JSON_LENGTH(COALESCE(s.answers_json, JSON_ARRAY())) > 0;

-- 9c. 更新 question_answered 计数
UPDATE student_interview_records rec
SET question_answered = (
  SELECT COUNT(*)
  FROM student_interview_answers ans
  WHERE ans.record_id = rec.record_id
    AND ans.answer_status IN ('answered', 'summarized')
);

-- =============================================================================
-- 第十步：移除 interview_sessions.answers_json（V2 改查 student_interview_answers）
-- 若列已不存在会报错，可忽略
-- =============================================================================

ALTER TABLE interview_sessions
  DROP COLUMN answers_json;

-- =============================================================================
-- 完成提示
-- =============================================================================
-- 迁移后建议人工校验：
--   SELECT COUNT(*) FROM interview_plans;
--   SELECT COUNT(*) FROM interview_plan_basics;
--   SELECT COUNT(*) FROM interview_plan_questions;
--   SELECT COUNT(*) FROM student_interview_records;
-- 确认无误后可择机：DROP TABLE interview_plans;
