package org.example.server_job.interview.service;

import java.util.Map;

/** 会话生命周期：开始、放弃。 */
public interface InterviewSessionLifecycleService {

    Map<String, Object> start(String interviewSessionId, String studentId);

    Map<String, Object> abandon(String interviewSessionId, String studentId);
}
