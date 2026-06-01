package org.example.server_job.interview.service;

import java.util.Map;

/** 面试报告只读查询。 */
public interface InterviewReportQueryService {

    Map<String, Object> getReport(String interviewSessionId, String studentId);
}
