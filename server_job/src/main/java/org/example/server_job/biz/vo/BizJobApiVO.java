package org.example.server_job.biz.vo;

import lombok.Data;

import java.util.List;

/**
 * 岗位 API 视图：兼容 web_job 旧 camelCase 字段，并暴露 0605 新 schema 及字典翻译文本。
 */
@Data
public class BizJobApiVO {

    /** 兼容字段 */
    private String id;
    private String jobName;
    private String companyName;
    private String companyId;
    /** 企业详情页路由 ID（{@code t_biz_compary_info.WID}） */
    private String companyWid;
    private String address;
    private String area;
    private String salaryRange;
    private String education;
    private String vacancies;
    private String content;
    private String createTime;
    private String synRag;
    private String ragMdPath;
    private String companyType;
    private String industry;

    /** 0605 原始字段 */
    private String yrdw;
    private String zwmc;
    private Integer zwlb;
    private Integer yxjb;
    private Integer xbyq;
    private Integer sxq;
    private String gzdd;
    private String gjz;
    private String zwms;
    private String jzrq;
    private String nlqx;
    private String xlyq;
    private String sxsj;
    private Integer zt;
    private Integer sfzm;
    private Integer nd;
    private String lxr;
    private String lxryx;
    private String lxrdh;
    private String lxrsjh;
    private String lxrqq;
    private String lxrwx;

    /** 字典翻译文本 */
    private String zwlbText;
    private String xbyqText;
    /** 任职要求翻译 */
    private String xlyqText;
    private String nlqxText;
    private String sxqText;
    private List<String> xlyqLabels;
    private List<String> nlqxLabels;
    private List<BizJobNlqxItemVO> nlqxItems;
    /** 关键字翻译（{@code gjz} 为 job_gjz 的 DM 逗号串） */
    private String gjzText;
    private List<BizJobGjzGroupVO> gjzGroups;
}
