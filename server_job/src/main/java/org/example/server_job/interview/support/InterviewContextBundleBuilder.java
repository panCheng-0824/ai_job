package org.example.server_job.interview.support;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

/**
 * 组装 ai_job {@code /turn} 所需的 context_bundle JSON。
 */
@Component
public class InterviewContextBundleBuilder {

    private final InterviewSessionSupport sessionSupport;
    private final ObjectMapper objectMapper;

    public InterviewContextBundleBuilder(InterviewSessionSupport sessionSupport, ObjectMapper objectMapper) {
        this.sessionSupport = sessionSupport;
        this.objectMapper = objectMapper;
    }

    public ObjectNode buildNode(InterviewSessionEntity session) {
        try {
            ObjectNode root = objectMapper.createObjectNode();
            root.set("session", objectMapper.readTree(sessionSupport.sessionToJson(session)));
            String planJson = sessionSupport.loadPlanJson(session.getPlanId(), session.getPlanVersion());
            root.set("plan", objectMapper.readTree(planJson));
            root.set("student_profile", objectMapper.createObjectNode());
            return root;
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "组装 context-bundle 失败");
        }
    }

    public Map<String, Object> buildMap(InterviewSessionEntity session) {
        try {
            return objectMapper.convertValue(buildNode(session), Map.class);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "context-bundle 序列化失败");
        }
    }
}
