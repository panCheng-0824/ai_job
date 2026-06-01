package org.example.server_job.interview.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.interview.entity.InterviewReportEntity;
import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.mapper.InterviewReportMapper;
import org.example.server_job.interview.service.InterviewReportQueryService;
import org.example.server_job.interview.support.InterviewSessionSupport;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.HashMap;
import java.util.Map;

/** 报告查询实现。 */
@Service
public class InterviewReportQueryServiceImpl implements InterviewReportQueryService {

    private final InterviewReportMapper reportMapper;
    private final InterviewSessionSupport sessionSupport;
    private final ObjectMapper objectMapper;

    public InterviewReportQueryServiceImpl(
            InterviewReportMapper reportMapper,
            InterviewSessionSupport sessionSupport,
            ObjectMapper objectMapper
    ) {
        this.reportMapper = reportMapper;
        this.sessionSupport = sessionSupport;
        this.objectMapper = objectMapper;
    }

    @Override
    public Map<String, Object> getReport(String interviewSessionId, String studentId) {
        InterviewSessionEntity session = sessionSupport.requireSession(interviewSessionId, studentId);
        if (session.getReportId() == null || session.getReportId().isBlank()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "报告尚未生成");
        }
        InterviewReportEntity report = reportMapper.selectById(session.getReportId());
        if (report == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "报告不存在");
        }
        Map<String, Object> out = new HashMap<>();
        out.put("report_id", report.getReportId());
        try {
            out.put("payload", objectMapper.readValue(report.getPayloadJson(), Map.class));
        } catch (Exception e) {
            out.put("payload_raw", report.getPayloadJson());
        }
        return out;
    }
}
