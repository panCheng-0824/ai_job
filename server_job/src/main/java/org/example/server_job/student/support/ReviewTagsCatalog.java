package org.example.server_job.student.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 与 ai_job config/review_tags.json 对齐：校验评价标签 id，限制每评最多条数。
 */
@Component
public class ReviewTagsCatalog {

    public static final int MAX_SELECTED_PER_REVIEW = 5;

    private final ObjectMapper objectMapper;
    private volatile JsonNode root;

    public ReviewTagsCatalog(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.root = objectMapper.createObjectNode();
    }

    @PostConstruct
    public void load() {
        try (InputStream in = new ClassPathResource("config/review_tags.json").getInputStream()) {
            root = objectMapper.readTree(in);
        } catch (Exception ignored) {
            root = objectMapper.createObjectNode();
        }
    }

    public Map<String, Object> getCatalogForApi() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("job_review_tags", readTagList("job_review_tags"));
        out.put("company_review_tags", readTagList("company_review_tags"));
        out.put("max_selected_per_review", MAX_SELECTED_PER_REVIEW);
        return out;
    }

    private List<Map<String, String>> readTagList(String key) {
        List<Map<String, String>> list = new ArrayList<>();
        JsonNode arr = root.path(key);
        if (!arr.isArray()) {
            return list;
        }
        for (JsonNode n : arr) {
            String id = n.path("id").asText("").trim();
            String label = n.path("label").asText("").trim();
            if (!id.isEmpty() && !label.isEmpty()) {
                list.add(Map.of("id", id, "label", label));
            }
        }
        return list;
    }

    public Set<String> allowedJobTagIds() {
        return toIdSet(readTagList("job_review_tags"));
    }

    public Set<String> allowedCompanyTagIds() {
        return toIdSet(readTagList("company_review_tags"));
    }

    private static Set<String> toIdSet(List<Map<String, String>> tags) {
        Set<String> s = new LinkedHashSet<>();
        for (Map<String, String> t : tags) {
            String id = t.get("id");
            if (id != null && !id.isEmpty()) {
                s.add(id);
            }
        }
        return s;
    }

    /** 只保留配置内 id，去重，最多 {@link #MAX_SELECTED_PER_REVIEW} 个。 */
    public List<String> normalizeJobTags(Iterable<?> raw) {
        return normalize(raw, allowedJobTagIds());
    }

    public List<String> normalizeCompanyTags(Iterable<?> raw) {
        return normalize(raw, allowedCompanyTagIds());
    }

    private static List<String> normalize(Iterable<?> raw, Set<String> allowed) {
        List<String> out = new ArrayList<>();
        if (raw == null) {
            return out;
        }
        for (Object x : raw) {
            if (x == null) {
                continue;
            }
            String tid = String.valueOf(x).trim();
            if (allowed.contains(tid) && !out.contains(tid)) {
                out.add(tid);
            }
            if (out.size() >= MAX_SELECTED_PER_REVIEW) {
                break;
            }
        }
        return out;
    }
}
