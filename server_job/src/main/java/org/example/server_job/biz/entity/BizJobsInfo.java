package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 岗位信息表 {@code t_biz_jobs_info} 实体（0605 新 schema）。
 */
@Data
@TableName("t_biz_jobs_info")
public class BizJobsInfo {

    /** 用人单位，存 {@code t_biz_compary_info.zzjgdm}（组织机构代码）。 */
    @TableField("yrdw")
    private String yrdw;

    @TableId("jobid")
    private String jobid;

    @TableField("zwmc")
    private String zwmc;

    @TableField("xqrs")
    private Integer xqrs;

    @TableField("jzrq")
    private String jzrq;

    @TableField("zwlb")
    private Integer zwlb;

    @TableField("yxjb")
    /** 月薪级别，{@code job_yxjb.DM}，展示单位元 */
    private Integer yxjb;

    @TableField("sxq")
    /** 实习期，{@code jpb_sxq.DM}，展示单位月 */
    private Integer sxq;

    @TableField("xbyq")
    private Integer xbyq;

    @TableField("gzszsf")
    private Integer gzszsf;

    @TableField("gzszcs")
    private Integer gzszcs;

    @TableField("gzszdq")
    private Integer gzszdq;

    @TableField("lxryx")
    private String lxryx;

    @TableField("xlyq")
    /** 学历要求，逗号分隔的 {@code job_xl.DM} */
    private String xlyq;

    @TableField("nlqx")
    /** 能力需求，逗号分隔的 {@code job_nl.DM} */
    private String nlqx;

    @TableField("sxsj")
    private LocalDateTime sxsj;

    @TableField("zt")
    private Integer zt;

    @TableField("lxrdh")
    private String lxrdh;

    @TableField("lxrsjh")
    private String lxrsjh;

    @TableField("lxrqq")
    private String lxrqq;

    @TableField("lxrwx")
    private String lxrwx;

    @TableField("zwms")
    /** 职位描述（富文本 HTML） */
    private String zwms;

    @TableField("lxr")
    private String lxr;

    @TableField("sfzm")
    private Integer sfzm;

    @TableField("nd")
    private Integer nd;

    @TableField("cjsj")
    private LocalDateTime cjsj;

    @TableField("gzdd")
    private String gzdd;

    /** 关键字，逗号分隔的 {@code job_gjz.DM} */
    @TableField("gjz")
    private String gjz;
}
