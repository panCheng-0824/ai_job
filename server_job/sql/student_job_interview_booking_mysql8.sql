-- 学生岗位面试预约（每人每岗一条，预约面试写入）
CREATE TABLE IF NOT EXISTS student_job_interview_booking (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  student_id    VARCHAR(64)     NOT NULL COMMENT '学号',
  job_id        VARCHAR(64)     NOT NULL COMMENT '岗位编号',
  job_title     VARCHAR(256)    NOT NULL DEFAULT '' COMMENT '岗位名称（冗余）',
  company_name  VARCHAR(256)    NOT NULL DEFAULT '' COMMENT '企业名称（冗余）',
  source        VARCHAR(32)     NOT NULL DEFAULT 'job_card' COMMENT '预约来源',
  created_at    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '预约时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_student_job (student_id, job_id),
  KEY idx_student (student_id),
  KEY idx_job (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生岗位面试预约';
