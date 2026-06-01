package org.example.server_job.interview.mq;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.server_job.interview.support.InterviewPlanBankWriteSupport;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 消费 {@code interview.plan.result}，将 AI 生成的大纲写入 V2 关系表（含行业分类）。
 *
 * <p>与 {@code InterviewPlanServiceImpl#confirm} 区分：本路径仅维护题库，不创建 interview_session。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class InterviewPlanBankPersistService {

    private static final String EVENT_PLAN_RESULT = "interview.plan.result";

    private final InterviewPlanBankWriteSupport bankWriteSupport;
    private final ObjectMapper objectMapper;

    /**
     * 解析 MQ 信封 JSON；命中 {@link #EVENT_PLAN_RESULT} 且 status=ok 时落库。
     *
     * @return 是否已处理（含幂等跳过）
     */
    @Transactional
    public boolean tryPersistFromEnvelopeJson(String rawJson) {
        if (rawJson == null || rawJson.isBlank()) {
            return false;
        }
        try {
            JsonNode root = objectMapper.readTree(rawJson);
            String eventType = text(root, "event_type");
            if (!EVENT_PLAN_RESULT.equals(eventType)) {
                return false;
            }
            JsonNode payload = root.path("payload");
            if (!payload.isObject()) {
                log.warn("interview.plan.result 缺少 payload");
                return false;
            }
            String status = text(payload, "status");
            if (!"ok".equalsIgnoreCase(status)) {
                log.info("跳过非 ok 的 plan.result status={}", status);
                return false;
            }

            JsonNode planNode = payload.path("plan");
            String planId = planNode.path("plan_id").asText("");
            int version = planNode.path("version").asInt(1);

            boolean persisted = bankWriteSupport.insertFromMqPayload(payload);
            if (!persisted) {
                log.warn("interview.plan.result 缺少有效 plan，未落库");
                return false;
            }

            log.info(
                    "大纲题库已入库(V2) plan_id={} version={} industry_category_id={} student_id={}",
                    planId,
                    version,
                    resolveIndustryCategoryId(payload, planNode),
                    text(payload, "student_id")
            );
            return true;
        } catch (Exception ex) {
            log.error("interview.plan.result 落库失败: {}", ex.getMessage(), ex);
            return false;
        }
    }

    private static String resolveIndustryCategoryId(JsonNode payload, JsonNode planNode) {
        String fromPayload = text(payload, "industry_category_id");
        if (!fromPayload.isBlank()) {
            return fromPayload;
        }
        return planNode.path("industry_category_id").asText("");
    }

    private static String text(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return v == null || v.isNull() ? "" : v.asText("");
    }
}
