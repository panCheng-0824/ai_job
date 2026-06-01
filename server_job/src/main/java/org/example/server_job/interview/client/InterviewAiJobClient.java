package org.example.server_job.interview.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.client.AiJobGatewayService;
import org.example.server_job.ai.client.AiJobHttpResponse;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * 调用 ai_job ROLE005 内部接口（规划预览、同步 /turn）。
 */
@Component
public class InterviewAiJobClient {

    private static final Logger log = LogManager.getLogger(InterviewAiJobClient.class);

    private final AiJobGatewayService gateway;
    private final ObjectMapper objectMapper;

    public InterviewAiJobClient(AiJobGatewayService gateway, ObjectMapper objectMapper) {
        this.gateway = gateway;
        this.objectMapper = objectMapper;
    }

    /**
     * POST /api/internal/interview/plan/preview
     */
    public JsonNode planPreview(ObjectNode requestBody) throws IOException {
        String json = objectMapper.writeValueAsString(requestBody);
        AiJobHttpResponse resp = gateway.postJson("/api/internal/interview/plan/preview", json);
        return parseSuccessBody(resp, "plan/preview");
    }

    /**
     * POST /api/internal/interview/turn
     */
    public JsonNode interviewTurn(ObjectNode requestBody) throws IOException {
        String json = objectMapper.writeValueAsString(requestBody);
        AiJobHttpResponse resp = gateway.postJson("/api/internal/interview/turn", json);
        return parseSuccessBody(resp, "turn");
    }

    private JsonNode parseSuccessBody(AiJobHttpResponse resp, String label) throws IOException {
        String raw = resp.body() == null ? "" : new String(resp.body(), StandardCharsets.UTF_8);
        if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
            log.warn("ai_job {} 失败 status={} body={}", label, resp.statusCode(), truncate(raw));
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "ai_job " + label + " 失败: HTTP " + resp.statusCode()
            );
        }
        JsonNode root = objectMapper.readTree(raw.isBlank() ? "{}" : raw);
        if (root.has("success") && !root.path("success").asBoolean(true)) {
            String detail = root.path("detail").asText("未知错误");
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "ai_job " + label + ": " + detail);
        }
        return root;
    }

    private static String truncate(String s) {
        if (s == null || s.length() <= 500) {
            return s;
        }
        return s.substring(0, 500) + "…";
    }
}
