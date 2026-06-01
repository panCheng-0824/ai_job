package org.example.server_job.interview.support;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.client.redis.RedisStringClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * 删除面试记录时清理 Redis：整场 ctx、单题 qsess、会话锁/心跳/倒计时。
 */
@Component
public class InterviewContextRedisDeleteSupport {

    private static final Logger log = LoggerFactory.getLogger(InterviewContextRedisDeleteSupport.class);

    private final RedisStringClient redis;
    private final ObjectMapper objectMapper;

    public InterviewContextRedisDeleteSupport(RedisStringClient redis, ObjectMapper objectMapper) {
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

    /**
     * 删除与一条面试记录关联的全部 Redis 数据。
     *
     * @param studentId          学号
     * @param recordId           面试记录 ID
     * @param chatSessionId      门户聊天 session_id，可为空
     * @param interviewSessionId 面试会话 ID，可为空
     * @return 删除的 key 数量（含 pattern 批量删除）
     */
    public long deleteForRecord(
            String studentId,
            String recordId,
            String chatSessionId,
            String interviewSessionId
    ) {
        String sid = studentId == null ? "" : studentId.trim();
        String rid = recordId == null ? "" : recordId.trim();
        if (sid.isEmpty() || rid.isEmpty()) {
            return 0;
        }

        long deleted = 0;
        String ctxKey = InterviewRedisKeys.ctx(sid, rid);
        String ctxRaw = redis.get(ctxKey);
        String cs = resolveChatSessionId(chatSessionId, ctxRaw);

        for (String questionId : extractQuestionIds(ctxRaw)) {
            if (cs.isEmpty() || questionId.isEmpty()) {
                continue;
            }
            if (redis.delete(InterviewRedisKeys.questionSession(cs, sid, rid, questionId))) {
                deleted++;
            }
        }

        deleted += redis.deleteByPattern(InterviewRedisKeys.qsessPatternForRecord(sid, rid));
        if (redis.delete(ctxKey)) {
            deleted++;
        }

        String sessionId = interviewSessionId == null ? "" : interviewSessionId.trim();
        if (!sessionId.isEmpty()) {
            if (redis.delete(InterviewRedisKeys.lock(sessionId))) {
                deleted++;
            }
            if (redis.delete(InterviewRedisKeys.heartbeat(sessionId))) {
                deleted++;
            }
            deleted += redis.deleteByPattern(InterviewRedisKeys.timerPattern(sessionId));
        }

        log.info(
                "面试记录 Redis 已清理 student={} record={} session={} deletedKeys={}",
                sid,
                rid,
                sessionId,
                deleted
        );
        return deleted;
    }

    private String resolveChatSessionId(String fromRecord, String ctxRaw) {
        if (fromRecord != null && !fromRecord.isBlank()) {
            return fromRecord.trim();
        }
        if (ctxRaw == null || ctxRaw.isBlank()) {
            return "";
        }
        try {
            JsonNode root = objectMapper.readTree(ctxRaw);
            return root.path("chat_session_id").asText("").trim();
        } catch (JsonProcessingException e) {
            return "";
        }
    }

    /** 从 ctx JSON 的 questions[] 提取题目 id（去重） */
    private List<String> extractQuestionIds(String ctxRaw) {
        Set<String> ids = new LinkedHashSet<>();
        if (ctxRaw == null || ctxRaw.isBlank()) {
            return List.of();
        }
        try {
            JsonNode root = objectMapper.readTree(ctxRaw);
            JsonNode currentId = root.get("current_question_id");
            if (currentId != null && !currentId.asText("").isBlank()) {
                ids.add(currentId.asText("").trim());
            }
            JsonNode questions = root.get("questions");
            if (questions != null && questions.isArray()) {
                for (JsonNode q : questions) {
                    String id = q.path("id").asText("").trim();
                    if (id.isEmpty()) {
                        id = q.path("question_id").asText("").trim();
                    }
                    if (!id.isEmpty()) {
                        ids.add(id);
                    }
                }
            }
        } catch (JsonProcessingException e) {
            log.warn("解析 ctx 题目 id 失败，将仅依赖 pattern 删除 qsess: {}", e.getMessage());
        }
        return new ArrayList<>(ids);
    }
}
