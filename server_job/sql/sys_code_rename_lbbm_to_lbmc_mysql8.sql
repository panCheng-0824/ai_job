-- sys_code：LBBM → LBMC（类别名称字段更名）
-- 已有库按需执行；列已是 LBMC 可忽略报错

SET NAMES utf8mb4;

ALTER TABLE `sys_code`
    CHANGE COLUMN `LBBM` `LBMC` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '类别名称';
