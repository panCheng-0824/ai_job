package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 企业信息表 {@code t_biz_compary_info} 实体（0605 新 schema）。
 */
@Data
@TableName("t_biz_compary_info")
public class BizCompanyInfo {

    @TableId("WID")
    private String wid;

    @TableField("dwzt")
    private Integer dwzt;

    @TableField("shsj")
    private LocalDateTime shsj;

    @TableField("logo")
    private String logo;

    @TableField("drzh")
    private String drzh;

    @TableField("gsmc")
    private String gsmc;

    @TableField("jglx")
    private String jglx;

    @TableField("zzjgdm")
    private String zzjgdm;

    @TableField("dwxz")
    private Integer dwxz;

    @TableField("hylx")
    private String hylx;

    @TableField("dwszsf")
    private Integer dwszsf;

    @TableField("dwszcs")
    private Integer dwszcs;

    @TableField("dwszdq")
    private Integer dwszdq;

    @TableField("dwbgdz")
    private String dwbgdz;

    @TableField("gsgm")
    private Integer gsgm;

    @TableField("gszy")
    private String gszy;

    @TableField("zczj")
    /** 注册资金，单位：万元 */
    private String zczj;

    @TableField("dwzcdz")
    private String dwzcdz;

    @TableField("dwjj")
    /** 单位简介（富文本 HTML） */
    private String dwjj;

    @TableField("lxr")
    private String lxr;

    @TableField("lxrch")
    private Integer lxrch;

    @TableField("lxrzw")
    private String lxrzw;

    @TableField("lxrdh")
    private String lxrdh;

    @TableField("lxrsjh")
    private String lxrsjh;

    @TableField("lxrcz")
    private String lxrcz;

    @TableField("lxrdzyj")
    private String lxrdzyj;

    @TableField("lxrqq")
    private Integer lxrqq;

    @TableField("lxrwx")
    private String lxrwx;

    @TableField("yzbm")
    private Integer yzbm;

    @TableField("dwzcsf")
    private Integer dwzcsf;

    @TableField("dwzccs")
    private Integer dwzccs;

    @TableField("dwzcdq")
    private Integer dwzcdq;

    @TableField("clsj")
    private String clsj;

    @TableField("djnf")
    private Integer djnf;

    @TableField("shzt")
    private Integer shzt;

    @TableField("dwyx")
    private String dwyx;

    @TableField("dwlx")
    private String dwlx;

    @TableField("nd")
    private String nd;
}
