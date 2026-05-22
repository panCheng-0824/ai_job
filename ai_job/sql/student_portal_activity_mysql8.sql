-- =============================================================================
-- 学生门户：收藏岗位、关注企业、评价岗位/企业（MySQL 8）
-- 应用侧：由 server_job（MyBatis）读写本脚本中的表；ai_job 不再包含学生活动持久化逻辑。
--
--   PORTAL_DB_HOST      必填（与 PORTAL_ACTIVITY_BACKEND=json 互斥）
--   PORTAL_DB_PORT      默认 3306
--   PORTAL_DB_USER      必填
--   PORTAL_DB_PASSWORD  可空
--   PORTAL_DB_NAME      必填（库名）
--   PORTAL_DB_CHARSET   默认 utf8mb4
--   PORTAL_ACTIVITY_BACKEND=mysql  可选，强制走库
--
-- 评价标签：独立关联表（非 JSON 列），便于按企业统计标签分布。
-- 每人每岗 / 每企业仅一条评价（UNIQUE），可更新；删除评价会级联删除标签行。
-- =============================================================================

SET NAMES utf8mb4;

-- -----------------------------------------------------------------------------
-- 1. 收藏岗位
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_favorite_job (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  student_id    VARCHAR(64)     NOT NULL COMMENT '学号，对应 user_student.student_id',
  job_id        VARCHAR(64)     NOT NULL COMMENT '岗位编号，对应 business_job.job_id',
  created_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '收藏时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_student_job (student_id, job_id),
  KEY idx_student (student_id),
  KEY idx_job (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生收藏岗位';

-- -----------------------------------------------------------------------------
-- 2. 关注企业（用于企业画像：关注人数 COUNT 本表 WHERE credit_code）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_follow_company (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  student_id    VARCHAR(64)     NOT NULL COMMENT '学号',
  credit_code   VARCHAR(32)     NOT NULL COMMENT '统一社会信用代码，对应 user_business.credit_code',
  created_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '关注时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_student_company (student_id, credit_code),
  KEY idx_student (student_id),
  KEY idx_company (credit_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生关注企业';

-- -----------------------------------------------------------------------------
-- 3. 评价岗位（每人每岗一条，可 UPDATE；删除走 DELETE）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_job_review (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  student_id    VARCHAR(64)     NOT NULL COMMENT '学号',
  job_id        VARCHAR(64)     NOT NULL COMMENT '岗位编号',
  stars         TINYINT UNSIGNED NOT NULL COMMENT '1～5 星',
  comment       VARCHAR(2000)   NOT NULL DEFAULT '' COMMENT '文字评价',
  created_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '首次提交时间',
  updated_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '最后更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_student_job (student_id, job_id),
  KEY idx_job (job_id),
  KEY idx_student (student_id),
  CONSTRAINT chk_job_stars CHECK (stars BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生对岗位的评价';

-- -----------------------------------------------------------------------------
-- 4. 岗位评价 — 标签（多对一关联 student_job_review.id）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_job_review_tag (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  job_review_id   BIGINT UNSIGNED NOT NULL COMMENT 'student_job_review.id',
  tag_id          VARCHAR(64)     NOT NULL COMMENT '标签 id，与 config/review_tags.json 中 job_review_tags 一致',
  PRIMARY KEY (id),
  UNIQUE KEY uk_review_tag (job_review_id, tag_id),
  KEY idx_tag (tag_id),
  CONSTRAINT fk_job_rev_tag_review FOREIGN KEY (job_review_id) REFERENCES student_job_review (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='岗位评价所选标签';

-- -----------------------------------------------------------------------------
-- 5. 评价企业
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_company_review (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  student_id    VARCHAR(64)     NOT NULL COMMENT '学号',
  credit_code   VARCHAR(32)     NOT NULL COMMENT '统一社会信用代码',
  stars         TINYINT UNSIGNED NOT NULL COMMENT '1～5 星',
  comment       VARCHAR(2000)   NOT NULL DEFAULT '' COMMENT '文字评价',
  created_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '首次提交时间',
  updated_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '最后更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_student_company (student_id, credit_code),
  KEY idx_company (credit_code),
  KEY idx_student (student_id),
  CONSTRAINT chk_company_stars CHECK (stars BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生对企业的评价';

-- -----------------------------------------------------------------------------
-- 6. 企业评价 — 标签（用于企业画像：按 credit_code JOIN 后 GROUP BY tag_id）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_company_review_tag (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  company_review_id   BIGINT UNSIGNED NOT NULL COMMENT 'student_company_review.id',
  tag_id              VARCHAR(64)     NOT NULL COMMENT '标签 id，与 config/review_tags.json 中 company_review_tags 一致',
  PRIMARY KEY (id),
  UNIQUE KEY uk_review_tag (company_review_id, tag_id),
  KEY idx_tag (tag_id),
  CONSTRAINT fk_co_rev_tag_review FOREIGN KEY (company_review_id) REFERENCES student_company_review (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='企业评价所选标签';

-- =============================================================================
-- 已有库升级（曾使用 tags_json 的旧表）
-- =============================================================================
-- 1) 若尚无标签子表，执行上文 CREATE TABLE IF NOT EXISTS student_*_review_tag。
-- 2) 将 JSON 标签迁入子表（需 MySQL 8.0.4+ 且 tags_json 为合法 JSON 数组）：
--
-- INSERT IGNORE INTO student_job_review_tag (job_review_id, tag_id)
-- SELECT j.id, jt.t
-- FROM student_job_review j
-- JOIN JSON_TABLE(
--   IF(JSON_VALID(j.tags_json), j.tags_json, JSON_ARRAY()),
--   '$[*]' COLUMNS (t VARCHAR(64) PATH '$')
-- ) AS jt;
--
-- INSERT IGNORE INTO student_company_review_tag (company_review_id, tag_id)
-- SELECT r.id, jt.t
-- FROM student_company_review r
-- JOIN JSON_TABLE(
--   IF(JSON_VALID(r.tags_json), r.tags_json, JSON_ARRAY()),
--   '$[*]' COLUMNS (t VARCHAR(64) PATH '$')
-- ) AS jt;
--
-- 3) 删除旧列（确认数据已迁后再执行）：
-- ALTER TABLE student_job_review DROP COLUMN tags_json;
-- ALTER TABLE student_company_review DROP COLUMN tags_json;
