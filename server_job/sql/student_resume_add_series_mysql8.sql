-- 已有库升级：增加 series_id，用于「同一学号多份简历、每份简历多条副本」归组。
-- 若列或索引已存在，请勿重复执行本脚本。
SET NAMES utf8mb4;

ALTER TABLE student_resume
  ADD COLUMN series_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '一份逻辑简历的标识；同学号可有多个不同 series_id' AFTER student_id;

UPDATE student_resume SET series_id = id WHERE series_id = '' OR series_id IS NULL;

ALTER TABLE student_resume
  ADD KEY idx_student_series (student_id, series_id);
