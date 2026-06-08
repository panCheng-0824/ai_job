-- =============================================================================
-- 业务数据清空脚本（MySQL 8）
--
-- 删除范围：
--   1. 岗位、企业主数据（t_biz_jobs_info / t_biz_company_info）
--   2. 学生关注/收藏/评价（岗位、企业）
--   3. 学生简历及全部副本（student_resume）
--   4. 学生面试相关（会话、答题、报告、大纲等）
--
-- 保留（不删）：
--   - t_biz_student_info 等学生档案
--   - interview_industry_category 行业分类种子
--   - interview_followup_patterns / interview_cohort_insights 系统资产
--   - t_chat_session / t_chat_message 聊天记录
--
-- 用法：
--   mysql -h127.0.0.1 -uroot -p app_db < sql/purge_business_data_mysql8.sql
-- 或：
--   bash scripts/run_purge_business_data.sh --execute
--
-- 警告：不可恢复，执行前请备份数据库。
-- =============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

START TRANSACTION;

-- ---------------------------------------------------------------------------
-- 0. 删除前计数（便于核对）
-- ---------------------------------------------------------------------------
SELECT 'BEFORE' AS phase,
       (SELECT COUNT(*) FROM t_biz_jobs_info)              AS jobs,
       (SELECT COUNT(*) FROM t_biz_compary_info)           AS companies,
       (SELECT COUNT(*) FROM student_favorite_job)       AS favorite_jobs,
       (SELECT COUNT(*) FROM student_follow_company)       AS follow_companies,
       (SELECT COUNT(*) FROM student_job_review)           AS job_reviews,
       (SELECT COUNT(*) FROM student_company_review)       AS company_reviews,
       (SELECT COUNT(*) FROM student_resume)               AS resume_copies,
       (SELECT COUNT(*) FROM student_interview_records)    AS interview_records,
       (SELECT COUNT(*) FROM interview_sessions)           AS interview_sessions;

-- ---------------------------------------------------------------------------
-- 1. 学生 ↔ 岗位/企业 关联（先删标签子表）
-- ---------------------------------------------------------------------------
DELETE FROM student_job_review_tag;
DELETE FROM student_job_review;
DELETE FROM student_company_review_tag;
DELETE FROM student_company_review;
DELETE FROM student_favorite_job;
DELETE FROM student_follow_company;

-- ---------------------------------------------------------------------------
-- 2. 学生面试数据（先子表后主表）
-- ---------------------------------------------------------------------------
DELETE FROM student_interview_answers;
DELETE FROM student_interview_records;
DELETE FROM interview_review_queue;
DELETE FROM interview_turns;
DELETE FROM interview_reports;
DELETE FROM interview_audit_logs;
DELETE FROM interview_sessions;
DELETE FROM student_interview_profiles;

-- 学生生成的大纲及题目附属表
DELETE FROM interview_plan_question_criteria;
DELETE FROM interview_plan_question_followups;
DELETE FROM interview_plan_question_dimensions;
DELETE FROM interview_plan_questions;
DELETE FROM interview_plan_module_tags;
DELETE FROM interview_plan_basics;
DELETE FROM interview_milvus_index_meta;
DELETE FROM interview_mq_consume_log;

-- V1 遗留表（若存在则清空；不存在可忽略报错或手动注释）
-- DELETE FROM interview_plans;

-- ---------------------------------------------------------------------------
-- 3. 学生简历（含全部 series 与副本）
-- ---------------------------------------------------------------------------
DELETE FROM student_resume;

-- ---------------------------------------------------------------------------
-- 4. 岗位、企业主数据
-- ---------------------------------------------------------------------------
DELETE FROM t_biz_jobs_info;
DELETE FROM t_biz_jobs_rag_sync;
DELETE FROM t_biz_compary_info;

-- ---------------------------------------------------------------------------
-- 5. 删除后计数
-- ---------------------------------------------------------------------------
SELECT 'AFTER' AS phase,
       (SELECT COUNT(*) FROM t_biz_jobs_info)              AS jobs,
       (SELECT COUNT(*) FROM t_biz_compary_info)           AS companies,
       (SELECT COUNT(*) FROM student_favorite_job)       AS favorite_jobs,
       (SELECT COUNT(*) FROM student_follow_company)       AS follow_companies,
       (SELECT COUNT(*) FROM student_job_review)           AS job_reviews,
       (SELECT COUNT(*) FROM student_company_review)       AS company_reviews,
       (SELECT COUNT(*) FROM student_resume)               AS resume_copies,
       (SELECT COUNT(*) FROM student_interview_records)    AS interview_records,
       (SELECT COUNT(*) FROM interview_sessions)           AS interview_sessions;

COMMIT;

SET FOREIGN_KEY_CHECKS = 1;
