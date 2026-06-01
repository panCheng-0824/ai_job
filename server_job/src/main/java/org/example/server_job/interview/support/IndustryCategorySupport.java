package org.example.server_job.interview.support;

import org.example.server_job.interview.entity.InterviewIndustryCategoryEntity;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 行业分类实体与 API 视图转换。
 */
@Component
public class IndustryCategorySupport {

    /**
     * 转为前端详情/列表项 Map。
     */
    public Map<String, Object> toItem(InterviewIndustryCategoryEntity row) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("category_id", row.getCategoryId());
        m.put("parent_id", row.getParentId());
        m.put("level", row.getLevel());
        m.put("category_code", row.getCategoryCode());
        m.put("category_name", row.getCategoryName());
        m.put("description", row.getDescription());
        m.put("intent_keywords", row.getIntentKeywords());
        m.put("enabled_for_intent", toBool(row.getEnabledForIntent()));
        m.put("enabled_for_classify", toBool(row.getEnabledForClassify()));
        m.put("sort_no", row.getSortNo());
        m.put("status", row.getStatus());
        m.put("created_at", row.getCreatedAt());
        m.put("updated_at", row.getUpdatedAt());
        return m;
    }

    /** 由编码生成默认 category_id */
    public String buildCategoryId(String categoryCode) {
        String code = categoryCode == null ? "" : categoryCode.trim().toLowerCase()
                .replaceAll("[^a-z0-9_\\u4e00-\\u9fa5]", "_")
                .replaceAll("_+", "_");
        if (code.isBlank()) {
            code = "cat";
        }
        return "ind_" + code;
    }

    private static boolean toBool(Integer v) {
        return v != null && v == 1;
    }
}
