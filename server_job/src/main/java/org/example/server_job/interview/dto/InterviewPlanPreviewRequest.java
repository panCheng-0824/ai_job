package org.example.server_job.interview.dto;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;
import java.util.Map;

/** 对外 POST /api/interview/plan/preview 请求体。 */
public record InterviewPlanPreviewRequest(
        String studentId,
        String messageContext,
        List<Map<String, Object>> contextCards,
        String studentContext
) {
    public InterviewPlanPreviewRequest {
        if (contextCards == null) {
            contextCards = List.of();
        }
    }
}
