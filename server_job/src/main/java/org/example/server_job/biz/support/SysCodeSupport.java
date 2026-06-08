package org.example.server_job.biz.support;

import org.example.server_job.biz.entity.SysCode;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 字典实体与 API/Redis 载荷之间的转换辅助。
 */
public final class SysCodeSupport {

    private SysCodeSupport() {
    }

    /** 将单行字典转为前端/缓存通用 Map */
    public static Map<String, Object> toItem(SysCode row) {
        Map<String, Object> item = new LinkedHashMap<>();
        if (row == null) {
            return item;
        }
        item.put("id", row.getId());
        item.put("fid", row.getFid());
        item.put("name", row.getName());
        item.put("dm", row.getDm());
        item.put("mc", row.getMc());
        item.put("bm", row.getBm());
        item.put("lbmc", row.getLbmc());
        return item;
    }

    /**
     * 将扁平字典列表按 FID 组装为树（用于省市区等级联）。
     *
     * @param items 同一 BM 下的全部项
     * @return 根节点列表（FID 为空或不在本列表 id 集合中）
     */
    public static List<Map<String, Object>> buildTree(List<Map<String, Object>> items) {
        if (items == null || items.isEmpty()) {
            return List.of();
        }
        Map<String, List<Map<String, Object>>> childrenByFid = new LinkedHashMap<>();
        for (Map<String, Object> item : items) {
            String fid = item.get("fid") == null ? "" : String.valueOf(item.get("fid")).trim();
            childrenByFid.computeIfAbsent(fid, k -> new ArrayList<>()).add(item);
        }
        for (Map<String, Object> item : items) {
            String id = item.get("id") == null ? "" : String.valueOf(item.get("id")).trim();
            List<Map<String, Object>> children = childrenByFid.getOrDefault(id, List.of());
            if (!children.isEmpty()) {
                item.put("children", children);
            }
        }
        List<Map<String, Object>> roots = new ArrayList<>();
        for (Map<String, Object> item : items) {
            String fid = item.get("fid") == null ? "" : String.valueOf(item.get("fid")).trim();
            if (fid.isEmpty()) {
                roots.add(item);
            }
        }
        return roots.isEmpty() ? items : roots;
    }
}
