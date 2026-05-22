-- 简历副本：增加「本简历线默认」标记（与全局 is_default 对话默认区分）
SET NAMES utf8mb4;

ALTER TABLE student_resume
  ADD COLUMN is_series_default TINYINT(1) NOT NULL DEFAULT 0
    COMMENT '该 series 下默认使用的副本（每学号每 series 至多一条为 1）'
    AFTER is_default;

-- 每条 series 将最近更新的副本标为本简历默认
UPDATE student_resume r
INNER JOIN (
  SELECT student_id, series_id, SUBSTRING_INDEX(
    GROUP_CONCAT(id ORDER BY updated_at DESC),
    ',', 1
  ) AS pick_id
  FROM student_resume
  GROUP BY student_id, series_id
) t ON r.id = t.pick_id
SET r.is_series_default = 1;
