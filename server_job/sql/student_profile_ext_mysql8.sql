-- =============================================================================
-- 学生自助画像扩展（MySQL 8）
-- 与 t_biz_* 学籍数据合并展示；学生可维护联系方式、求职意向、能力标签等。
-- =============================================================================

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS student_profile_ext (
  student_id            VARCHAR(64)     NOT NULL COMMENT '学号',
  phone                 VARCHAR(32)     NULL COMMENT '手机',
  email                 VARCHAR(128)    NULL COMMENT '邮箱',
  avatar_url            VARCHAR(512)    NULL COMMENT '头像 URL',
  campus_experience     TEXT            NULL COMMENT '校园经历补充说明',
  job_intent_json       JSON            NOT NULL COMMENT '求职意向',
  ability_json          JSON            NOT NULL COMMENT '能力标签与雷达',
  created_at            DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at            DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学生自助画像扩展（与学籍合并展示）';
