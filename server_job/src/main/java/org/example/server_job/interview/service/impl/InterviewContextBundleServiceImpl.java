package org.example.server_job.interview.service.impl;

import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.service.InterviewContextBundleService;
import org.example.server_job.interview.support.InterviewContextBundleBuilder;
import org.example.server_job.interview.support.InterviewSessionSupport;
import org.springframework.stereotype.Service;

import java.util.Map;

/** internal context-bundle 实现。 */
@Service
public class InterviewContextBundleServiceImpl implements InterviewContextBundleService {

    private final InterviewSessionSupport sessionSupport;
    private final InterviewContextBundleBuilder bundleBuilder;

    public InterviewContextBundleServiceImpl(
            InterviewSessionSupport sessionSupport,
            InterviewContextBundleBuilder bundleBuilder
    ) {
        this.sessionSupport = sessionSupport;
        this.bundleBuilder = bundleBuilder;
    }

    @Override
    public Map<String, Object> build(String interviewSessionId) {
        InterviewSessionEntity session = sessionSupport.findSessionOrThrow(interviewSessionId);
        return bundleBuilder.buildMap(session);
    }
}
