package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.example.server_job.interview.entity.InterviewPlanQuestionCriteriaEntity;
import org.example.server_job.interview.entity.InterviewPlanQuestionDimensionEntity;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;
import org.example.server_job.interview.entity.InterviewPlanQuestionFollowupEntity;
import org.example.server_job.interview.mapper.InterviewPlanQuestionCriteriaMapper;
import org.example.server_job.interview.mapper.InterviewPlanQuestionDimensionMapper;
import org.example.server_job.interview.mapper.InterviewPlanQuestionFollowupMapper;
import org.example.server_job.interview.mapper.InterviewPlanQuestionMapper;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 大纲题目附属子表读写：考察维度、预设追问、评分标准。
 *
 * <p>供 MQ 落库、confirm 落库与 {@link InterviewPlanAssembler} 组装 JSON 共用，
 * 避免 dimensions / preset_followups / eval_criteria 仍嵌在 payload_json 中。
 */
@Component
public class InterviewPlanQuestionExtrasSupport {

    private static final int CRITERION_VALUE_MAX_LEN = 512;

    private final InterviewPlanQuestionMapper questionMapper;
    private final InterviewPlanQuestionDimensionMapper dimensionMapper;
    private final InterviewPlanQuestionFollowupMapper followupMapper;
    private final InterviewPlanQuestionCriteriaMapper criteriaMapper;

    public InterviewPlanQuestionExtrasSupport(
            InterviewPlanQuestionMapper questionMapper,
            InterviewPlanQuestionDimensionMapper dimensionMapper,
            InterviewPlanQuestionFollowupMapper followupMapper,
            InterviewPlanQuestionCriteriaMapper criteriaMapper
    ) {
        this.questionMapper = questionMapper;
        this.dimensionMapper = dimensionMapper;
        this.followupMapper = followupMapper;
        this.criteriaMapper = criteriaMapper;
    }

    /**
     * 从单题 JSON 写入附属子表（主表行须已 insert）。
     *
     * @param iqRowId 题目物理主键
     * @param qNode   ai_job QuestionItem 结构节点
     */
    public void persistFromQuestionJson(String iqRowId, JsonNode qNode) {
        if (iqRowId == null || iqRowId.isBlank() || qNode == null || !qNode.isObject()) {
            return;
        }
        persistDimensions(iqRowId, qNode.path("dimensions"));
        persistFollowups(iqRowId, qNode.path("preset_followups"));
        persistCriteria(iqRowId, qNode.path("eval_criteria"));
    }

    /**
     * 删除某大纲版本下全部题目的附属行（须在删 interview_plan_questions 之前调用）。
     */
    public void deleteByPlanRowId(String planRowId) {
        if (planRowId == null || planRowId.isBlank()) {
            return;
        }
        List<InterviewPlanQuestionEntity> questions = questionMapper.selectList(
                Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanRowId, planRowId)
                        .select(InterviewPlanQuestionEntity::getIqRowId)
        );
        for (InterviewPlanQuestionEntity q : questions) {
            deleteByIqRowId(q.getIqRowId());
        }
    }

    /** 按题目物理主键删除其全部附属行 */
    public void deleteByIqRowId(String iqRowId) {
        if (iqRowId == null || iqRowId.isBlank()) {
            return;
        }
        dimensionMapper.delete(
                Wrappers.<InterviewPlanQuestionDimensionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionDimensionEntity::getIqRowId, iqRowId)
        );
        followupMapper.delete(
                Wrappers.<InterviewPlanQuestionFollowupEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionFollowupEntity::getIqRowId, iqRowId)
        );
        criteriaMapper.delete(
                Wrappers.<InterviewPlanQuestionCriteriaEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionCriteriaEntity::getIqRowId, iqRowId)
        );
    }

    /**
     * 批量加载某大纲版本下全部题目的附属数据，供组装 JSON 时 O(1) 查找。
     */
    public PlanQuestionExtrasSnapshot loadSnapshotByPlanRowId(String planRowId) {
        PlanQuestionExtrasSnapshot snapshot = new PlanQuestionExtrasSnapshot();
        if (planRowId == null || planRowId.isBlank()) {
            return snapshot;
        }
        List<InterviewPlanQuestionEntity> questions = questionMapper.selectList(
                Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanRowId, planRowId)
                        .select(InterviewPlanQuestionEntity::getIqRowId)
        );
        if (questions.isEmpty()) {
            return snapshot;
        }
        List<String> iqRowIds = new ArrayList<>(questions.size());
        for (InterviewPlanQuestionEntity q : questions) {
            iqRowIds.add(q.getIqRowId());
        }

        List<InterviewPlanQuestionDimensionEntity> dims = dimensionMapper.selectList(
                Wrappers.<InterviewPlanQuestionDimensionEntity>lambdaQuery()
                        .in(InterviewPlanQuestionDimensionEntity::getIqRowId, iqRowIds)
                        .orderByAsc(InterviewPlanQuestionDimensionEntity::getSortNo)
        );
        for (InterviewPlanQuestionDimensionEntity row : dims) {
            snapshot.dimensionsByIqRowId
                    .computeIfAbsent(row.getIqRowId(), k -> new ArrayList<>())
                    .add(row.getDimensionCode());
        }

        List<InterviewPlanQuestionFollowupEntity> followups = followupMapper.selectList(
                Wrappers.<InterviewPlanQuestionFollowupEntity>lambdaQuery()
                        .in(InterviewPlanQuestionFollowupEntity::getIqRowId, iqRowIds)
                        .orderByAsc(InterviewPlanQuestionFollowupEntity::getSeqNo)
        );
        for (InterviewPlanQuestionFollowupEntity row : followups) {
            snapshot.followupsByIqRowId
                    .computeIfAbsent(row.getIqRowId(), k -> new ArrayList<>())
                    .add(row.getFollowupText());
        }

        List<InterviewPlanQuestionCriteriaEntity> criteria = criteriaMapper.selectList(
                Wrappers.<InterviewPlanQuestionCriteriaEntity>lambdaQuery()
                        .in(InterviewPlanQuestionCriteriaEntity::getIqRowId, iqRowIds)
                        .orderByAsc(InterviewPlanQuestionCriteriaEntity::getSortNo)
        );
        for (InterviewPlanQuestionCriteriaEntity row : criteria) {
            snapshot.criteriaByIqRowId
                    .computeIfAbsent(row.getIqRowId(), k -> new LinkedHashMap<>())
                    .put(row.getCriterionKey(), row.getCriterionValue());
        }
        return snapshot;
    }

    /**
     * 将附属字段写入题目 JSON 节点（dimensions / preset_followups / eval_criteria）。
     */
    public void fillQuestionNode(ObjectNode item, String iqRowId, PlanQuestionExtrasSnapshot snapshot) {
        ArrayNode dimArr = item.putArray("dimensions");
        for (String code : snapshot.dimensionsOf(iqRowId)) {
            dimArr.add(code);
        }
        ArrayNode followArr = item.putArray("preset_followups");
        for (String text : snapshot.followupsOf(iqRowId)) {
            followArr.add(text);
        }
        ObjectNode criteriaNode = item.putObject("eval_criteria");
        for (Map.Entry<String, String> entry : snapshot.criteriaOf(iqRowId).entrySet()) {
            criteriaNode.put(entry.getKey(), entry.getValue());
        }
    }

    private void persistDimensions(String iqRowId, JsonNode dimensionsNode) {
        if (dimensionsNode == null || !dimensionsNode.isArray()) {
            return;
        }
        int sort = 0;
        for (JsonNode node : dimensionsNode) {
            String code = node.asText("").trim();
            if (code.isEmpty()) {
                continue;
            }
            InterviewPlanQuestionDimensionEntity row = new InterviewPlanQuestionDimensionEntity();
            row.setIqRowId(iqRowId);
            row.setDimensionCode(code);
            row.setSortNo(sort++);
            dimensionMapper.insert(row);
        }
    }

    private void persistFollowups(String iqRowId, JsonNode followupsNode) {
        if (followupsNode == null || !followupsNode.isArray()) {
            return;
        }
        int seq = 0;
        for (JsonNode node : followupsNode) {
            String text = node.asText("").trim();
            if (text.isEmpty()) {
                continue;
            }
            InterviewPlanQuestionFollowupEntity row = new InterviewPlanQuestionFollowupEntity();
            row.setIqRowId(iqRowId);
            row.setSeqNo(seq++);
            row.setFollowupText(text);
            followupMapper.insert(row);
        }
    }

    private void persistCriteria(String iqRowId, JsonNode criteriaNode) {
        if (criteriaNode == null || !criteriaNode.isObject()) {
            return;
        }
        int sort = 0;
        Iterator<Map.Entry<String, JsonNode>> fields = criteriaNode.fields();
        while (fields.hasNext()) {
            Map.Entry<String, JsonNode> entry = fields.next();
            String key = entry.getKey() == null ? "" : entry.getKey().trim();
            if (key.isEmpty()) {
                continue;
            }
            InterviewPlanQuestionCriteriaEntity row = new InterviewPlanQuestionCriteriaEntity();
            row.setIqRowId(iqRowId);
            row.setCriterionKey(key);
            row.setCriterionValue(truncateCriterionValue(nodeToCriterionValue(entry.getValue())));
            row.setSortNo(sort++);
            criteriaMapper.insert(row);
        }
    }

    /** 评分项值：标量转字符串，复杂结构保留 JSON 文本 */
    private static String nodeToCriterionValue(JsonNode node) {
        if (node == null || node.isNull()) {
            return "";
        }
        if (node.isTextual()) {
            return node.asText("");
        }
        if (node.isNumber() || node.isBoolean()) {
            return node.asText("");
        }
        return node.toString();
    }

    private static String truncateCriterionValue(String value) {
        if (value == null) {
            return "";
        }
        if (value.length() <= CRITERION_VALUE_MAX_LEN) {
            return value;
        }
        return value.substring(0, CRITERION_VALUE_MAX_LEN);
    }

    /**
     * 某大纲版本下题目附属数据的内存快照。
     */
    public static final class PlanQuestionExtrasSnapshot {

        private final Map<String, List<String>> dimensionsByIqRowId = new LinkedHashMap<>();
        private final Map<String, List<String>> followupsByIqRowId = new LinkedHashMap<>();
        private final Map<String, Map<String, String>> criteriaByIqRowId = new LinkedHashMap<>();

        public List<String> dimensionsOf(String iqRowId) {
            return dimensionsByIqRowId.getOrDefault(iqRowId, List.of());
        }

        public List<String> followupsOf(String iqRowId) {
            return followupsByIqRowId.getOrDefault(iqRowId, List.of());
        }

        public Map<String, String> criteriaOf(String iqRowId) {
            return criteriaByIqRowId.getOrDefault(iqRowId, Map.of());
        }
    }
}
