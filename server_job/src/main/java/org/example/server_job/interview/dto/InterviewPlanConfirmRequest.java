package org.example.server_job.interview.dto;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;
import java.util.Map;

/** 对外 POST /api/interview/plan/confirm 请求体。 */
public record InterviewPlanConfirmRequest(
        String studentId,
        String chatSessionId,
        boolean regenerate,
        String planId,
        Integer planVersion,
        JsonNode plan,
        String messageContext,
        List<Map<String, Object>> contextCards,
        JsonNode snapshots
) {
    public InterviewPlanConfirmRequest {
        if (contextCards == null) {
            contextCards = List.of();
        }
    }
}
