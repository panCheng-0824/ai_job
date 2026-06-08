package org.example.server_job.biz.support;

import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.springframework.stereotype.Component;

import java.time.format.DateTimeFormatter;

/**
 * 将岗位 + 企业 + 字典翻译拼装为 RAG 入库 Markdown 正文。
 * <p>策略：一岗一文档，企业完整画像嵌入岗位文档（非独立企业文档）。</p>
 */
@Component
public class JobRagTextBuilder {

    private static final DateTimeFormatter DT_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final BizDictLabelSupport dict;

    public JobRagTextBuilder(BizDictLabelSupport dict) {
        this.dict = dict;
    }

    /**
     * @param job     岗位主数据
     * @param company 关联企业，可为 null
     * @return Markdown 风格正文
     */
    public String build(BizJobsInfo job, BizCompanyInfo company) {
        StringBuilder sb = new StringBuilder();
        sb.append("# 岗位信息：").append(orDash(job.getZwmc())).append("\n\n");
        sb.append(buildRetrievalAnchor(job, company)).append("\n\n");

        sb.append("## 基本信息\n");
        sb.append("- 岗位ID：").append(orDash(job.getJobid())).append('\n');
        sb.append("- 职位名称：").append(orDash(job.getZwmc())).append('\n');
        sb.append("- 职位类别：").append(dict.label(BizDictBm.ZWLB, job.getZwlb())).append('\n');
        sb.append("- 月薪级别：").append(dict.yxjbLabel(job.getYxjb())).append('\n');
        sb.append("- 需求人数：").append(orDash(job.getXqrs())).append('\n');
        sb.append("- 学历要求：").append(dict.xlyqLabel(job.getXlyq())).append('\n');
        sb.append("- 能力需求：").append(dict.nlqxLabel(job.getNlqx())).append('\n');
        sb.append("- 性别要求：").append(dict.label(BizDictBm.XB, job.getXbyq())).append('\n');
        sb.append("- 实习期：").append(dict.sxqLabel(job.getSxq())).append('\n');
        sb.append("- 工作地点：").append(orDash(job.getGzdd())).append('\n');
        sb.append("- 工作地区：").append(dict.regionLabel(job.getGzszsf(), job.getGzszcs(), job.getGzszdq())).append('\n');
        sb.append("- 截止日期：").append(orDash(job.getJzrq())).append('\n');
        sb.append("- 生效时间：").append(formatTime(job.getSxsj())).append('\n');
        sb.append("- 创建时间：").append(formatTime(job.getCjsj())).append('\n');
        sb.append("- 关键字：").append(dict.gjzText(job.getGjz())).append("\n\n");

        appendEmployerSection(sb, job, company);

        sb.append("## 岗位联系信息\n");
        sb.append("- 联系人：").append(orDash(job.getLxr())).append('\n');
        sb.append("- 联系人邮箱：").append(orDash(job.getLxryx())).append('\n');
        sb.append("- 联系人电话：").append(orDash(job.getLxrdh())).append('\n');
        sb.append("- 联系人手机：").append(orDash(job.getLxrsjh())).append('\n');
        sb.append("- 联系人QQ：").append(orDash(job.getLxrqq())).append('\n');
        sb.append("- 联系人微信：").append(orDash(job.getLxrwx())).append("\n\n");

        sb.append("## 岗位描述\n");
        sb.append(orDash(RichTextSupport.toPlainText(job.getZwms()))).append('\n');
        return sb.toString();
    }

    /** 检索锚点：便于 LightRAG 向量命中企业/岗位关键维度 */
    String buildRetrievalAnchor(BizJobsInfo job, BizCompanyInfo company) {
        String companyName = company != null ? orDash(company.getGsmc()) : orDash(job.getYrdw());
        String companyType = company != null ? dict.dwxzLabel(company.getDwxz()) : "-";
        String companySize = company != null ? dict.gsgmLabel(company.getGsgm()) : "-";
        String industry = company != null ? dict.industryLabel(company.getHylx()) : "-";
        String companyRegion = company != null
                ? dict.companyRegionLabel(company.getDwszsf(), company.getDwszcs(), company.getDwszdq())
                : "-";
        return "【检索摘要】企业：" + companyName
                + " | 性质：" + companyType
                + " | 规模：" + companySize
                + " | 行业：" + industry
                + " | 企业地区：" + companyRegion
                + " | 岗位：" + orDash(job.getZwmc())
                + " | 学历：" + dict.xlyqLabel(job.getXlyq())
                + " | 月薪：" + dict.yxjbLabel(job.getYxjb())
                + " | 工作地区：" + dict.regionLabel(job.getGzszsf(), job.getGzszcs(), job.getGzszdq());
    }

    /** 用人单位完整区块（嵌入每条岗位文档） */
    void appendEmployerSection(StringBuilder sb, BizJobsInfo job, BizCompanyInfo company) {
        sb.append("## 用人单位\n");
        sb.append("- 组织机构代码：").append(orDash(job.getYrdw())).append('\n');
        if (company == null) {
            sb.append("- 说明：未在企业主数据表中匹配到记录\n\n");
            return;
        }
        sb.append("- 企业ID：").append(orDash(company.getWid())).append('\n');
        sb.append("- 公司名称：").append(orDash(company.getGsmc())).append('\n');
        sb.append("- 单位性质：").append(dict.dwxzLabel(company.getDwxz())).append('\n');
        sb.append("- 公司规模：").append(dict.gsgmLabel(company.getGsgm())).append('\n');
        sb.append("- 行业类型：").append(dict.industryLabel(company.getHylx())).append('\n');
        sb.append("- 机构类型：").append(orDash(company.getJglx())).append('\n');
        sb.append("- 单位类型：").append(orDash(company.getDwlx())).append('\n');
        sb.append("- 注册资金：").append(formatZczjWan(company.getZczj())).append('\n');
        sb.append("- 成立时间：").append(orDash(company.getClsj())).append('\n');
        sb.append("- 登记年份：").append(orDash(company.getDjnf())).append('\n');
        sb.append("- 公司主页：").append(orDash(company.getGszy())).append('\n');
        sb.append("- 办公地址：").append(orDash(company.getDwbgdz())).append('\n');
        sb.append("- 办公地区：").append(dict.companyRegionLabel(company.getDwszsf(), company.getDwszcs(), company.getDwszdq())).append('\n');
        sb.append("- 注册地址：").append(orDash(company.getDwzcdz())).append('\n');
        sb.append("- 注册地区：").append(dict.companyRegionLabel(company.getDwzcsf(), company.getDwzccs(), company.getDwzcdq())).append('\n');
        sb.append("- 单位邮箱：").append(orDash(company.getDwyx())).append('\n');
        sb.append("- 企业联系人：").append(orDash(company.getLxr())).append('\n');
        sb.append("- 企业联系人职位：").append(orDash(company.getLxrzw())).append('\n');
        sb.append("- 企业联系人电话：").append(orDash(company.getLxrdh())).append('\n');
        sb.append("- 企业联系人手机：").append(orDash(company.getLxrsjh())).append('\n');
        sb.append("- 企业联系人邮箱：").append(orDash(company.getLxrdzyj())).append('\n');
        sb.append("- 企业联系人传真：").append(orDash(company.getLxrcz())).append('\n');
        sb.append("- 企业联系人微信：").append(orDash(company.getLxrwx())).append('\n');
        sb.append("- 单位简介：").append(orDash(RichTextSupport.toPlainText(company.getDwjj()))).append("\n\n");
    }

    /** 生成 GrepRAG 落盘文件名 */
    public String buildMarkdownFilename(BizJobsInfo job, BizCompanyInfo company) {
        String companyName = company != null ? orDash(company.getGsmc()) : orDash(job.getYrdw());
        String jobName = orDash(job.getZwmc());
        String jobId = orDash(job.getJobid());
        return "job_"
                + sanitizeFilenamePart(companyName)
                + "_"
                + sanitizeFilenamePart(jobName)
                + "_"
                + sanitizeFilenamePart(jobId)
                + "_"
                + System.currentTimeMillis()
                + ".md";
    }

    private static String formatZczjWan(String zczj) {
        if (zczj == null || zczj.isBlank()) {
            return "-";
        }
        String s = zczj.trim();
        if (s.contains("万")) {
            return s;
        }
        return s + " 万元";
    }

    private static String sanitizeFilenamePart(String value) {
        String s = value.replaceAll("[\\\\/:*?\"<>|\\s]+", "_").replaceAll("_+", "_").replaceAll("^_+|_+$", "");
        return s.isEmpty() || "-".equals(s) ? "unknown" : s;
    }

    private static String formatTime(java.time.LocalDateTime t) {
        return t == null ? "-" : t.format(DT_FMT);
    }

    private static String orDash(Object value) {
        if (value == null) {
            return "-";
        }
        String s = String.valueOf(value).trim();
        return s.isEmpty() ? "-" : s;
    }
}
