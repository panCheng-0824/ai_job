package org.example.server_job.interview.service.impl;

import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.mapper.InterviewSessionMapper;
import org.example.server_job.interview.service.InterviewAuditService;
import org.example.server_job.interview.service.InterviewSessionLifecycleService;
import org.example.server_job.interview.support.InterviewSessionSupport;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.Map;

/** 会话开始 / 放弃。 */
@Service
public class InterviewSessionLifecycleServiceImpl implements InterviewSessionLifecycleService {

    private final InterviewSessionMapper sessionMapper;
    private final InterviewSessionSupport sessionSupport;
    private final InterviewAuditService auditService;

    public InterviewSessionLifecycleServiceImpl(
            InterviewSessionMapper sessionMapper,
            InterviewSessionSupport sessionSupport,
            InterviewAuditService auditService
    ) {
        this.sessionMapper = sessionMapper;
        this.sessionSupport = sessionSupport;
        this.auditService = auditService;
    }

    @Override
    @Transactional
    public Map<String, Object> start(String interviewSessionId, String studentId) {
        InterviewSessionEntity session = sessionSupport.requireSession(interviewSessionId, studentId);
        if (!"ready".equals(session.getStatus())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "会话状态不允许开始: " + session.getStatus());
        }
        session.setStatus("in_progress");
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        auditService.log(interviewSessionId, studentId, "session.started", "student", Map.of(), null);
        return sessionSupport.sessionToMap(session);
    }

    @Override
    @Transactional
    public Map<String, Object> abandon(String interviewSessionId, String studentId) {
        InterviewSessionEntity session = sessionSupport.requireSession(interviewSessionId, studentId);
        session.setStatus("abandoned");
        session.setUpdatedAt(LocalDateTime.now());
        session.setCompletedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        auditService.log(interviewSessionId, studentId, "session.abandoned", "student", Map.of(), null);
        return sessionSupport.sessionToMap(session);
    }
}
