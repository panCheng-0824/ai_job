package org.example.server_job.interview.mq;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;

/**
 * 写入 {@code interview_mq_consume_log} 做消费幂等（表不存在时仅打日志）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class InterviewMqConsumeLogService {

    private final JdbcTemplate jdbcTemplate;
    private final InterviewMqProperties mqProperties;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public void recordIfNew(String rawJson) {
        if (rawJson == null || rawJson.isBlank()) {
            return;
        }
        String messageId = extractField(rawJson, "message_id");
        if (messageId.isBlank()) {
            messageId = sha256Hex(rawJson);
        }
        String idempotencyKey = extractField(rawJson, "idempotency_key");
        String eventType = extractField(rawJson, "event_type");
        String digest = sha256Hex(rawJson);
        String group = mqProperties.getConsumerGroups().getAiResult();

        try {
            int rows = jdbcTemplate.update(
                    """
                    INSERT INTO interview_mq_consume_log
                      (message_id, idempotency_key, event_type, consumer_group, payload_digest)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    messageId,
                    idempotencyKey,
                    eventType,
                    group,
                    digest
            );
            if (rows > 0) {
                log.debug("MQ 消费已登记 message_id={} event={}", messageId, eventType);
            }
        } catch (Exception ex) {
            if (isDuplicate(ex)) {
                log.debug("MQ 重复消息已忽略 message_id={}", messageId);
                return;
            }
            log.warn("MQ 消费登记失败（可能未建表）: {}", ex.getMessage());
        }
    }

    private String extractField(String json, String field) {
        try {
            JsonNode node = objectMapper.readTree(json);
            JsonNode v = node.get(field);
            return v == null || v.isNull() ? "" : v.asText("");
        } catch (Exception e) {
            return "";
        }
    }

    private static boolean isDuplicate(Exception ex) {
        String msg = ex.getMessage() == null ? "" : ex.getMessage().toLowerCase();
        return msg.contains("duplicate") || msg.contains("uk_message_id");
    }

    private static String sha256Hex(String text) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(text.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (Exception e) {
            return "";
        }
    }
}
