package org.example.server_job.interview.dto;

import com.fasterxml.jackson.databind.JsonNode;

/** 对外 POST /api/interview/{id}/turn 请求体。 */
public record InterviewTurnRequest(
        String studentId,
        String turnId,
        String idempotencyKey,
        String action,
        JsonNode payload,
        String userQuery
) {
}
