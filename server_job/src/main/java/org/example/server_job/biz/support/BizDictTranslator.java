package org.example.server_job.biz.support;

import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * 业务主数据字典字段翻译：优先读 Redis（{@link SysCodeRedisCache}），未命中回退编码字符串。
 */
@Component
public class BizDictTranslator {

    private final SysCodeRedisCache sysCodeRedisCache;

    public BizDictTranslator(SysCodeRedisCache sysCodeRedisCache) {
        this.sysCodeRedisCache = sysCodeRedisCache;
    }

    public String text(String bm, Integer dm) {
        if (dm == null) {
            return null;
        }
        return sysCodeRedisCache.lookupName(bm, dm).orElse(String.valueOf(dm));
    }

    /** 拼接工作地省/市/区文本 */
    public String workRegion(BizJobsInfo job) {
        if (job == null) {
            return null;
        }
        return joinRegion(job.getGzszsf(), job.getGzszcs(), job.getGzszdq());
    }

    /** 拼接企业办公地省/市/区文本 */
    public String companyOfficeRegion(BizCompanyInfo company) {
        if (company == null) {
            return null;
        }
        return joinRegion(company.getDwszsf(), company.getDwszcs(), company.getDwszdq());
    }

    private String joinRegion(Integer sf, Integer cs, Integer dq) {
        List<String> parts = new ArrayList<>();
        addPart(parts, BizDictBm.XZQH, sf);
        addPart(parts, BizDictBm.XZQH, cs);
        addPart(parts, BizDictBm.XZQH, dq);
        if (parts.isEmpty()) {
            return null;
        }
        return String.join(" / ", parts);
    }

    private void addPart(List<String> parts, String bm, Integer dm) {
        if (dm == null) {
            return;
        }
        Optional<String> name = sysCodeRedisCache.lookupName(bm, dm);
        parts.add(name.orElse(String.valueOf(dm)));
    }
}
