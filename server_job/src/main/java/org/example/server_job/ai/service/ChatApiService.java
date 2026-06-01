package org.example.server_job.ai.service;

import org.springframework.http.ResponseEntity;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

public interface ChatApiService {
    ResponseEntity<byte[]> listSessions(String studentId);

    ResponseEntity<byte[]> getSession(String sessionId);

    ResponseEntity<byte[]> getSessionHistory(String sessionId, String studentId);

    ResponseEntity<byte[]> initSession(String body);

    ResponseEntity<byte[]> deleteSession(String sessionId, String studentId);

    ResponseEntity<byte[]> generateSessionId(String studentId);

    ResponseEntity<byte[]> sendMessage(String sessionId, String body);

    ResponseEntity<byte[]> stopStream(String sessionId, String studentId);

    ResponseEntity<StreamingResponseBody> streamMessage(
            String sessionId,
            String studentId,
            String message,
            Boolean useRolePipeline,
            Boolean useAdversarialHarness,
            String adversarialDesc
    );

    ResponseEntity<StreamingResponseBody> streamMessagePost(String sessionId, String body);
}
