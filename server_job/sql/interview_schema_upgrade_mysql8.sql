-- =============================================================================
-- ROLE005 面试表 — 已有库增量升级（按需执行；列已存在可忽略报错）
-- =============================================================================

SET NAMES utf8mb4;

-- 若从零部署请直接执行 interview_schema_mysql8.sql + interview_schema_v2_mysql8.sql
-- V1 interview_plans.summary_json 升级已废弃；迁移见 interview_schema_v2_upgrade_mysql8.sql
