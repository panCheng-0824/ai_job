package org.example.server_job.student.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.example.server_job.biz.support.StudentPortraitChineseJsonTranslator;
import org.example.server_job.biz.vo.BizStudentPortraitVO;
import org.example.server_job.student.entity.StudentProfileExt;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 将学籍画像 {@link BizStudentPortraitVO} 与学生扩展 {@link StudentProfileExt} 合并为前端统一结构。
 */
public final class StudentProfileMergeSupport {

    public static final String SECTION_JOB_INTENT = "求职意向";
    public static final String SECTION_ABILITY = "能力画像";

    private static final String[] RADAR_KEYS = {
            "professional", "communication", "office", "comprehensive", "practice"
    };
    private static final String[] RADAR_LABELS = {
            "专业能力", "沟通能力", "办公技能", "综合素养", "实践能力"
    };

    private StudentProfileMergeSupport() {
    }

    public static ObjectNode merge(
            ObjectMapper mapper,
            BizStudentPortraitVO portrait,
            StudentProfileExt ext
    ) {
        JsonNode baseTree = StudentPortraitChineseJsonTranslator.toFullPortraitChineseTree(mapper, portrait);
        ObjectNode root = baseTree.deepCopy();

        ObjectNode student = (ObjectNode) root.path("学生基本信息");
        if (!student.isObject()) {
            student = mapper.createObjectNode();
            root.set("学生基本信息", student);
        }

        JsonNode jobIntent = readJobIntent(mapper, ext);
        JsonNode ability = readAbility(mapper, ext, portrait, jobIntent);

        if (ext != null) {
            putIfPresent(student, "手机", ext.getPhone());
            putIfPresent(student, "邮箱", ext.getEmail());
            putIfPresent(student, "头像", ext.getAvatarUrl());
            putIfPresent(student, "校园经历补充", ext.getCampusExperience());
        } else {
            student.putNull("手机");
            student.putNull("邮箱");
            student.putNull("头像");
            student.putNull("校园经历补充");
        }

        root.set(SECTION_JOB_INTENT, toJobIntentSection(mapper, jobIntent));
        root.set(SECTION_ABILITY, toAbilitySection(mapper, ability, portrait));
        return root;
    }

    public static Map<String, Object> toApiMap(ObjectMapper mapper, ObjectNode root) {
        try {
            return mapper.convertValue(root, mapper.getTypeFactory().constructMapType(
                    LinkedHashMap.class, String.class, Object.class
            ));
        } catch (Exception ex) {
            return Map.of();
        }
    }

    public static ObjectNode defaultJobIntent(ObjectMapper mapper) {
        ObjectNode n = mapper.createObjectNode();
        n.set("targetRoles", mapper.createArrayNode());
        n.set("targetCities", mapper.createArrayNode());
        n.putNull("salaryMin");
        n.putNull("salaryMax");
        n.put("salaryNegotiable", true);
        n.set("targetCompanies", mapper.createArrayNode());
        n.put("queryText", "");
        return n;
    }

    public static ObjectNode defaultAbility(ObjectMapper mapper, BizStudentPortraitVO portrait) {
        ObjectNode n = mapper.createObjectNode();
        n.set("tags", mapper.createArrayNode());
        ObjectNode radar = computeDefaultRadar(mapper, portrait);
        n.set("radar", radar);
        n.put("radarSource", "computed");
        return n;
    }

    public static ObjectNode computeDefaultRadar(ObjectMapper mapper, BizStudentPortraitVO portrait) {
        double gpa = 0;
        if (portrait != null && portrait.getStudentInfo() != null && portrait.getStudentInfo().getPjjd() != null) {
            gpa = portrait.getStudentInfo().getPjjd();
        }
        int awardCount = portrait != null && portrait.getAwardInfoList() != null
                ? portrait.getAwardInfoList().size() : 0;
        int base = gpa > 0 ? Math.min(95, (int) Math.round(gpa * 22)) : 72;
        int boost = Math.min(12, awardCount * 3);

        ObjectNode radar = mapper.createObjectNode();
        radar.put(RADAR_KEYS[0], base);
        radar.put(RADAR_KEYS[1], 68 + boost);
        radar.put(RADAR_KEYS[2], 70 + Math.floor(boost / 2.0));
        radar.put(RADAR_KEYS[3], 74 + boost);
        radar.put(RADAR_KEYS[4], 66 + boost);
        return radar;
    }

    public static List<String> computeSuggestedTags(BizStudentPortraitVO portrait) {
        Set<String> out = new LinkedHashSet<>();
        if (portrait != null && portrait.getAwardInfoList() != null) {
            for (var award : portrait.getAwardInfoList()) {
                if (award.getXmmc() != null && !award.getXmmc().isBlank()) {
                    out.add(truncate(award.getXmmc(), 20));
                } else if (award.getXmlx() != null && !award.getXmlx().isBlank()) {
                    out.add(truncate(award.getXmlx(), 20));
                }
            }
        }
        if (portrait != null && portrait.getStudentInfo() != null) {
            if (portrait.getStudentInfo().getZymc() != null) {
                out.add(truncate(portrait.getStudentInfo().getZymc(), 20));
            }
            if (portrait.getStudentInfo().getXl() != null) {
                out.add(truncate(portrait.getStudentInfo().getXl(), 20));
            }
        }
        return new ArrayList<>(out).subList(0, Math.min(10, out.size()));
    }

    public static String formatSalaryDisplay(JsonNode jobIntent) {
        if (jobIntent == null || jobIntent.isNull()) {
            return "面议";
        }
        if (jobIntent.path("salaryNegotiable").asBoolean(false)) {
            return "面议";
        }
        Integer min = readIntOrNull(jobIntent.get("salaryMin"));
        Integer max = readIntOrNull(jobIntent.get("salaryMax"));
        if (min != null && max != null) {
            return formatK(min) + "-" + formatK(max);
        }
        if (min != null) {
            return formatK(min) + "起";
        }
        if (max != null) {
            return "≤" + formatK(max);
        }
        return "面议";
    }

    public static String writeJson(ObjectMapper mapper, JsonNode node) {
        try {
            return mapper.writeValueAsString(node);
        } catch (Exception ex) {
            throw new IllegalStateException("JSON 序列化失败", ex);
        }
    }

    public static JsonNode readJobIntent(ObjectMapper mapper, StudentProfileExt ext) {
        if (ext == null || ext.getJobIntentJson() == null || ext.getJobIntentJson().isBlank()) {
            return defaultJobIntent(mapper);
        }
        try {
            return mapper.readTree(ext.getJobIntentJson());
        } catch (Exception ex) {
            return defaultJobIntent(mapper);
        }
    }

    public static JsonNode readAbility(ObjectMapper mapper, StudentProfileExt ext, BizStudentPortraitVO portrait, JsonNode jobIntent) {
        if (ext == null || ext.getAbilityJson() == null || ext.getAbilityJson().isBlank()) {
            return defaultAbility(mapper, portrait);
        }
        try {
            JsonNode parsed = mapper.readTree(ext.getAbilityJson());
            if (!parsed.isObject()) {
                return defaultAbility(mapper, portrait);
            }
            ObjectNode out = (ObjectNode) parsed.deepCopy();
            if (!out.has("tags") || !out.get("tags").isArray()) {
                out.set("tags", mapper.createArrayNode());
            }
            JsonNode radar = out.get("radar");
            if (radar == null || !radar.isObject() || radar.isEmpty()) {
                out.set("radar", computeDefaultRadar(mapper, portrait));
                out.put("radarSource", "computed");
            }
            if (!out.has("radarSource")) {
                out.put("radarSource", "manual");
            }
            return out;
        } catch (Exception ex) {
            return defaultAbility(mapper, portrait);
        }
    }

    private static ObjectNode toJobIntentSection(ObjectMapper mapper, JsonNode jobIntent) {
        ObjectNode section = mapper.createObjectNode();
        section.set("意向岗位", toStringArray(mapper, jobIntent.path("targetRoles")));
        section.set("意向城市", toStringArray(mapper, jobIntent.path("targetCities")));
        section.put("期望薪资", formatSalaryDisplay(jobIntent));
        section.set("意向企业", toStringArray(mapper, jobIntent.path("targetCompanies")));
        section.put("综合诉求", jobIntent.path("queryText").asText(""));
        section.put("salaryNegotiable", jobIntent.path("salaryNegotiable").asBoolean(true));
        if (jobIntent.has("salaryMin") && !jobIntent.get("salaryMin").isNull()) {
            section.set("salaryMin", jobIntent.get("salaryMin"));
        } else {
            section.putNull("salaryMin");
        }
        if (jobIntent.has("salaryMax") && !jobIntent.get("salaryMax").isNull()) {
            section.set("salaryMax", jobIntent.get("salaryMax"));
        } else {
            section.putNull("salaryMax");
        }
        return section;
    }

    private static ObjectNode toAbilitySection(ObjectMapper mapper, JsonNode ability, BizStudentPortraitVO portrait) {
        ObjectNode section = mapper.createObjectNode();
        section.set("标签", toStringArray(mapper, ability.path("tags")));
        section.set("推荐标签", toStringArray(mapper, mapper.valueToTree(computeSuggestedTags(portrait))));

        ObjectNode radarCn = mapper.createObjectNode();
        JsonNode radar = ability.path("radar");
        for (int i = 0; i < RADAR_KEYS.length; i++) {
            int val = radar.path(RADAR_KEYS[i]).asInt(0);
            if (val <= 0) {
                val = computeDefaultRadar(mapper, portrait).path(RADAR_KEYS[i]).asInt(72);
            }
            radarCn.put(RADAR_LABELS[i], Math.max(0, Math.min(100, val)));
        }
        section.set("雷达", radarCn);
        section.put("radarSource", ability.path("radarSource").asText("computed"));

        ObjectNode radarEn = mapper.createObjectNode();
        for (String key : RADAR_KEYS) {
            radarEn.set(key, radar.path(key));
        }
        section.set("radarRaw", radarEn);
        return section;
    }

    private static ArrayNode toStringArray(ObjectMapper mapper, JsonNode node) {
        ArrayNode arr = mapper.createArrayNode();
        if (node == null || !node.isArray()) {
            return arr;
        }
        for (JsonNode item : node) {
            String s = item.asText("").trim();
            if (!s.isEmpty()) {
                arr.add(s);
            }
        }
        return arr;
    }

    private static void putIfPresent(ObjectNode obj, String key, String value) {
        if (value == null || value.isBlank()) {
            obj.putNull(key);
        } else {
            obj.put(key, value.trim());
        }
    }

    private static Integer readIntOrNull(JsonNode node) {
        if (node == null || node.isNull()) {
            return null;
        }
        int v = node.asInt(-1);
        return v >= 0 ? v : null;
    }

    private static String formatK(int yuan) {
        if (yuan >= 1000 && yuan % 1000 == 0) {
            return (yuan / 1000) + "k";
        }
        return yuan + "元";
    }

    private static String truncate(String text, int max) {
        if (text == null) {
            return "";
        }
        return text.length() <= max ? text : text.substring(0, max);
    }
}
