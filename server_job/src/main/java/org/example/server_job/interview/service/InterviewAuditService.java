package org.example.server_job.interview.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.interview.entity.InterviewAuditLogEntity;
import org.example.server_job.interview.mapper.InterviewAuditLogMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;

/** 审计日志写入（状态变更、turn、规划确认）。 */
@Service
public class InterviewAuditService {

    private final InterviewAuditLogMapper auditLogMapper;
    private final ObjectMapper objectMapper;

    public InterviewAuditService(InterviewAuditLogMapper auditLogMapper, ObjectMapper objectMapper) {
        this.auditLogMapper = auditLogMapper;
        this.objectMapper = objectMapper;
    }

    public void log(
            String interviewSessionId,
            String studentId,
            String eventType,
            String actor,
            Map<String, Object> detail,
            String traceId
    ) {
        try {
            InterviewAuditLogEntity row = new InterviewAuditLogEntity();
            row.setInterviewSessionId(interviewSessionId);
            row.setStudentId(studentId == null ? "" : studentId);
            row.setEventType(eventType);
            row.setActor(actor == null ? "system" : actor);
            if (detail != null && !detail.isEmpty()) {
                row.setDetailJson(objectMapper.writeValueAsString(detail));
            }
            row.setTraceId(traceId);
            row.setCreatedAt(LocalDateTime.now());
            auditLogMapper.insert(row);
        } catch (Exception ignored) {
            // 审计失败不阻断主流程
        }
    }
}
