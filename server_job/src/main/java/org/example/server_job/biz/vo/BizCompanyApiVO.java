package org.example.server_job.biz.vo;

import lombok.Data;

/**
 * 企业 API 视图：兼容 web_job 旧 camelCase 字段，并暴露 0605 新 schema 及字典翻译文本。
 */
@Data
public class BizCompanyApiVO {

    /** 兼容字段 */
    private String id;
    private String companyName;
    private String companySize;
    private String companyType;
    private String area;
    private String address;
    private String website;

    /** 0605 原始字段 */
    private String wid;
    private String gsmc;
    private String hylx;
    private String dwjj;
    private String gszy;
    private String zczj;
    private String dwzcdz;
    private String jglx;
    private String zzjgdm;
    private String clsj;
    private String dwlx;
    private String lxr;
    private String lxrzw;
    private String lxrdh;
    private String lxrsjh;
    private String lxrdzyj;

    /** 办公地省市区（字典翻译拼接） */
    private String region;
}
