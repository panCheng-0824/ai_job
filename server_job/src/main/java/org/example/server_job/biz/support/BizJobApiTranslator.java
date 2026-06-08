package org.example.server_job.biz.support;

import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.example.server_job.biz.entity.BizJobsRagSync;
import org.example.server_job.biz.vo.BizJobApiVO;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * 岗位实体 → 对外 API VO（兼容 web_job 旧字段名 + 0605 新字段）。
 */
public final class BizJobApiTranslator {

    private static final DateTimeFormatter DT_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private BizJobApiTranslator() {
    }

    public static BizJobApiVO toVo(
            BizJobsInfo job,
            BizJobsRagSync rag,
            BizCompanyInfo company,
            BizDictLabelSupport dict
    ) {
        BizJobApiVO vo = new BizJobApiVO();
        if (job == null) {
            return vo;
        }
        fillRawFields(vo, job);
        vo.setId(job.getJobid());
        vo.setJobName(job.getZwmc());
        vo.setCompanyId(job.getYrdw());
        vo.setAddress(job.getGzdd());
        vo.setVacancies(job.getXqrs() == null ? null : String.valueOf(job.getXqrs()));
        vo.setContent(job.getZwms());
        vo.setCreateTime(formatTime(job.getCjsj()));
        vo.setSxsj(formatTime(job.getSxsj()));

        if (company != null) {
            vo.setCompanyName(company.getGsmc());
            vo.setCompanyWid(company.getWid());
            if (dict != null) {
                vo.setIndustry(dict.industryLabel(company.getHylx()));
                vo.setCompanyType(dict.dwxzLabel(company.getDwxz()));
            } else {
                vo.setIndustry(company.getHylx());
                vo.setCompanyType(company.getDwxz() == null ? null : String.valueOf(company.getDwxz()));
            }
        } else {
            vo.setCompanyName(job.getYrdw());
        }

        if (dict != null) {
            vo.setArea(dict.regionLabel(job.getGzszsf(), job.getGzszcs(), job.getGzszdq()));
            vo.setSalaryRange(dict.yxjbLabel(job.getYxjb()));
            vo.setZwlbText(dict.label(BizDictBm.ZWLB, job.getZwlb()));
            vo.setXbyqText(dict.label(BizDictBm.XB, job.getXbyq()));
            vo.setEducation(dict.xlyqLabel(job.getXlyq()));
            vo.setXlyqText(dict.xlyqLabel(job.getXlyq()));
            vo.setXlyqLabels(dict.xlyqLabels(job.getXlyq()));
            vo.setNlqxText(dict.nlqxLabel(job.getNlqx()));
            vo.setNlqxLabels(dict.nlqxLabels(job.getNlqx()));
            vo.setNlqxItems(dict.nlqxItems(job.getNlqx()));
            vo.setSxqText(dict.sxqLabel(job.getSxq()));
            vo.setGjzText(dict.gjzText(job.getGjz()));
            vo.setGjzGroups(dict.gjzGroups(job.getGjz()));
        } else {
            vo.setArea("-");
            vo.setSalaryRange(job.getYxjb() == null ? null : String.valueOf(job.getYxjb()));
            vo.setEducation(job.getXlyq());
            vo.setXlyqText(job.getXlyq());
            vo.setNlqxText(job.getNlqx());
            vo.setSxqText(job.getSxq() == null ? null : String.valueOf(job.getSxq()));
            vo.setZwlbText(job.getZwlb() == null ? null : String.valueOf(job.getZwlb()));
            vo.setXbyqText(job.getXbyq() == null ? null : String.valueOf(job.getXbyq()));
        }

        if (rag != null && rag.getSynRag() != null && rag.getSynRag() == 1) {
            vo.setSynRag("1");
            vo.setRagMdPath(rag.getRagMdPath());
        } else {
            vo.setSynRag("0");
            vo.setRagMdPath(null);
        }
        return vo;
    }

    private static void fillRawFields(BizJobApiVO vo, BizJobsInfo job) {
        vo.setYrdw(job.getYrdw());
        vo.setZwmc(job.getZwmc());
        vo.setZwlb(job.getZwlb());
        vo.setYxjb(job.getYxjb());
        vo.setXbyq(job.getXbyq());
        vo.setSxq(job.getSxq());
        vo.setGzdd(job.getGzdd());
        vo.setGjz(job.getGjz());
        vo.setZwms(job.getZwms());
        vo.setJzrq(job.getJzrq());
        vo.setNlqx(job.getNlqx());
        vo.setXlyq(job.getXlyq());
        vo.setZt(job.getZt());
        vo.setSfzm(job.getSfzm());
        vo.setNd(job.getNd());
        vo.setLxr(job.getLxr());
        vo.setLxryx(job.getLxryx());
        vo.setLxrdh(job.getLxrdh());
        vo.setLxrsjh(job.getLxrsjh());
        vo.setLxrqq(job.getLxrqq());
        vo.setLxrwx(job.getLxrwx());
    }

    private static String formatTime(LocalDateTime t) {
        return t == null ? null : t.format(DT_FMT);
    }
}
