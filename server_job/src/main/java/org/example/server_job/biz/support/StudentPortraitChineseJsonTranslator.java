package org.example.server_job.biz.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.example.server_job.biz.vo.BizStudentPortraitVO;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 将 {@link BizStudentPortraitVO} 转为「完整学生资料」JSON：结构与前端展开 JSON 一致，
 * 字段 key 均为 dbData/*.sql 列 COMMENT 的中文名；缺失或非 null 的字段一律写出（值为 JSON null）。
 * Redis 与 HTTP GET /api/students/{id} 共用同一套输出。
 */
public final class StudentPortraitChineseJsonTranslator {

    static final String SECTION_STUDENT = "学生基本信息";
    static final String SECTION_FAMILY = "家庭信息";
    static final String SECTION_AWARD = "奖励信息";
    static final String SECTION_XLZX_ZX = "心理咨询申请";
    static final String SECTION_XLZX_GY = "心理咨询概要";
    static final String SECTION_XLZX_GD = "心理咨询归档";

    private static final Map<String, String> STUDENT_FIELDS = studentFields();
    private static final Map<String, String> FAMILY_FIELDS = familyFields();
    private static final Map<String, String> AWARD_FIELDS = awardFields();
    private static final Map<String, String> XLZX_ZX_FIELDS = xlzxZxFields();
    private static final Map<String, String> XLZX_GY_FIELDS = xlzxGyFields();
    private static final Map<String, String> XLZX_GD_FIELDS = xlzxGdFields();

    private StudentPortraitChineseJsonTranslator() {
    }

    public static JsonNode toFullPortraitChineseTree(ObjectMapper mapper, BizStudentPortraitVO portrait) {
        JsonNode tree = mapper.valueToTree(portrait);
        ObjectNode root = mapper.createObjectNode();
        root.set(SECTION_STUDENT, fillObject(tree.path("studentInfo"), STUDENT_FIELDS, mapper));
        root.set(SECTION_FAMILY, fillArray(tree.path("familyInfoList"), FAMILY_FIELDS, mapper));
        root.set(SECTION_AWARD, fillArray(tree.path("awardInfoList"), AWARD_FIELDS, mapper));
        root.set(SECTION_XLZX_ZX, fillArray(tree.path("counselingRecordList"), XLZX_ZX_FIELDS, mapper));
        root.set(SECTION_XLZX_GY, fillArray(tree.path("counselorRecordList"), XLZX_GY_FIELDS, mapper));
        root.set(SECTION_XLZX_GD, fillArray(tree.path("trackingRecordList"), XLZX_GD_FIELDS, mapper));
        return root;
    }

    public static String toRedisJson(ObjectMapper mapper, BizStudentPortraitVO portrait) throws Exception {
        return mapper.writeValueAsString(toFullPortraitChineseTree(mapper, portrait));
    }

    private static ObjectNode fillObject(JsonNode srcObj, Map<String, String> pyToCn, ObjectMapper mapper) {
        ObjectNode out = mapper.createObjectNode();
        boolean hasObj = srcObj != null && !srcObj.isNull() && srcObj.isObject();
        for (Map.Entry<String, String> e : pyToCn.entrySet()) {
            String py = e.getKey();
            String cn = e.getValue();
            if (hasObj && srcObj.has(py) && !srcObj.get(py).isNull()) {
                out.set(cn, srcObj.get(py).deepCopy());
            } else {
                out.putNull(cn);
            }
        }
        return out;
    }

    private static ArrayNode fillArray(JsonNode srcArr, Map<String, String> pyToCn, ObjectMapper mapper) {
        ArrayNode out = mapper.createArrayNode();
        if (srcArr == null || srcArr.isNull() || !srcArr.isArray()) {
            return out;
        }
        for (JsonNode item : srcArr) {
            out.add(fillObject(item, pyToCn, mapper));
        }
        return out;
    }

    /** t_biz_student_info.sql COMMENT */
    private static Map<String, String> studentFields() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("xxmc", "学校名称");
        m.put("yxmc", "院系名称");
        m.put("csrq", "出生日期");
        m.put("zymc", "专业名称");
        m.put("bjmc", "班级名称");
        m.put("xm", "姓名");
        m.put("xh", "学号");
        m.put("zjh", "证件号");
        m.put("mz", "民族");
        m.put("xl", "学历");
        m.put("bynd", "毕业年度");
        m.put("byjj", "毕业季节");
        m.put("xb", "性别");
        m.put("pjjd", "平均绩点");
        m.put("tccj", "体测成绩");
        return Map.copyOf(m);
    }

    /** t_biz_family_info.sql COMMENT */
    private static Map<String, String> familyFields() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("xh", "学号");
        m.put("jzxn", "家长姓名");
        m.put("ybrgx", "与本人关系");
        m.put("jzcsrq", "家长出生日期");
        m.put("zjlx", "证件类型");
        m.put("jzzjh", "家长证件号");
        m.put("jzdw", "家长单位");
        m.put("jzzw", "家长职务");
        m.put("jzzy", "家长职业");
        m.put("jayzbm", "家长邮政编码");
        m.put("jalxdh", "家长联系电话");
        m.put("jzsj", "家长手机号");
        m.put("pjysr", "平均月收入");
        return Map.copyOf(m);
    }

    /** t_biz_award_info.sql COMMENT */
    private static Map<String, String> awardFields() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("xh", "学号");
        m.put("jxnd", "奖项年度");
        m.put("xmmc", "项目名称");
        m.put("xmms", "项目描述");
        m.put("xmlx", "项目类别");
        return Map.copyOf(m);
    }

    /** t_biz_xlzx_zx.sql COMMENT */
    private static Map<String, String> xlzxZxFields() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("wid", "申请ID");
        m.put("xh", "学号");
        m.put("nd", "年度");
        m.put("zxyt", "咨询议题");
        m.put("zxxg", "咨询效果");
        m.put("zxsj", "咨询时间");
        return Map.copyOf(m);
    }

    /** t_biz_xlzx_gy.sql COMMENT */
    private static Map<String, String> xlzxGyFields() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("wid", "记录ID");
        m.put("xh", "学号");
        m.put("zxid", "咨询申请ID");
        m.put("zssj", "咨询时间");
        m.put("zxgy", "咨询概要");
        return Map.copyOf(m);
    }

    /** t_biz_xlzx_gd.sql COMMENT（wid 注释为 WID，现为中文「档案主键」便于理解） */
    private static Map<String, String> xlzxGdFields() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("xh", "学号");
        m.put("wid", "档案主键");
        m.put("sqid", "咨询ID");
        m.put("tjsj", "添加时间");
        m.put("xqwt", "寻求问题");
        m.put("wtpg", "问题评估");
        m.put("zxxg", "咨询效果");
        m.put("xszt", "学生状态");
        m.put("yxhz", "院系合作");
        m.put("qtqk", "其他情况");
        return Map.copyOf(m);
    }
}
