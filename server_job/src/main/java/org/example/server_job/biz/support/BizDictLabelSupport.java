package org.example.server_job.biz.support;

import org.springframework.stereotype.Component;

import org.example.server_job.biz.vo.BizJobGjzGroupVO;
import org.example.server_job.biz.vo.BizJobNlqxItemVO;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * 基于 Redis 字典缓存的编码翻译辅助。
 */
@Component
public class BizDictLabelSupport {

    /** GB/T 4754 门类字母 A 对应 sys_code.job_hylb 顶级项 ID=800 */
    private static final int HYLB_GBT_LETTER_ID_BASE = 800;

    private final SysCodeRedisCache sysCodeRedisCache;

    public BizDictLabelSupport(SysCodeRedisCache sysCodeRedisCache) {
        this.sysCodeRedisCache = sysCodeRedisCache;
    }

    /**
     * 单值翻译（{@code sys_code.DM} → {@code NAME}）。
     * 先按 DM 查，未命中再按字典项 ID 查（部分历史数据 {@code dwxz} 存的是 ID 而非 DM）。
     */
    public String label(String bm, Integer dm) {
        if (dm == null) {
            return "-";
        }
        Optional<String> byDm = sysCodeRedisCache.lookupName(bm, dm);
        if (byDm.isPresent()) {
            return byDm.get();
        }
        Optional<String> byId = sysCodeRedisCache.lookupNameById(bm, String.valueOf(dm));
        return byId.orElse(String.valueOf(dm));
    }

    /** {@code t_biz_compary_info.dwxz} → 单位性质中文名 */
    public String dwxzLabel(Integer dwxz) {
        return label(BizDictBm.DWXZ, dwxz);
    }

    /** {@code t_biz_compary_info.gsgm} → 公司规模中文名 */
    public String gsgmLabel(Integer gsgm) {
        return label(BizDictBm.GSGM, gsgm);
    }

    /**
     * {@code t_biz_jobs_info.gjz}：逗号分隔的 {@code job_gjz.DM} → 按 {@code job_gjz_fz} 分组的中文关键字。
     */
    public List<BizJobGjzGroupVO> gjzGroups(String gjzRaw) {
        if (gjzRaw == null || gjzRaw.isBlank()) {
            return List.of();
        }
        ensureGjzCache();
        Map<String, List<String>> grouped = new LinkedHashMap<>();
        List<String> unknown = new ArrayList<>();
        for (String part : gjzRaw.split(",")) {
            String dm = part.trim();
            if (dm.isEmpty()) {
                continue;
            }
            GjzDictEntry entry = gjzByDm.get(dm);
            if (entry == null) {
                unknown.add(resolveGjzKeywordFallback(dm));
                continue;
            }
            String groupId = entry.groupId == null || entry.groupId.isBlank() ? "_ungrouped" : entry.groupId;
            grouped.computeIfAbsent(groupId, k -> new ArrayList<>()).add(entry.keywordName);
        }
        if (!unknown.isEmpty()) {
            grouped.computeIfAbsent("_unknown", k -> new ArrayList<>()).addAll(unknown);
        }
        if (grouped.isEmpty()) {
            return List.of();
        }

        List<BizJobGjzGroupVO> result = new ArrayList<>();
        for (String groupId : gjzGroupOrder) {
            appendGjzGroup(result, groupId, grouped.remove(groupId));
        }
        for (Map.Entry<String, List<String>> entry : grouped.entrySet()) {
            String groupName = "_unknown".equals(entry.getKey())
                    ? "未匹配"
                    : gjzGroupNameById.getOrDefault(entry.getKey(), "其他");
            appendGjzGroupNamed(result, groupName, entry.getValue());
        }
        return result;
    }

    /** 分组关键字拼成单行摘要，供列表/RAG/对话上下文使用 */
    public String gjzText(String gjzRaw) {
        List<BizJobGjzGroupVO> groups = gjzGroups(gjzRaw);
        if (groups.isEmpty()) {
            return "-";
        }
        return groups.stream()
                .map(g -> g.getGroupName() + "：" + String.join("、", g.getKeywords()))
                .collect(Collectors.joining("；"));
    }

    /** {@code t_biz_jobs_info.yxjb} → 职业月薪（单位：元） */
    public String yxjbLabel(Integer yxjb) {
        if (yxjb == null) {
            return "-";
        }
        String text = label(BizDictBm.YXJB, yxjb);
        if ("-".equals(text) || text.contains("面议") || text.contains("元")) {
            return text;
        }
        return text + " 元";
    }

    /** {@code t_biz_jobs_info.sxq} → 实习期（单位：月，字典项已含「月/年/面议」时不重复追加） */
    public String sxqLabel(Integer sxq) {
        if (sxq == null) {
            return "-";
        }
        String text = label(BizDictBm.SXQ, sxq);
        if ("-".equals(text) || text.contains("月") || text.contains("年") || text.contains("面议")) {
            return text;
        }
        return text + " 月";
    }

    /** {@code t_biz_jobs_info.xlyq}：逗号分隔 {@code job_xl.DM} */
    public String xlyqLabel(String xlyqRaw) {
        return commaSeparatedText(BizDictBm.XL, xlyqRaw);
    }

    public List<String> xlyqLabels(String xlyqRaw) {
        return commaSeparatedLabels(BizDictBm.XL, xlyqRaw);
    }

    /** {@code t_biz_jobs_info.nlqx}：逗号分隔 {@code job_nl.DM}（展示类型简称） */
    public String nlqxLabel(String nlqxRaw) {
        List<String> labels = nlqxLabels(nlqxRaw);
        return labels.isEmpty() ? "-" : String.join("、", labels);
    }

    public List<String> nlqxLabels(String nlqxRaw) {
        return nlqxItems(nlqxRaw).stream().map(BizJobNlqxItemVO::getLabel).toList();
    }

    /** {@code t_biz_jobs_info.nlqx} → 能力项列表（含字典完整描述） */
    public List<BizJobNlqxItemVO> nlqxItems(String nlqxRaw) {
        if (nlqxRaw == null || nlqxRaw.isBlank()) {
            return List.of();
        }
        List<BizJobNlqxItemVO> items = new ArrayList<>();
        for (String part : nlqxRaw.split(",")) {
            String code = part.trim();
            if (code.isEmpty()) {
                continue;
            }
            String fullName = lookupCodeName(BizDictBm.NL, code);
            BizJobNlqxItemVO item = new BizJobNlqxItemVO();
            item.setCode(code);
            item.setLabel(nlShortLabel(fullName, code));
            item.setDetail(fullName != null && !fullName.isBlank() ? fullName : code);
            items.add(item);
        }
        return items;
    }

    /** 逗号分隔字典编码 → 中文列表（顿号拼接文本） */
    public String commaSeparatedText(String bm, String raw) {
        List<String> labels = commaSeparatedLabels(bm, raw);
        return labels.isEmpty() ? "-" : String.join("、", labels);
    }

    /** 逗号分隔字典编码 → 中文标签列表 */
    public List<String> commaSeparatedLabels(String bm, String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        List<String> labels = new ArrayList<>();
        for (String part : raw.split(",")) {
            String code = part.trim();
            if (code.isEmpty()) {
                continue;
            }
            labels.add(lookupCodeName(bm, code));
        }
        return labels;
    }

    private String lookupCodeName(String bm, String code) {
        Optional<String> byCode = sysCodeRedisCache.lookupNameByCode(bm, code);
        if (byCode.isPresent()) {
            return byCode.get();
        }
        try {
            return label(bm, Integer.parseInt(code));
        } catch (NumberFormatException ignored) {
            return code;
        }
    }

    /** 能力类型长描述取冒号前简称，如「调研型(I)」 */
    private static String nlShortLabel(String fullName, String code) {
        if (fullName == null || fullName.isBlank()) {
            return code;
        }
        int idx = fullName.indexOf('：');
        if (idx < 0) {
            idx = fullName.indexOf(':');
        }
        String head = idx > 0 ? fullName.substring(0, idx).trim() : fullName.trim();
        if (head.length() > 24) {
            head = head.substring(0, 24);
        }
        return head + "(" + code + ")";
    }

    private record GjzDictEntry(String keywordName, String groupId) {
    }

    private volatile Map<String, GjzDictEntry> gjzByDm;
    private volatile Map<String, String> gjzGroupNameById;
    private volatile List<String> gjzGroupOrder;

    private void ensureGjzCache() {
        if (gjzByDm != null) {
            return;
        }
        synchronized (this) {
            if (gjzByDm != null) {
                return;
            }
            loadGjzCache();
        }
    }

    @SuppressWarnings("unchecked")
    private void loadGjzCache() {
        Map<String, String> groupNames = new LinkedHashMap<>();
        List<String> groupOrder = new ArrayList<>();
        sysCodeRedisCache.readBucket(BizDictBm.GJZ_FZ).ifPresent(bucket -> {
            Object itemsObj = bucket.get("items");
            if (!(itemsObj instanceof List<?> items)) {
                return;
            }
            for (Object itemObj : items) {
                if (!(itemObj instanceof Map<?, ?> item)) {
                    continue;
                }
                String id = asString(item.get("id"));
                String name = asString(item.get("name"));
                if (id.isEmpty() || name.isEmpty()) {
                    continue;
                }
                groupNames.put(id, name);
                groupOrder.add(id);
            }
        });

        Map<String, GjzDictEntry> byDm = new LinkedHashMap<>();
        sysCodeRedisCache.readBucket(BizDictBm.GJZ).ifPresent(bucket -> {
            Object itemsObj = bucket.get("items");
            if (!(itemsObj instanceof List<?> items)) {
                return;
            }
            for (Object itemObj : items) {
                if (!(itemObj instanceof Map<?, ?> item)) {
                    continue;
                }
                String dm = asString(item.get("dm"));
                String name = asString(item.get("name"));
                String fid = asString(item.get("fid"));
                if (dm.isEmpty() || name.isEmpty()) {
                    continue;
                }
                byDm.put(dm, new GjzDictEntry(name, fid));
            }
        });

        this.gjzGroupNameById = groupNames;
        this.gjzGroupOrder = groupOrder;
        this.gjzByDm = byDm;
    }

    private String resolveGjzKeywordFallback(String dm) {
        try {
            return label(BizDictBm.GJZ, Integer.parseInt(dm));
        } catch (NumberFormatException ignored) {
            return dm;
        }
    }

    private void appendGjzGroup(List<BizJobGjzGroupVO> result, String groupId, List<String> keywords) {
        if (keywords == null || keywords.isEmpty()) {
            return;
        }
        appendGjzGroupNamed(result, gjzGroupNameOrDefault(groupId), keywords);
    }

    private void appendGjzGroupNamed(List<BizJobGjzGroupVO> result, String groupName, List<String> keywords) {
        if (keywords == null || keywords.isEmpty()) {
            return;
        }
        BizJobGjzGroupVO vo = new BizJobGjzGroupVO();
        vo.setGroupName(groupName);
        vo.setKeywords(List.copyOf(keywords));
        result.add(vo);
    }

    private String gjzGroupNameOrDefault(String groupId) {
        if ("_ungrouped".equals(groupId)) {
            return "其他";
        }
        return gjzGroupNameById.getOrDefault(groupId, "其他");
    }

    private static String asString(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    /**
     * 业务表 varchar 字段存 DM 时的翻译（如 {@code t_biz_compary_info.hylx} → {@link BizDictBm#HYLB}）。
     * 非数字或字典未命中时回退为原字符串。
     */
    public String labelFromCode(String bm, String code) {
        if (code == null || code.isBlank()) {
            return "-";
        }
        String trimmed = code.trim();
        try {
            int dm = Integer.parseInt(trimmed);
            return label(bm, dm);
        } catch (NumberFormatException ignored) {
            return trimmed;
        }
    }

    /** 企业行业类别（{@code job_hylb}）：支持 DM、国标门类字母（A-T）、字典 ID、已是中文名 */
    public String industryLabel(String hylxRaw) {
        if (hylxRaw == null || hylxRaw.isBlank()) {
            return "-";
        }
        String trimmed = hylxRaw.trim();
        String bm = BizDictBm.HYLB;

        // 1) 数字 DM
        try {
            int dm = Integer.parseInt(trimmed);
            Optional<String> byDm = sysCodeRedisCache.lookupName(bm, dm);
            if (byDm.isPresent()) {
                return byDm.get();
            }
        } catch (NumberFormatException ignored) {
            // 非纯数字，继续其它规则
        }

        // 2) GB/T 4754 门类单字母 A-T → sys_code.id 800-819
        if (trimmed.length() == 1) {
            char letter = Character.toUpperCase(trimmed.charAt(0));
            Optional<String> byDmCode = sysCodeRedisCache.lookupNameByCode(bm, String.valueOf(letter));
            if (byDmCode.isPresent()) {
                return byDmCode.get();
            }
            if (letter >= 'A' && letter <= 'T') {
                String topId = String.valueOf(HYLB_GBT_LETTER_ID_BASE + (letter - 'A'));
                Optional<String> byLetter = sysCodeRedisCache.lookupNameById(bm, topId);
                if (byLetter.isPresent()) {
                    return byLetter.get();
                }
            }
        }

        // 3) 字典项 ID（如 808）
        Optional<String> byId = sysCodeRedisCache.lookupNameById(bm, trimmed);
        if (byId.isPresent()) {
            return byId.get();
        }

        // 4) 已是中文行业名或未维护编码，原样展示
        return trimmed;
    }

    /** 拼接省/市/区三级地名（DM 均来自 {@link BizDictBm#XZQH}） */
    public String regionLabel(Integer provinceDm, Integer cityDm, Integer districtDm) {
        return joinXzqh(provinceDm, cityDm, districtDm);
    }

    /** 企业办公地省市区（DM 均来自 {@link BizDictBm#XZQH}） */
    public String companyRegionLabel(Integer provinceDm, Integer cityDm, Integer districtDm) {
        return joinXzqh(provinceDm, cityDm, districtDm);
    }

    private String joinXzqh(Integer provinceDm, Integer cityDm, Integer districtDm) {
        List<String> parts = new ArrayList<>();
        addIfPresent(parts, BizDictBm.XZQH, provinceDm);
        addIfPresent(parts, BizDictBm.XZQH, cityDm);
        addIfPresent(parts, BizDictBm.XZQH, districtDm);
        return parts.isEmpty() ? "-" : String.join(" / ", parts);
    }

    public Optional<String> lookupOptional(String bm, Integer dm) {
        if (dm == null) {
            return Optional.empty();
        }
        return sysCodeRedisCache.lookupName(bm, dm);
    }

    private void addIfPresent(List<String> parts, String bm, Integer dm) {
        if (dm == null) {
            return;
        }
        String text = label(bm, dm);
        if (!text.isBlank() && !"-".equals(text)) {
            parts.add(text);
        }
    }
}
