-- =============================================================================
-- ROLE005 面试表 — 删除 V1 大纲表 interview_plans
--
-- 前置：已执行 interview_schema_v2_upgrade_mysql8.sql 并完成数据校验
-- 说明：应用代码已不再读写 interview_plans，本脚本仅清理遗留表结构
-- =============================================================================

SET NAMES utf8mb4;

DROP TABLE IF EXISTS interview_plans;
