package org.example.server_job.interview.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.example.server_job.interview.client.InterviewAiJobClient;
import org.example.server_job.interview.dto.InterviewPlanConfirmRequest;
import org.example.server_job.interview.dto.InterviewPlanPreviewRequest;
import org.example.server_job.interview.dto.InterviewPlanStartRequest;
import org.example.server_job.interview.service.InterviewAuditService;
import org.example.server_job.interview.service.InterviewPlanService;
import org.example.server_job.interview.support.InterviewIds;
import org.example.server_job.interview.support.InterviewPlanPersistService;
import org.example.server_job.interview.support.InterviewRequestValidator;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

/**
 * 规划阶段：预览转发 ai_job；确认时写入 V2 关系表并创建会话。
 */
@Service
public class InterviewPlanServiceImpl implements InterviewPlanService {

    private final InterviewAiJobClient aiJobClient;
    private final InterviewPlanPersistService persistService;
    private final InterviewAuditService auditService;
    private final ObjectMapper objectMapper;

    public InterviewPlanServiceImpl(
            InterviewAiJobClient aiJobClient,
            InterviewPlanPersistService persistService,
            InterviewAuditService auditService,
            ObjectMapper objectMapper
    ) {
        this.aiJobClient = aiJobClient;
        this.persistService = persistService;
        this.auditService = auditService;
        this.objectMapper = objectMapper;
    }

    @Override
    public JsonNode preview(InterviewPlanPreviewRequest request) throws Exception {
        ObjectNode body = objectMapper.createObjectNode();
        body.put("student_id", request.studentId());
        body.put("message_context", request.messageContext() == null ? "" : request.messageContext());
        body.put("student_context", request.studentContext() == null ? "" : request.studentContext());
        body.set("context_cards", objectMapper.valueToTree(request.contextCards()));
        JsonNode resp = aiJobClient.planPreview(body);
        auditService.log(null, request.studentId(), "plan.preview", "server_job", Map.of(), null);
        return resp;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> confirm(InterviewPlanConfirmRequest request) throws Exception {
        String studentId = InterviewRequestValidator.requireStudentId(request.studentId());
        JsonNode planNode = request.plan();
        if (planNode == null || planNode.isMissingNode()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "缺少 plan");
        }

        String planId = request.planId();
        if (planId == null || planId.isBlank()) {
            planId = planNode.path("plan_id").asText(InterviewIds.newPlanId());
        }
        int version = request.planVersion() != null ? request.planVersion() : planNode.path("version").asInt(1);

        String snapshotsJson = "{}";
        if (request.snapshots() != null && !request.snapshots().isMissingNode()) {
            snapshotsJson = objectMapper.writeValueAsString(request.snapshots());
        }

        JsonNode industryNode = planNode.path("industry_category_id");
        String industryCategoryId = industryNode.isMissingNode() || industryNode.isNull()
                ? null
                : industryNode.asText().isBlank() ? null : industryNode.asText();
        Map<String, Object> out = persistService.persistConfirm(
                studentId,
                planId,
                version,
                planNode,
                null,
                request.chatSessionId(),
                snapshotsJson,
                industryCategoryId
        );

        auditService.log(
                String.valueOf(out.get("interview_session_id")),
                studentId,
                "plan.confirmed",
                "student",
                Map.of("plan_id", planId),
                null
        );
        return out;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> start(InterviewPlanStartRequest request) {
        String studentId = InterviewRequestValidator.requireStudentId(request.studentId());
        if (request.planId() == null || request.planId().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "plan_id 不能为空");
        }
        String chatSessionId = request.chatSessionId() == null ? "" : request.chatSessionId().trim();
        Map<String, Object> out = persistService.startSessionFromBankPlan(
                studentId,
                request.planId().trim(),
                request.planVersion(),
                chatSessionId
        );

        auditService.log(
                String.valueOf(out.get("interview_session_id")),
                studentId,
                "plan.started",
                "student",
                Map.of("plan_id", request.planId().trim()),
                null
        );
        return out;
    }
}
