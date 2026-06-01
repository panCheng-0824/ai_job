package org.example.server_job.interview.support;

import com.fasterxml.jackson.databind.JsonNode;
import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.springframework.stereotype.Component;

/**
 * 将 ai_job TurnResult 中的增量字段写回会话实体（调用方负责 updateById）。
 */
@Component
public class InterviewSessionDeltaApplier {

    public void apply(InterviewSessionEntity session, JsonNode resultNode) {
        if (resultNode.has("phase")) {
            session.setPhase(resultNode.get("phase").asText());
        }
        if (resultNode.has("current_question_index")) {
            session.setCurrentQuestionIndex(resultNode.get("current_question_index").asInt());
        }
        if (resultNode.has("checkpoint_id")) {
            session.setGraphCheckpointId(resultNode.get("checkpoint_id").asText());
        }
        JsonNode delta = resultNode.path("session_delta");
        if (!delta.isMissingNode() && delta.has("token_budget_used")) {
            session.setTokenBudgetUsed(
                    session.getTokenBudgetUsed() + delta.get("token_budget_used").asInt(0)
            );
        }
    }
}
