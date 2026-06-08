CREATE TABLE `sys_code` (
  `ID` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'id',
  `FID` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '父级id',
  `NAME` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '字典内容',
  `DM` int DEFAULT NULL COMMENT '字典编码',
  `MC` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '类型名称',
  `BM` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '类型编码',
  `LBMC` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '类别名称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='字典表';


CREATE TABLE `t_biz_compary_info` (
  `WID` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'id',
  `dwzt` int DEFAULT NULL COMMENT '单位状态',
  `shsj` datetime DEFAULT NULL COMMENT '审核时间',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'logo',
  `drzh` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '登入账号',
  `gsmc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司名称',
  `jglx` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '机构类型',
  `zzjgdm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '组织机构代码',
  `dwxz` int DEFAULT NULL COMMENT '单位性质',
  `hylx` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '行业类型',
  `dwszsf` int DEFAULT NULL COMMENT '单位办公所在省份',
  `dwszcs` int DEFAULT NULL COMMENT '单位所在城市',
  `dwszdq` int DEFAULT NULL COMMENT '单位所在地区',
  `dwbgdz` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '单位办公地址',
  `gsgm` int DEFAULT NULL COMMENT '公司规模',
  `gszy` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司主业',
  `zczj` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '注册资金（单位：万元）',
  `dwzcdz` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '单位注册地址',
  `dwjj` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '单位简介',
  `lxr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人',
  `lxrch` int DEFAULT NULL COMMENT '联系人称呼',
  `lxrzw` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人职位',
  `lxrdh` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人电话',
  `lxrsjh` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人手机号',
  `lxrcz` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人传真',
  `lxrdzyj` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人电子邮件',
  `lxrqq` int DEFAULT NULL COMMENT '联系人qq',
  `lxrwx` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人微信',
  `yzbm` int DEFAULT NULL COMMENT '邮政编码',
  `dwzcsf` int DEFAULT NULL COMMENT '单位注册省份',
  `dwzccs` int DEFAULT NULL COMMENT '单位注册城市',
  `dwzcdq` int DEFAULT NULL COMMENT '单位注册地区',
  `clsj` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '成立时间',
  `djnf` int DEFAULT NULL COMMENT '登记年份',
  `shzt` int DEFAULT NULL COMMENT '审核状态',
  `dwyx` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '单位邮箱',
  `dwlx` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '单位类型',
  `nd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '年度'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='公司信息';


CREATE TABLE `t_biz_jobs_info` (
  `yrdw` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用人单位（关联 t_biz_compary_info.zzjgdm）',
  `jobid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位id',
  `zwmc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位名称',
  `xqrs` int DEFAULT NULL COMMENT '需求人数',
  `jzrq` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '截止日期',
  `zwlb` int DEFAULT NULL COMMENT '职位类别',
  `yxjb` int DEFAULT NULL COMMENT '月薪级别（job_yxjb.DM，展示单位：元）',
  `sxq` int DEFAULT NULL COMMENT '实习期（jpb_sxq.DM，展示单位：月）',
  `xbyq` int DEFAULT NULL COMMENT '性别要求',
  `gzszsf` int DEFAULT NULL COMMENT '工作所在省份',
  `gzszcs` int DEFAULT NULL COMMENT '工作所在城市',
  `gzszdq` int DEFAULT NULL COMMENT '工作所在地区',
  `lxryx` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人邮箱',
  `xlyq` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学历要求（job_xl.DM 逗号分隔）',
  `nlqx` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '能力需求（job_nl.DM 逗号分隔）',
  `sxsj` datetime DEFAULT NULL COMMENT '生效时间',
  `zt` int DEFAULT NULL COMMENT '状态',
  `lxrdh` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人电话',
  `lxrsjh` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人手机',
  `lxrqq` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人qq',
  `lxrwx` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人微信',
  `zwms` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '职位描述',
  `lxr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系人',
  `sfzm` int DEFAULT NULL COMMENT '是否招满',
  `nd` int DEFAULT NULL COMMENT '年度',
  `cjsj` datetime DEFAULT NULL COMMENT '创建时间',
  `gzdd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工作地点',
  `gjz` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '关键字（job_gjz.DM 逗号分隔）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='岗位信息';


CREATE TABLE `t_biz_jobs_rag_sync` (
  `jobid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '岗位id',
  `syn_rag` tinyint NOT NULL DEFAULT 0 COMMENT '0未同步 1已同步',
  `rag_md_path` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'GrepRAG Markdown 路径',
  `synced_at` datetime DEFAULT NULL COMMENT '最近同步成功时间',
  `updated_at` datetime DEFAULT NULL COMMENT '记录更新时间',
  PRIMARY KEY (`jobid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='岗位 RAG 同步状态（与 t_biz_jobs_info 按 jobid 关联）';