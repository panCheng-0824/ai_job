package org.example.server_job.interview.service;

import java.util.Map;

/** 会话只读查询：状态、历史列表。 */
public interface InterviewSessionQueryService {

    Map<String, Object> getState(String interviewSessionId, String studentId);

    Map<String, Object> listByStudent(String studentId);
}
