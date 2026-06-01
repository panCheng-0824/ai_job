package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.example.server_job.interview.entity.InterviewPlanBasicsEntity;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;
import org.example.server_job.interview.mapper.InterviewPlanBasicsMapper;
import org.example.server_job.interview.mapper.InterviewPlanQuestionMapper;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

/**
 * 将 V2 关系表（{@code interview_plan_basics} 及题目子表）组装为 ai_job 所需的 InterviewPlan JSON。
 */
@Component
public class InterviewPlanAssembler {

    private final InterviewPlanBasicsMapper basicsMapper;
    private final InterviewPlanQuestionMapper questionMapper;
    private final InterviewPlanQuestionExtrasSupport questionExtrasSupport;
    private final ObjectMapper objectMapper;

    public InterviewPlanAssembler(
            InterviewPlanBasicsMapper basicsMapper,
            InterviewPlanQuestionMapper questionMapper,
            InterviewPlanQuestionExtrasSupport questionExtrasSupport,
            ObjectMapper objectMapper
    ) {
        this.basicsMapper = basicsMapper;
        this.questionMapper = questionMapper;
        this.questionExtrasSupport = questionExtrasSupport;
        this.objectMapper = objectMapper;
    }

    /**
     * 加载指定版本大纲的完整 JSON（含 questions[]）。
     *
     * @param planId   大纲业务 ID
     * @param version  版本号
     * @return InterviewPlan 结构 JSON 字符串
     */
    public String loadPlanJson(String planId, int version) {
        String rowId = InterviewIds.planRowId(planId, version);
        InterviewPlanBasicsEntity basics = basicsMapper.selectById(rowId);
        if (basics == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "大纲不存在");
        }
        return assembleFromBasics(basics);
    }

    /**
     * 将 basics 行与题目子表拼成标准 InterviewPlan JSON。
     */
    public String assembleFromBasics(InterviewPlanBasicsEntity basics) {
        try {
            ObjectNode root = objectMapper.createObjectNode();
            root.put("plan_id", basics.getPlanId());
            root.put("version", basics.getVersion() == null ? 1 : basics.getVersion());
            root.put("target_role", nullToEmpty(basics.getTargetRole()));
            root.put("source_material_hash", nullToEmpty(basics.getSourceMaterialHash()));
            root.put("rubric_version", nullToEmpty(basics.getRubricVersion(), "v1"));
            root.put("planner_model", nullToEmpty(basics.getPlannerModel()));

            List<InterviewPlanQuestionEntity> questions = questionMapper.selectList(
                    Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                            .eq(InterviewPlanQuestionEntity::getPlanRowId, basics.getPlanRowId())
                            .orderByAsc(InterviewPlanQuestionEntity::getSeqNo)
            );
            InterviewPlanQuestionExtrasSupport.PlanQuestionExtrasSnapshot extrasSnapshot =
                    questionExtrasSupport.loadSnapshotByPlanRowId(basics.getPlanRowId());

            ArrayNode qArr = objectMapper.createArrayNode();
            for (InterviewPlanQuestionEntity q : questions) {
                ObjectNode item = objectMapper.createObjectNode();
                item.put("id", q.getQuestionId());
                item.put("text", nullToEmpty(q.getQuestionText()));
                item.put("weight", q.getWeight() == null ? 1.0 : q.getWeight().doubleValue());
                item.put("thinking_hint", nullToEmpty(q.getThinkingHint()));
                item.put("timeout_seconds", q.getTimeoutSeconds() == null ? 300 : q.getTimeoutSeconds());
                item.put("reference_answer", nullToEmpty(q.getReferenceAnswer()));
                questionExtrasSupport.fillQuestionNode(item, q.getIqRowId(), extrasSnapshot);
                qArr.add(item);
            }
            root.set("questions", qArr);
            return objectMapper.writeValueAsString(root);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "组装大纲 JSON 失败");
        }
    }

    private static String nullToEmpty(String v) {
        return v == null ? "" : v;
    }

    private static String nullToEmpty(String v, String defaultVal) {
        if (v == null || v.isBlank()) {
            return defaultVal;
        }
        return v;
    }
}
