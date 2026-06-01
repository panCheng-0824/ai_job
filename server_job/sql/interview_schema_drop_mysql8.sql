-- =============================================================================
-- ROLE005 面试表 — 开发环境回滚（DROP，慎用生产）
-- 删除顺序：先子表后主表
-- =============================================================================

SET NAMES utf8mb4;

-- V2 学生记录与大纲子表（先删子表）
DROP TABLE IF EXISTS student_interview_answers;
DROP TABLE IF EXISTS student_interview_records;
DROP TABLE IF EXISTS interview_plan_question_criteria;
DROP TABLE IF EXISTS interview_plan_question_followups;
DROP TABLE IF EXISTS interview_plan_question_dimensions;
DROP TABLE IF EXISTS interview_plan_questions;
DROP TABLE IF EXISTS interview_plan_module_tags;
DROP TABLE IF EXISTS interview_plan_basics;
DROP TABLE IF EXISTS interview_industry_category;

DROP TABLE IF EXISTS interview_milvus_index_meta;
DROP TABLE IF EXISTS interview_mq_consume_log;
DROP TABLE IF EXISTS interview_review_queue;
DROP TABLE IF EXISTS interview_cohort_insights;
DROP TABLE IF EXISTS interview_followup_patterns;
DROP TABLE IF EXISTS student_interview_profiles;
DROP TABLE IF EXISTS interview_audit_logs;
DROP TABLE IF EXISTS interview_reports;
DROP TABLE IF EXISTS interview_turns;
DROP TABLE IF EXISTS interview_sessions;
DROP TABLE IF EXISTS interview_plans;
