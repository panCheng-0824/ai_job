package org.example.server_job.biz.support;

import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.example.server_job.biz.entity.BizJobsRagSync;
import org.example.server_job.biz.vo.BizJobGjzGroupVO;
import org.example.server_job.biz.vo.BizJobNlqxItemVO;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * 岗位/企业详情页底部 JSON 预览：按业务分区输出字典翻译后的展示文本（不输出原始字典编码）。
 */
@Component
public class BizDetailPreviewBuilder {

    private static final DateTimeFormatter DT_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int COMPANY_JOB_PACK_PREVIEW_LIMIT = 15;

    private final BizDictLabelSupport dict;
    private final JobRagTextBuilder jobRagTextBuilder;

    public BizDetailPreviewBuilder(BizDictLabelSupport dict, JobRagTextBuilder jobRagTextBuilder) {
        this.dict = dict;
        this.jobRagTextBuilder = jobRagTextBuilder;
    }

    /** 岗位详情 + 关联企业 + RAG 元数据 */
    public Map<String, Object> buildJobPreview(
            BizJobsInfo job,
            BizCompanyInfo company,
            BizJobsRagSync rag,
            String ragMarkdown,
            String ragFilename,
            String ragSource
    ) {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("概要", buildJobMeta(job, company, rag, ragMarkdown, ragFilename, ragSource));
        root.put("岗位基础信息", buildJobBasic(job));
        root.put("任职要求与薪资", buildJobRequirements(job));
        root.put("工作地点", buildJobLocation(job));
        root.put("岗位联系信息", buildJobContact(job));
        root.put("关键字", buildJobGjz(job));
        root.put("职位描述", orDash(RichTextSupport.toPlainText(job.getZwms())));
        root.put("用人单位", company == null ? buildMissingCompany(job) : buildCompanyPreview(company));
        root.put("知识库同步正文_markdown", orDash(ragMarkdown));
        return root;
    }

    /** 企业详情 */
    public Map<String, Object> buildCompanyPreview(BizCompanyInfo company) {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("企业概要", buildCompanySummary(company));
        root.put("工商与规模", buildCompanyBusiness(company));
        root.put("地址信息", buildCompanyAddress(company));
        root.put("联系信息", buildCompanyContact(company));
        root.put("单位简介", orDash(RichTextSupport.toPlainText(company.getDwjj())));
        return root;
    }

    /**
     * 企业详情页：LightRAG 打包预览（企业区块 + 各关联岗位的完整打包 JSON）。
     */
    public Map<String, Object> buildCompanyRagPackPreview(
            BizCompanyInfo company,
            List<BizJobsInfo> jobs,
            Map<String, BizJobsRagSync> ragMap,
            String ragSource
    ) {
        List<BizJobsInfo> safeJobs = jobs == null ? List.of() : jobs;
        Map<String, BizJobsRagSync> safeRagMap = ragMap == null ? Map.of() : ragMap;

        Map<String, Object> root = new LinkedHashMap<>();
        root.put("打包策略", "一岗一文档（LightRAG 文档 ID：job-{岗位ID}）；企业完整信息嵌入每条岗位文档");
        put(root, "企业WID", company.getWid());
        put(root, "组织机构代码", company.getZzjgdm());
        put(root, "关联岗位总数", safeJobs.size());
        root.put("检索锚点摘要_示例", jobRagTextBuilder.buildRetrievalAnchor(
                safeJobs.isEmpty() ? placeholderJob(company) : safeJobs.get(0),
                company
        ));
        root.put("嵌入岗位文档的企业区块", buildCompanyEmbeddedInJobPack(company));

        List<Map<String, Object>> jobPacks = new ArrayList<>();
        int limit = Math.min(safeJobs.size(), COMPANY_JOB_PACK_PREVIEW_LIMIT);
        for (int i = 0; i < limit; i++) {
            BizJobsInfo job = safeJobs.get(i);
            BizJobsRagSync rag = job.getJobid() == null ? null : safeRagMap.get(job.getJobid());
            String markdown = jobRagTextBuilder.build(job, company);
            String filename = jobRagTextBuilder.buildMarkdownFilename(job, company);
            Map<String, Object> pack = new LinkedHashMap<>();
            put(pack, "LightRAG文档ID", job.getJobid() == null ? "-" : "job-" + job.getJobid());
            put(pack, "职位名称", job.getZwmc());
            put(pack, "知识库已同步", rag != null && rag.getSynRag() != null && rag.getSynRag() == 1 ? "是" : "否");
            put(pack, "知识库文档路径", rag != null ? rag.getRagMdPath() : null);
            pack.put("展示数据", buildJobPreview(job, company, rag, markdown, filename, ragSource));
            jobPacks.add(pack);
        }
        root.put("关联岗位打包预览", jobPacks);
        if (safeJobs.size() > limit) {
            put(root, "预览说明", "仅展示前 " + limit + " 条岗位打包详情，共 " + safeJobs.size() + " 条");
            List<String> restIds = safeJobs.stream()
                    .skip(limit)
                    .map(BizJobsInfo::getJobid)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            root.put("未展开岗位ID", restIds);
        }
        return root;
    }

    /** 同步岗位文档时重复嵌入的企业 JSON 区块 */
    public Map<String, Object> buildCompanyEmbeddedInJobPack(BizCompanyInfo company) {
        Map<String, Object> root = new LinkedHashMap<>();
        put(root, "说明", "以下字段写入每条岗位 LightRAG 文档的「用人单位」章节");
        root.put("企业概要", buildCompanySummary(company));
        root.put("工商与规模", buildCompanyBusiness(company));
        root.put("地址信息", buildCompanyAddress(company));
        root.put("企业联系信息", buildCompanyContact(company));
        root.put("单位简介", orDash(RichTextSupport.toPlainText(company.getDwjj())));
        return root;
    }

    private static BizJobsInfo placeholderJob(BizCompanyInfo company) {
        BizJobsInfo job = new BizJobsInfo();
        job.setJobid("-");
        job.setZwmc("（示例岗位）");
        job.setYrdw(company.getZzjgdm());
        return job;
    }

    private Map<String, Object> buildJobMeta(
            BizJobsInfo job,
            BizCompanyInfo company,
            BizJobsRagSync rag,
            String ragMarkdown,
            String ragFilename,
            String ragSource
    ) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "岗位ID", job.getJobid());
        put(m, "职位名称", job.getZwmc());
        put(m, "用人单位名称", company != null ? company.getGsmc() : job.getYrdw());
        put(m, "组织机构代码", job.getYrdw());
        put(m, "企业详情页ID", company != null ? company.getWid() : null);
        put(m, "知识库已同步", rag != null && rag.getSynRag() != null && rag.getSynRag() == 1 ? "是" : "否");
        put(m, "知识库文档路径", rag != null ? rag.getRagMdPath() : null);
        put(m, "RAG来源", ragSource);
        put(m, "RAG文件名", ragFilename);
        int len = ragMarkdown == null ? 0 : ragMarkdown.length();
        put(m, "RAG正文字数", len);
        return m;
    }

    private Map<String, Object> buildJobBasic(BizJobsInfo job) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "职位名称", job.getZwmc());
        put(m, "职位类别", dict.label(BizDictBm.ZWLB, job.getZwlb()));
        put(m, "需求人数", job.getXqrs());
        put(m, "截止日期", job.getJzrq());
        put(m, "年度", job.getNd());
        put(m, "生效时间", formatTime(job.getSxsj()));
        put(m, "创建时间", formatTime(job.getCjsj()));
        put(m, "是否招满", job.getSfzm());
        return m;
    }

    private Map<String, Object> buildJobRequirements(BizJobsInfo job) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "学历要求", dict.xlyqLabel(job.getXlyq()));
        put(m, "学历要求_分项", dict.xlyqLabels(job.getXlyq()));
        put(m, "月薪级别", dict.yxjbLabel(job.getYxjb()));
        put(m, "能力需求", dict.nlqxLabel(job.getNlqx()));
        put(m, "能力需求_分项", nlqxItemsToMaps(dict.nlqxItems(job.getNlqx())));
        put(m, "性别要求", dict.label(BizDictBm.XB, job.getXbyq()));
        put(m, "实习期", dict.sxqLabel(job.getSxq()));
        return m;
    }

    private Map<String, Object> buildJobLocation(BizJobsInfo job) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "工作地点", job.getGzdd());
        put(m, "工作地区", dict.regionLabel(job.getGzszsf(), job.getGzszcs(), job.getGzszdq()));
        return m;
    }

    private Map<String, Object> buildJobContact(BizJobsInfo job) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "联系人", job.getLxr());
        put(m, "联系人邮箱", job.getLxryx());
        put(m, "联系人电话", job.getLxrdh());
        put(m, "联系人手机", job.getLxrsjh());
        put(m, "联系人QQ", job.getLxrqq());
        put(m, "联系人微信", job.getLxrwx());
        return m;
    }

    private Map<String, Object> buildJobGjz(BizJobsInfo job) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "关键字汇总", dict.gjzText(job.getGjz()));
        List<BizJobGjzGroupVO> groups = dict.gjzGroups(job.getGjz());
        if (!groups.isEmpty()) {
            List<Map<String, Object>> groupMaps = new ArrayList<>();
            for (BizJobGjzGroupVO g : groups) {
                Map<String, Object> gm = new LinkedHashMap<>();
                gm.put("分组", g.getGroupName());
                gm.put("关键词", g.getKeywords());
                groupMaps.add(gm);
            }
            put(m, "关键字分组", groupMaps);
        }
        return m;
    }

    private Map<String, Object> buildMissingCompany(BizJobsInfo job) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "组织机构代码", job.getYrdw());
        put(m, "说明", "未在企业主数据表中匹配到记录");
        return m;
    }

    private Map<String, Object> buildCompanySummary(BizCompanyInfo company) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "企业ID", company.getWid());
        put(m, "公司名称", company.getGsmc());
        put(m, "组织机构代码", company.getZzjgdm());
        put(m, "单位性质", dict.dwxzLabel(company.getDwxz()));
        put(m, "公司规模", dict.gsgmLabel(company.getGsgm()));
        put(m, "行业类型", dict.industryLabel(company.getHylx()));
        put(m, "办公地址", company.getDwbgdz());
        put(m, "办公地区", dict.companyRegionLabel(company.getDwszsf(), company.getDwszcs(), company.getDwszdq()));
        return m;
    }

    private Map<String, Object> buildCompanyBusiness(BizCompanyInfo company) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "机构类型", company.getJglx());
        put(m, "单位类型", company.getDwlx());
        put(m, "注册资金", formatZczjWan(company.getZczj()));
        put(m, "成立时间", company.getClsj());
        put(m, "登记年份", company.getDjnf());
        put(m, "公司主页", company.getGszy());
        put(m, "年度", company.getNd());
        return m;
    }

    private Map<String, Object> buildCompanyAddress(BizCompanyInfo company) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "办公地址", company.getDwbgdz());
        put(m, "办公地区", dict.companyRegionLabel(company.getDwszsf(), company.getDwszcs(), company.getDwszdq()));
        put(m, "注册地址", company.getDwzcdz());
        put(m, "注册地区", dict.companyRegionLabel(company.getDwzcsf(), company.getDwzccs(), company.getDwzcdq()));
        return m;
    }

    private Map<String, Object> buildCompanyContact(BizCompanyInfo company) {
        Map<String, Object> m = new LinkedHashMap<>();
        put(m, "单位邮箱", company.getDwyx());
        put(m, "联系人", company.getLxr());
        put(m, "联系人职位", company.getLxrzw());
        put(m, "联系人电话", company.getLxrdh());
        put(m, "联系人手机", company.getLxrsjh());
        put(m, "联系人邮箱", company.getLxrdzyj());
        put(m, "联系人传真", company.getLxrcz());
        put(m, "联系人微信", company.getLxrwx());
        put(m, "邮政编码", company.getYzbm());
        return m;
    }

    private static List<Map<String, Object>> nlqxItemsToMaps(List<BizJobNlqxItemVO> items) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (BizJobNlqxItemVO item : items) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("类型", item.getLabel());
            m.put("详情", item.getDetail());
            out.add(m);
        }
        return out;
    }

    private static void put(Map<String, Object> target, String key, Object value) {
        target.put(key, orDash(value));
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

    private static String formatTime(LocalDateTime t) {
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
