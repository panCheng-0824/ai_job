-- 学生岗位投递表（与 ai_job/sql/student_portal_activity_mysql8.sql 第 7 节一致）
CREATE TABLE IF NOT EXISTS student_job_application (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  student_id    VARCHAR(64)     NOT NULL COMMENT '学号',
  job_id        VARCHAR(64)     NOT NULL COMMENT '岗位编号',
  resume_id     VARCHAR(64)     NULL COMMENT '投递时使用的简历副本 id',
  source        VARCHAR(32)     NOT NULL DEFAULT 'one_click' COMMENT '投递来源',
  created_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '投递时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_student_job (student_id, job_id),
  KEY idx_student (student_id),
  KEY idx_job (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生岗位投递记录';
