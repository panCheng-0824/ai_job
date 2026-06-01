package org.example.server_job.interview.service;

import com.fasterxml.jackson.databind.JsonNode;
import org.example.server_job.interview.dto.InterviewPlanConfirmRequest;
import org.example.server_job.interview.dto.InterviewPlanPreviewRequest;
import org.example.server_job.interview.dto.InterviewPlanStartRequest;

import java.util.Map;

/** 规划阶段：预览大纲、确认入库并创建会话。 */
public interface InterviewPlanService {

    JsonNode preview(InterviewPlanPreviewRequest request) throws Exception;

    Map<String, Object> confirm(InterviewPlanConfirmRequest request) throws Exception;

    /**
     * 按 plan_id 从题库加载大纲，创建 {@code interview_sessions} 与 {@code student_interview_records}。
     */
    Map<String, Object> start(InterviewPlanStartRequest request);
}
