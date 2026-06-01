package org.example.server_job.interview.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * 大纲题目保存项。
 *
 * @param questionId     题目业务 ID，如 q001
 * @param text           题干
 * @param weight         权重
 * @param thinkingHint   思考提示
 * @param timeoutSeconds 超时秒数
 */
public record InterviewPlanQuestionSaveItem(
        @JsonProperty("question_id") String questionId,
        @JsonProperty("text") String text,
        @JsonProperty("weight") Double weight,
        @JsonProperty("thinking_hint") String thinkingHint,
        @JsonProperty("timeout_seconds") Integer timeoutSeconds
) {
}
