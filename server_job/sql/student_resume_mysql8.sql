-- =============================================================================
-- 学生简历持久化（MySQL 8）
-- 由 server_job（MyBatis-Plus）读写；与 web_job「创建简历」字段对齐。
-- 模型：同一学号（student_id）可有多份逻辑简历；每份简历以 series_id 标识，其下可存多条带时间戳的副本（每行 id 一条副本）。
-- content_json：{ "basic": {}, "intent": {}, "sections": {}, "extraNotes": "" }
-- =============================================================================

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS student_resume (
  id            VARCHAR(64)     NOT NULL COMMENT '单条版本（副本）UUID',
  student_id    VARCHAR(64)     NOT NULL COMMENT '学号，与门户 student_id 一致',
  series_id     VARCHAR(64)     NOT NULL COMMENT '一份逻辑简历的标识；同学号可有多个不同 series_id',
  template_id   VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '模版 id',
  display_name  VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '副本展示名（常含 _yyyyMMddHHmmss 后缀）',
  content_json  JSON            NOT NULL COMMENT '该副本的正文 JSON',
  is_default    TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '学号下对话/规划师引用的全局默认副本',
  is_series_default TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '同一 series_id 下默认加载的副本',
  created_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_student_updated (student_id, updated_at DESC),
  KEY idx_student_series (student_id, series_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生简历副本表：学号多简历、每简历多副本（按 series_id 归组）';
