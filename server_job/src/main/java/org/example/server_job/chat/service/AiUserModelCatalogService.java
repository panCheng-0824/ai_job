package org.example.server_job.chat.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.ai.client.AiJobGatewayService;
import org.example.server_job.ai.client.AiJobHttpResponse;
import org.example.server_job.client.redis.RedisStringClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Optional;

@Service
public class AiUserModelCatalogService {

    private final AiJobGatewayService gateway;
    private final RedisStringClient redis;
    private final ObjectMapper objectMapper;

    @Value("${chat.usermodels.cache-key:chat:usermodels:snapshot}")
    private String cacheKey;

    @Value("${chat.usermodels.cache-ttl-minutes:5}")
    private long cacheTtlMinutes;

    public AiUserModelCatalogService(
            AiJobGatewayService gateway,
            RedisStringClient redis,
            ObjectMapper objectMapper
    ) {
        this.gateway = gateway;
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

    public JsonNode userModelsArray() throws IOException {
        String cached = redis.get(cacheKey);
        if (cached != null && !cached.isEmpty()) {
            return objectMapper.readTree(cached);
        }
        AiJobHttpResponse r = gateway.get("/user-models", java.util.Map.of());
        if (r.statusCode() < 200 || r.statusCode() >= 300) {
            throw new IOException("ai_job /user-models 失败 status=" + r.statusCode());
        }
        String body = new String(r.body(), StandardCharsets.UTF_8);
        redis.set(cacheKey, body, Duration.ofMinutes(Math.max(1, cacheTtlMinutes)));
        return objectMapper.readTree(body);
    }

    public Optional<JsonNode> findByUsercode(String usercode) throws IOException {
        String uc = usercode == null ? "" : usercode.trim();
        if (uc.isEmpty()) {
            return Optional.empty();
        }
        JsonNode arr = userModelsArray();
        if (!arr.isArray()) {
            return Optional.empty();
        }
        for (JsonNode n : arr) {
            if (uc.equals(n.path("usercode").asText())) {
                return Optional.of(n);
            }
        }
        return Optional.empty();
    }
}
