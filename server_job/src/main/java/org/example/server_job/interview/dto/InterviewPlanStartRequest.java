package org.example.server_job.interview.dto;

/** 对外 POST /api/interview/plan/start：基于已入库大纲创建面试会话与学生记录。 */
public record InterviewPlanStartRequest(
        String studentId,
        String planId,
        Integer planVersion,
        String chatSessionId
) {
}
