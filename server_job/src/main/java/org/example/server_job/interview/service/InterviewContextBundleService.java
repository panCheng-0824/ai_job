package org.example.server_job.interview.service;

import java.util.Map;

/** 供 ai_job 拉取完整上下文（internal API）。 */
public interface InterviewContextBundleService {

    Map<String, Object> build(String interviewSessionId);
}
