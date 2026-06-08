package org.example.server_job.biz.support;

import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.vo.BizCompanyApiVO;

/**
 * 企业实体 → 对外 API VO（兼容 web_job 旧字段名 + 0605 新字段）。
 */
public final class BizCompanyApiTranslator {

    private BizCompanyApiTranslator() {
    }

    public static BizCompanyApiVO toVo(BizCompanyInfo company, BizDictLabelSupport dict) {
        BizCompanyApiVO vo = new BizCompanyApiVO();
        if (company == null) {
            return vo;
        }
        vo.setId(company.getWid());
        vo.setWid(company.getWid());
        vo.setCompanyName(company.getGsmc());
        vo.setGsmc(company.getGsmc());
        vo.setDwjj(company.getDwjj());
        vo.setAddress(company.getDwbgdz());
        vo.setWebsite(company.getDwyx());
        vo.setGszy(company.getGszy());
        vo.setZczj(company.getZczj());
        vo.setDwzcdz(company.getDwzcdz());
        vo.setJglx(company.getJglx());
        vo.setZzjgdm(company.getZzjgdm());
        vo.setClsj(company.getClsj());
        vo.setDwlx(company.getDwlx());
        vo.setLxr(company.getLxr());
        vo.setLxrzw(company.getLxrzw());
        vo.setLxrdh(company.getLxrdh());
        vo.setLxrsjh(company.getLxrsjh());
        vo.setLxrdzyj(company.getLxrdzyj());

        if (dict != null) {
            String industryLabel = dict.industryLabel(company.getHylx());
            vo.setHylx(industryLabel);
            vo.setArea(industryLabel);
            vo.setCompanySize(dict.gsgmLabel(company.getGsgm()));
            vo.setCompanyType(dict.dwxzLabel(company.getDwxz()));
            vo.setRegion(dict.companyRegionLabel(company.getDwszsf(), company.getDwszcs(), company.getDwszdq()));
        } else {
            String rawHylx = company.getHylx();
            vo.setHylx(rawHylx);
            vo.setArea(rawHylx);
            vo.setCompanySize(company.getGsgm() == null ? null : String.valueOf(company.getGsgm()));
            vo.setCompanyType(company.getDwxz() == null ? null : String.valueOf(company.getDwxz()));
            vo.setRegion("-");
        }
        return vo;
    }
}
