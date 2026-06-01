package org.example.server_job.interview.service;

import org.example.server_job.interview.dto.InterviewTurnRequest;

import java.util.Map;

/** 单轮答题：幂等、调 ai_job、事务落库。 */
public interface InterviewTurnService {

    Map<String, Object> processTurn(String interviewSessionId, InterviewTurnRequest request) throws Exception;
}
