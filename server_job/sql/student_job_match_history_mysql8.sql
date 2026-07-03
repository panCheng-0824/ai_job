-- =============================================================================
-- 学生智能匹配历史（MySQL 8）
-- 应用侧：server_job（MyBatis）读写；按 created_at 倒序分页查询，默认每页 8 条。
-- =============================================================================

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS student_job_match_history (
  id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  student_id            VARCHAR(64)     NOT NULL COMMENT '学号',
  query_text            VARCHAR(2000)   NOT NULL COMMENT '岗位诉求原文',
  settings_json         JSON            NOT NULL COMMENT '匹配设置（权重、最低分、top_n 等）',
  jobs_json             JSON            NOT NULL COMMENT '匹配到的岗位列表',
  recommendation_json   JSON            NULL COMMENT '推荐理由结构化数据',
  job_count             INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '岗位数量',
  created_at            DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '匹配完成时间',
  PRIMARY KEY (id),
  KEY idx_student_created (student_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生智能匹配历史';
