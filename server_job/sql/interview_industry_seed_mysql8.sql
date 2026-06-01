-- =============================================================================
-- 行业分类种子数据（可选，开发/演示用）
-- 执行前需已创建 interview_industry_category 表（见 interview_schema_v2_mysql8.sql）
-- =============================================================================

SET NAMES utf8mb4;

INSERT IGNORE INTO interview_industry_category
  (category_id, parent_id, level, category_code, category_name, description, intent_keywords, enabled_for_intent, enabled_for_classify, sort_no, status)
VALUES
  ('ind_internet', NULL, 1, 'internet', '互联网', '面向互联网产品/研发/运营类岗位', '', 1, 1, 10, 'active'),
  ('ind_finance', NULL, 1, 'finance', '金融', '银行/证券/保险/金融科技', '', 1, 1, 20, 'active'),
  ('ind_backend', 'ind_internet', 2, 'backend_dev', '后端开发',
   'Java/Go/Python 服务端、数据库、缓存、微服务', '后端,java,go,spring', 1, 1, 10, 'active'),
  ('ind_frontend', 'ind_internet', 2, 'frontend_dev', '前端开发',
   'Web/H5/小程序，Vue/React 工程化', '前端,vue,react', 1, 1, 20, 'active');
