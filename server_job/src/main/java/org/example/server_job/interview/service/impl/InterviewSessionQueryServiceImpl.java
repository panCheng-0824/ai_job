package org.example.server_job.interview.service.impl;

import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.service.InterviewSessionQueryService;
import org.example.server_job.interview.service.StudentInterviewRecordService;
import org.example.server_job.interview.support.InterviewSessionSupport;
import org.springframework.stereotype.Service;

import java.util.Map;

/** 会话只读查询实现。 */
@Service
public class InterviewSessionQueryServiceImpl implements InterviewSessionQueryService {

    private final InterviewSessionSupport sessionSupport;
    private final StudentInterviewRecordService recordService;

    public InterviewSessionQueryServiceImpl(
            InterviewSessionSupport sessionSupport,
            StudentInterviewRecordService recordService
    ) {
        this.sessionSupport = sessionSupport;
        this.recordService = recordService;
    }

    @Override
    public Map<String, Object> getState(String interviewSessionId, String studentId) {
        InterviewSessionEntity session = sessionSupport.requireSession(interviewSessionId, studentId);
        return sessionSupport.sessionToMap(session);
    }

    @Override
    public Map<String, Object> listByStudent(String studentId) {
        // 与「我的面试记录」共用 V2 列表
        return recordService.listByStudent(studentId, null);
    }
}
