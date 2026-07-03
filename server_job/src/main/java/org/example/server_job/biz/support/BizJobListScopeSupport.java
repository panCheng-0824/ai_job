package org.example.server_job.biz.support;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * 岗位列表 / RAG 同步共用的查询范围：关键词、公司类型、行业。
 */
@Component
public class BizJobListScopeSupport {

    private final SysCodeRedisCache sysCodeRedisCache;

    public BizJobListScopeSupport(SysCodeRedisCache sysCodeRedisCache) {
        this.sysCodeRedisCache = sysCodeRedisCache;
    }

    public static String normalizeKeyword(String keyword) {
        return keyword == null ? "" : keyword.trim();
    }

    public void applyListScope(
            LambdaQueryWrapper<BizJobsInfo> wrapper,
            String keyword,
            String companyType,
            String industry
    ) {
        applyKeywordScope(wrapper, normalizeKeyword(keyword));
        applyCompanyTypeFilter(wrapper, companyType);
        applyIndustryFilter(wrapper, industry);
    }

    public static void applyKeywordScope(LambdaQueryWrapper<BizJobsInfo> w, String normalizedKeyword) {
        if (normalizedKeyword == null || normalizedKeyword.isEmpty()) {
            return;
        }
        w.and(x -> x.like(BizJobsInfo::getJobid, normalizedKeyword)
                .or().like(BizJobsInfo::getZwmc, normalizedKeyword)
                .or().like(BizJobsInfo::getYrdw, normalizedKeyword)
                .or().like(BizJobsInfo::getGzdd, normalizedKeyword)
                .or().like(BizJobsInfo::getGjz, normalizedKeyword)
                .or().like(BizJobsInfo::getZwms, normalizedKeyword));
    }

    public void applyCompanyTypeFilter(LambdaQueryWrapper<BizJobsInfo> w, String companyTypeCode) {
        if (companyTypeCode == null || companyTypeCode.isEmpty()) {
            return;
        }
        Optional<Map<String, Object>> dictItem = findDictItemByCode(BizDictBm.DWXZ, companyTypeCode);
        if (dictItem.isEmpty()) {
            return;
        }
        Set<String> matchValues = collectDwxzMatchValues(dictItem.get());
        if (matchValues.isEmpty()) {
            return;
        }
        w.inSql(BizJobsInfo::getYrdw, buildCompanyFieldSubquery("dwxz", matchValues));
    }

    public void applyIndustryFilter(LambdaQueryWrapper<BizJobsInfo> w, String industryCode) {
        if (industryCode == null || industryCode.isEmpty()) {
            return;
        }
        Optional<Map<String, Object>> dictItem = findDictItemByCode(BizDictBm.HYLB, industryCode);
        if (dictItem.isEmpty()) {
            return;
        }
        Set<String> matchValues = collectIndustryMatchValues(dictItem.get());
        if (matchValues.isEmpty()) {
            return;
        }
        w.inSql(BizJobsInfo::getYrdw, buildCompanyFieldSubquery("hylx", matchValues));
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> loadDictItems(String bm) {
        Optional<Map<String, Object>> bucket = sysCodeRedisCache.readBucket(bm);
        if (bucket.isEmpty()) {
            return List.of();
        }
        Object raw = bucket.get().get("items");
        if (!(raw instanceof List<?> list)) {
            return List.of();
        }
        List<Map<String, Object>> items = new ArrayList<>();
        for (Object o : list) {
            if (o instanceof Map<?, ?> map) {
                items.add((Map<String, Object>) map);
            }
        }
        return items;
    }

    private Optional<Map<String, Object>> findDictItemByCode(String bm, String code) {
        if (code == null || code.isBlank()) {
            return Optional.empty();
        }
        String normalized = code.trim();
        for (Map<String, Object> item : loadDictItems(bm)) {
            if (normalized.equals(facetCodeOf(item))) {
                return Optional.of(item);
            }
        }
        return Optional.empty();
    }

    private Set<String> collectDwxzMatchValues(Map<String, Object> item) {
        LinkedHashMap<String, Boolean> values = new LinkedHashMap<>();
        putIfNotBlank(values, textOf(item.get("dm")));
        putIfNotBlank(values, textOf(item.get("id")));
        String dm = textOf(item.get("dm"));
        if (!dm.isEmpty()) {
            try {
                putIfNotBlank(values, String.valueOf(Integer.parseInt(dm)));
            } catch (NumberFormatException ignored) {
                // ignore
            }
        }
        return values.keySet();
    }

    private Set<String> collectIndustryMatchValues(Map<String, Object> item) {
        LinkedHashMap<String, Boolean> values = new LinkedHashMap<>();
        putIfNotBlank(values, textOf(item.get("dm")));
        putIfNotBlank(values, textOf(item.get("id")));
        putIfNotBlank(values, textOf(item.get("name")));
        String dm = textOf(item.get("dm"));
        if (dm.length() == 1) {
            putIfNotBlank(values, String.valueOf(Character.toUpperCase(dm.charAt(0))));
            putIfNotBlank(values, String.valueOf(Character.toLowerCase(dm.charAt(0))));
        }
        return values.keySet();
    }

    private static void putIfNotBlank(Map<String, Boolean> values, String value) {
        if (value != null && !value.isBlank()) {
            values.put(value.trim(), Boolean.TRUE);
        }
    }

    private String buildCompanyFieldSubquery(String field, Set<String> matchValues) {
        if ("dwxz".equals(field)) {
            List<String> numericParts = new ArrayList<>();
            List<String> textParts = new ArrayList<>();
            for (String value : matchValues) {
                try {
                    numericParts.add(String.valueOf(Integer.parseInt(value)));
                } catch (NumberFormatException ex) {
                    textParts.add(sqlStringLiteral(value));
                }
            }
            List<String> clauses = new ArrayList<>();
            if (!numericParts.isEmpty()) {
                clauses.add("c.dwxz IN (" + String.join(", ", numericParts) + ")");
            }
            if (!textParts.isEmpty()) {
                clauses.add("CAST(c.dwxz AS CHAR) IN (" + String.join(", ", textParts) + ")");
            }
            return "SELECT c.zzjgdm FROM t_biz_compary_info c WHERE " + String.join(" OR ", clauses);
        }
        List<String> literals = matchValues.stream().map(BizJobListScopeSupport::sqlStringLiteral).toList();
        return "SELECT c.zzjgdm FROM t_biz_compary_info c WHERE TRIM(c.hylx) IN (" + String.join(", ", literals) + ")";
    }

    private static String sqlStringLiteral(String value) {
        String escaped = value.replace("'", "''");
        return "'" + escaped + "'";
    }

    private static String facetCodeOf(Map<String, Object> item) {
        String dm = textOf(item.get("dm"));
        if (!dm.isEmpty()) {
            return dm;
        }
        return textOf(item.get("id"));
    }

    private static String textOf(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }
}
