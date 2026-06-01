package org.example.server_job.interview.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.example.server_job.interview.client.InterviewAiJobClient;
import org.example.server_job.interview.dto.InterviewTurnRequest;
import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.entity.InterviewTurnEntity;
import org.example.server_job.interview.mapper.InterviewSessionMapper;
import org.example.server_job.interview.mapper.InterviewTurnMapper;
import org.example.server_job.interview.service.InterviewAuditService;
import org.example.server_job.interview.service.InterviewTurnService;
import org.example.server_job.interview.support.InterviewContextBundleBuilder;
import org.example.server_job.interview.support.InterviewRequestValidator;
import org.example.server_job.interview.support.InterviewSessionDeltaApplier;
import org.example.server_job.interview.support.InterviewSessionSupport;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

/**
 * 单轮 /turn：幂等查重 → 调 ai_job → 写 interview_turns + 更新 session。
 */
@Service
public class InterviewTurnServiceImpl implements InterviewTurnService {

    private final InterviewAiJobClient aiJobClient;
    private final InterviewTurnMapper turnMapper;
    private final InterviewSessionMapper sessionMapper;
    private final InterviewSessionSupport sessionSupport;
    private final InterviewContextBundleBuilder bundleBuilder;
    private final InterviewSessionDeltaApplier deltaApplier;
    private final InterviewAuditService auditService;
    private final ObjectMapper objectMapper;

    public InterviewTurnServiceImpl(
            InterviewAiJobClient aiJobClient,
            InterviewTurnMapper turnMapper,
            InterviewSessionMapper sessionMapper,
            InterviewSessionSupport sessionSupport,
            InterviewContextBundleBuilder bundleBuilder,
            InterviewSessionDeltaApplier deltaApplier,
            InterviewAuditService auditService,
            ObjectMapper objectMapper
    ) {
        this.aiJobClient = aiJobClient;
        this.turnMapper = turnMapper;
        this.sessionMapper = sessionMapper;
        this.sessionSupport = sessionSupport;
        this.bundleBuilder = bundleBuilder;
        this.deltaApplier = deltaApplier;
        this.auditService = auditService;
        this.objectMapper = objectMapper;
    }

    @Override
    @Transactional
    public Map<String, Object> processTurn(String interviewSessionId, InterviewTurnRequest request) throws Exception {
        String studentId = InterviewRequestValidator.requireStudentId(request.studentId());
        String idemKey = InterviewRequestValidator.requireIdempotencyKey(request.idempotencyKey());

        // 幂等：相同 idempotency_key 直接返回已存结果
        InterviewTurnEntity existing = turnMapper.selectOne(
                new LambdaQueryWrapper<InterviewTurnEntity>()
                        .eq(InterviewTurnEntity::getStudentId, studentId)
                        .eq(InterviewTurnEntity::getIdempotencyKey, idemKey)
                        .last("LIMIT 1")
        );
        if (existing != null && existing.getResultSnapshotJson() != null) {
            return objectMapper.readValue(existing.getResultSnapshotJson(), Map.class);
        }

        InterviewSessionEntity session = sessionSupport.requireSession(interviewSessionId, studentId);
        ensureSessionInProgress(session, request.action());

        ObjectNode turnBody = objectMapper.createObjectNode();
        turnBody.set("context_bundle", bundleBuilder.buildNode(session));
        turnBody.put("turn_id", request.turnId() == null ? UUID.randomUUID().toString() : request.turnId());
        turnBody.put("action", request.action());
        turnBody.set("payload", request.payload() == null ? objectMapper.createObjectNode() : request.payload());
        turnBody.put("user_query", request.userQuery() == null ? "" : request.userQuery());

        JsonNode aiResp = aiJobClient.interviewTurn(turnBody);
        JsonNode resultNode = aiResp.path("result");
        if (resultNode.isMissingNode() || resultNode.isNull()) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "ai_job 未返回 turn result");
        }

        InterviewTurnEntity turn = new InterviewTurnEntity();
        turn.setTurnId(turnBody.get("turn_id").asText());
        turn.setInterviewSessionId(interviewSessionId);
        turn.setStudentId(studentId);
        turn.setIdempotencyKey(idemKey);
        turn.setAction(request.action());
        if (request.payload() != null) {
            turn.setPayloadJson(objectMapper.writeValueAsString(request.payload()));
        }
        turn.setResultSnapshotJson(objectMapper.writeValueAsString(resultNode));
        turn.setProcessedAt(LocalDateTime.now());
        turnMapper.insert(turn);

        deltaApplier.apply(session, resultNode);
        session.setLockVersion(session.getLockVersion() + 1);
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);

        auditService.log(interviewSessionId, studentId, "turn.processed", "ai_job_a",
                Map.of("action", request.action(), "turn_id", turn.getTurnId()), null);

        Map<String, Object> out = objectMapper.convertValue(resultNode, Map.class);
        out.put("interview_session_id", interviewSessionId);
        return out;
    }

    private void ensureSessionInProgress(InterviewSessionEntity session, String action) {
        if ("in_progress".equals(session.getStatus())) {
            return;
        }
        // start 动作允许从 ready 进入进行中
        if ("ready".equals(session.getStatus()) && "start".equals(action)) {
            session.setStatus("in_progress");
            return;
        }
        if (!"in_progress".equals(session.getStatus())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "会话未进行中");
        }
    }
}
