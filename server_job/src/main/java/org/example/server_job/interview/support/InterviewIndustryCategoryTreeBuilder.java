package org.example.server_job.interview.support;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 将平铺行业分类转为一级节点 + children 二级列表。
 */
@Component
public class InterviewIndustryCategoryTreeBuilder {

    /**
     * @param flat {@code listCategories} 产出的平铺 item
     * @return 仅含 level=1 的根节点，每节点带 children
     */
    public List<Map<String, Object>> buildTree(List<Map<String, Object>> flat) {
        Map<String, Map<String, Object>> roots = new LinkedHashMap<>();
        List<Map<String, Object>> level2 = flat.stream()
                .filter(m -> Integer.valueOf(2).equals(m.get("level")))
                .collect(Collectors.toList());

        for (Map<String, Object> item : flat) {
            if (!Integer.valueOf(1).equals(item.get("level"))) {
                continue;
            }
            Map<String, Object> copy = new LinkedHashMap<>(item);
            copy.put("children", new ArrayList<Map<String, Object>>());
            roots.put(String.valueOf(item.get("category_id")), copy);
        }

        for (Map<String, Object> child : level2) {
            String parentId = String.valueOf(child.get("parent_id"));
            Map<String, Object> root = roots.get(parentId);
            if (root != null) {
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> children = (List<Map<String, Object>>) root.get("children");
                children.add(child);
            }
        }
        return new ArrayList<>(roots.values());
    }
}
