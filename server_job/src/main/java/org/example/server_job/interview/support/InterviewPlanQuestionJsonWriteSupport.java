package org.example.server_job.interview.support;

import com.fasterxml.jackson.databind.JsonNode;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;
import org.example.server_job.interview.mapper.InterviewPlanQuestionMapper;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 从 ai_job InterviewPlan JSON 写入大纲题目主表及附属子表。
 *
 * <p>MQ 落库（{@link InterviewPlanBankWriteSupport}）与 confirm 落库
 * （{@link InterviewPlanPersistService}）共用，保证拆解逻辑一致。
 */
@Component
public class InterviewPlanQuestionJsonWriteSupport {

    private final InterviewPlanQuestionMapper questionMapper;
    private final InterviewPlanQuestionExtrasSupport extrasSupport;

    public InterviewPlanQuestionJsonWriteSupport(
            InterviewPlanQuestionMapper questionMapper,
            InterviewPlanQuestionExtrasSupport extrasSupport
    ) {
        this.questionMapper = questionMapper;
        this.extrasSupport = extrasSupport;
    }

    /**
     * 将 questions[] 逐题写入 {@code interview_plan_questions} 及维度/追问/评分子表。
     *
     * @return 实际写入题目数
     */
    public int insertQuestionsFromJson(
            String planRowId,
            String planId,
            int version,
            JsonNode questionsNode,
            LocalDateTime now
    ) {
        if (questionsNode == null || !questionsNode.isArray()) {
            return 0;
        }
        int seq = 0;
        for (JsonNode q : questionsNode) {
            String questionId = q.path("id").asText("q" + (seq + 1));
            String iqRowId = InterviewIds.questionRowId(planRowId, questionId);

            InterviewPlanQuestionEntity row = new InterviewPlanQuestionEntity();
            row.setIqRowId(iqRowId);
            row.setPlanRowId(planRowId);
            row.setPlanId(planId);
            row.setPlanVersion(version);
            row.setQuestionId(questionId);
            row.setSeqNo(seq++);
            row.setQuestionText(q.path("text").asText(""));
            row.setWeight(BigDecimal.valueOf(q.path("weight").asDouble(1.0)));
            row.setThinkingHint(q.path("thinking_hint").asText(""));
            row.setTimeoutSeconds(q.path("timeout_seconds").asInt(300));
            row.setReferenceAnswer(q.path("reference_answer").asText(""));
            row.setCreatedAt(now);
            questionMapper.insert(row);

            // 主表写入后再拆附属子表，便于按 iq_row_id 关联
            extrasSupport.persistFromQuestionJson(iqRowId, q);
        }
        return seq;
    }
}
