package org.example.server_job.chat.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.chat.entity.ChatMessage;
import org.example.server_job.chat.entity.ChatSession;
import org.example.server_job.chat.mapper.ChatMessageMapper;
import org.example.server_job.chat.mapper.ChatSessionMapper;
import org.example.server_job.client.redis.RedisStringClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class ChatSessionApplicationService {

    private static final Logger log = LogManager.getLogger(ChatSessionApplicationService.class);

    private final ChatSessionMapper sessionMapper;
    private final ChatMessageMapper messageMapper;
    private final RedisStringClient redis;
    private final ObjectMapper objectMapper;
    private final BizStudentInfoService bizStudentInfoService;
    private final AiUserModelCatalogService userModelCatalogService;

    @Value("${chat.session.cache-key-prefix:chat:session:}")
    private String sessionCacheKeyPrefix;

    @Value("${chat.session.cache-ttl-hours:24}")
    private long cacheTtlHours;

    public ChatSessionApplicationService(
            ChatSessionMapper sessionMapper,
            ChatMessageMapper messageMapper,
            RedisStringClient redis,
            ObjectMapper objectMapper,
            BizStudentInfoService bizStudentInfoService,
            AiUserModelCatalogService userModelCatalogService
    ) {
        this.sessionMapper = sessionMapper;
        this.messageMapper = messageMapper;
        this.redis = redis;
        this.objectMapper = objectMapper;
        this.bizStudentInfoService = bizStudentInfoService;
        this.userModelCatalogService = userModelCatalogService;
    }

    public List<Map<String, Object>> listSessionsDocument(String studentId) throws IOException {
        String sid = studentId == null ? "" : studentId.trim();
        if (sid.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "student_id 不能为空");
        }
        List<ChatSession> rows = sessionMapper.selectList(
                new LambdaQueryWrapper<ChatSession>()
                        .eq(ChatSession::getStudentId, sid)
                        .orderByDesc(ChatSession::getUpdatedAt));
        if (rows.isEmpty()) {
            return List.of();
        }
        List<String> ids = rows.stream().map(ChatSession::getSessionId).toList();
        List<ChatMessage> msgs = messageMapper.selectList(
                new LambdaQueryWrapper<ChatMessage>()
                        .in(ChatMessage::getSessionId, ids)
                        .orderByAsc(ChatMessage::getSessionId)
                        .orderByAsc(ChatMessage::getSeqNo));
        Map<String, List<Map<String, Object>>> bySession = new LinkedHashMap<>();
        for (String id : ids) {
            bySession.put(id, new ArrayList<>());
        }
        for (ChatMessage msg : msgs) {
            bySession.computeIfAbsent(msg.getSessionId(), k -> new ArrayList<>()).add(messageToMap(msg));
        }
        List<Map<String, Object>> out = new ArrayList<>();
        for (ChatSession row : rows) {
            out.add(toSessionDocument(row, bySession.getOrDefault(row.getSessionId(), List.of())));
        }
        return out;
    }

    public Map<String, Object> getSessionDocument(String sessionId) throws IOException {
        String sid = normalizeSessionId(sessionId);
        String cacheKey = sessionCacheKeyPrefix + sid;
        String cached = redis.get(cacheKey);
        if (cached != null && !cached.isEmpty()) {
            return objectMapper.readValue(cached, new TypeReference<>() {
            });
        }
        ChatSession row = sessionMapper.selectById(sid);
        if (row == null) {
            return null;
        }
        List<Map<String, Object>> history = loadHistoryMaps(sid);
        Map<String, Object> doc = toSessionDocument(row, history);
        redis.set(cacheKey, objectMapper.writeValueAsString(doc),
                Duration.ofHours(Math.max(1, cacheTtlHours)));
        return doc;
    }

    public Map<String, Object> getHistoryDocument(String sessionId) throws IOException {
        String sid = normalizeSessionId(sessionId);
        ChatSession row = sessionMapper.selectById(sid);
        if (row == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会话不存在");
        }
        List<Map<String, Object>> history = loadHistoryMaps(sid);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("session_id", sid);
        out.put("history", history);
        return out;
    }

    @Transactional
    public Map<String, Object> initSession(String body) throws IOException {
        JsonNode root = objectMapper.readTree(body == null ? "{}" : body);
        String sessionId = root.path("session_id").asText("").trim();
        String studentId = root.path("student_id").asText("").trim();
        String usercode = root.path("usercode").asText("").trim();
        if (sessionId.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "session_id 不能为空");
        }
        if (studentId.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "student_id 不能为空");
        }
        if (usercode.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "usercode 不能为空");
        }

        validateStudentExists(studentId);
        JsonNode model = userModelCatalogService.findByUsercode(usercode)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "user_model 不存在"));

        ChatSession existing = sessionMapper.selectById(sessionId);
        if (existing != null) {
            Map<String, Object> doc = getSessionDocument(sessionId);
            if (doc == null) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会话不存在");
            }
            Map<String, Object> wrap = new LinkedHashMap<>();
            wrap.put("created", false);
            wrap.put("session", doc);
            wrap.put("message", "已存在会话，返回历史记录");
            return wrap;
        }

        Instant now = Instant.now();
        ChatSession row = new ChatSession();
        row.setSessionId(sessionId);
        row.setStudentId(studentId);
        row.setUsercode(usercode);
        row.setUsername(model.path("username").asText(""));
        row.setRoleName(model.path("role_name").asText(""));
        row.setModelLevel(model.path("model_level").asText(""));
        row.setCreatedAt(now);
        row.setUpdatedAt(now);
        sessionMapper.insert(row);

        Map<String, Object> doc = toSessionDocument(row, List.of());
        redis.set(sessionCacheKeyPrefix + sessionId, objectMapper.writeValueAsString(doc),
                Duration.ofHours(Math.max(1, cacheTtlHours)));

        Map<String, Object> wrap = new LinkedHashMap<>();
        wrap.put("created", true);
        wrap.put("session", doc);
        wrap.put("message", "会话不存在，已创建新会话");
        return wrap;
    }

    @Transactional
    public void deleteSession(String sessionId) {
        String sid = normalizeSessionId(sessionId);
        ChatSession row = sessionMapper.selectById(sid);
        if (row == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会话不存在");
        }
        messageMapper.delete(new LambdaQueryWrapper<ChatMessage>().eq(ChatMessage::getSessionId, sid));
        sessionMapper.deleteById(sid);
        redis.delete(sessionCacheKeyPrefix + sid);
    }

    public Map<String, Object> generateSessionId(String studentId) {
        validateStudentExists(studentId);
        String sid = studentId.trim();
        int n = 100_000 + ThreadLocalRandom.current().nextInt(900_000);
        return Map.of("session_id", sid + "-" + n);
    }

    public ChatInferenceSnapshot requireInferenceSnapshot(String sessionId) throws IOException {
        String sid = normalizeSessionId(sessionId);
        ChatSession row = sessionMapper.selectById(sid);
        if (row == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会话不存在，请先初始化会话");
        }
        List<Map<String, Object>> history = loadHistoryMaps(sid);
        String stud = row.getStudentId() == null ? "" : row.getStudentId().trim();
        return new ChatInferenceSnapshot(stud, row.getUsercode(), history);
    }

    /**
     * 当 SSE {@code done} 到达后，用完整 history 覆盖本地消息表并刷新缓存。
     */
    @Transactional
    public void persistDoneJson(String sessionId, String doneDataJson) throws IOException {
        JsonNode root = objectMapper.readTree(doneDataJson);
        JsonNode hist = root.get("history");
        if (hist == null || !hist.isArray()) {
            log.warn("done 事件缺少 history, sessionId={}", sessionId);
            return;
        }
        replaceHistoryFromMaps(sessionId, historyTurnsFromJson(hist));
        Map<String, Object> doc = reloadSessionDocumentNoCache(sessionId);
        if (doc != null) {
            redis.set(sessionCacheKeyPrefix + sessionId, objectMapper.writeValueAsString(doc),
                    Duration.ofHours(Math.max(1, cacheTtlHours)));
        }
    }

    /**
     * 非流式推理完成后，根据 ai_job 响应中的 history 覆盖本地。
     */
    @Transactional
    public void persistCompleteResponseHistory(String sessionId, byte[] responseBody) throws IOException {
        if (responseBody == null || responseBody.length == 0) {
            return;
        }
        JsonNode root = objectMapper.readTree(responseBody);
        JsonNode hist = root.get("history");
        if (hist == null || !hist.isArray()) {
            return;
        }
        replaceHistoryFromMaps(sessionId, historyTurnsFromJson(hist));
        Map<String, Object> doc = reloadSessionDocumentNoCache(sessionId);
        if (doc != null) {
            redis.set(sessionCacheKeyPrefix + sessionId, objectMapper.writeValueAsString(doc),
                    Duration.ofHours(Math.max(1, cacheTtlHours)));
        }
    }

    private List<Map<String, Object>> historyTurnsFromJson(JsonNode hist) {
        List<Map<String, Object>> list = new ArrayList<>();
        for (JsonNode n : hist) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("role", n.path("role").asText(""));
            m.put("content", n.path("content").asText(""));
            m.put("ts", n.path("ts").asText(""));
            JsonNode cards = n.get("context_cards");
            if (cards != null && cards.isArray() && !cards.isEmpty()) {
                m.put("context_cards", objectMapper.convertValue(cards, new TypeReference<List<Map<String, Object>>>() {}));
            }
            if (n.hasNonNull("message_context")) {
                String mc = n.path("message_context").asText("");
                if (!mc.isBlank()) {
                    m.put("message_context", mc);
                }
            }
            JsonNode jr = n.get("job_recommend");
            if (jr != null && jr.isObject() && !jr.isEmpty()) {
                m.put("job_recommend", objectMapper.convertValue(jr, new TypeReference<Map<String, Object>>() {}));
            }
            list.add(m);
        }
        return list;
    }

    private Map<String, Object> reloadSessionDocumentNoCache(String sessionId) throws IOException {
        redis.delete(sessionCacheKeyPrefix + sessionId);
        ChatSession row = sessionMapper.selectById(sessionId);
        if (row == null) {
            return null;
        }
        List<Map<String, Object>> history = loadHistoryMaps(sessionId);
        return toSessionDocument(row, history);
    }

    private void replaceHistoryFromMaps(String sessionId, List<Map<String, Object>> history) {
        String sid = normalizeSessionId(sessionId);
        ChatSession row = sessionMapper.selectById(sid);
        if (row == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会话不存在");
        }
        messageMapper.delete(new LambdaQueryWrapper<ChatMessage>().eq(ChatMessage::getSessionId, sid));
        int seq = 0;
        for (Map<String, Object> turn : history) {
            ChatMessage m = new ChatMessage();
            m.setSessionId(sid);
            m.setRole(String.valueOf(turn.getOrDefault("role", "")));
            m.setContent(Objects.toString(turn.get("content"), ""));
            m.setExtraJson(serializeTurnExtraJson(turn));
            m.setMsgTs(Objects.toString(turn.get("ts"), ""));
            m.setSeqNo(seq++);
            messageMapper.insert(m);
        }
        row.setUpdatedAt(Instant.now());
        sessionMapper.updateById(row);
        redis.delete(sessionCacheKeyPrefix + sid);
    }

    private List<Map<String, Object>> loadHistoryMaps(String sessionId) {
        List<ChatMessage> msgs = messageMapper.selectList(
                new LambdaQueryWrapper<ChatMessage>()
                        .eq(ChatMessage::getSessionId, sessionId)
                        .orderByAsc(ChatMessage::getSeqNo));
        List<Map<String, Object>> out = new ArrayList<>();
        for (ChatMessage msg : msgs) {
            out.add(messageToMap(msg));
        }
        return out;
    }

    private Map<String, Object> messageToMap(ChatMessage msg) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("role", msg.getRole());
        m.put("content", msg.getContent() == null ? "" : msg.getContent());
        m.put("ts", msg.getMsgTs() == null ? "" : msg.getMsgTs());
        mergeExtraJsonIntoTurnMap(m, msg.getExtraJson());
        return m;
    }

    private String serializeTurnExtraJson(Map<String, Object> turn) {
        Map<String, Object> extra = new LinkedHashMap<>();
        Object cards = turn.get("context_cards");
        if (cards instanceof List<?> list && !list.isEmpty()) {
            extra.put("context_cards", cards);
        }
        Object mc = turn.get("message_context");
        if (mc != null) {
            String s = String.valueOf(mc).trim();
            if (!s.isEmpty()) {
                extra.put("message_context", s);
            }
        }
        Object jr = turn.get("job_recommend");
        if (jr instanceof Map<?, ?> jrMap && !jrMap.isEmpty()) {
            extra.put("job_recommend", jrMap);
        }
        if (extra.isEmpty()) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(extra);
        } catch (Exception ex) {
            log.warn("序列化消息扩展字段失败: {}", ex.getMessage());
            return null;
        }
    }

    private void mergeExtraJsonIntoTurnMap(Map<String, Object> m, String extraJson) {
        if (extraJson == null || extraJson.isBlank()) {
            return;
        }
        try {
            Map<String, Object> extra = objectMapper.readValue(extraJson, new TypeReference<Map<String, Object>>() {});
            Object cards = extra.get("context_cards");
            if (cards instanceof List<?> list && !list.isEmpty()) {
                m.put("context_cards", list);
            }
            Object mc = extra.get("message_context");
            if (mc != null) {
                String s = String.valueOf(mc).trim();
                if (!s.isEmpty()) {
                    m.put("message_context", s);
                }
            }
            Object jr = extra.get("job_recommend");
            if (jr instanceof Map<?, ?> jrMap && !jrMap.isEmpty()) {
                m.put("job_recommend", jrMap);
            }
        } catch (Exception ex) {
            log.warn("解析消息扩展字段失败: {}", ex.getMessage());
        }
    }

    private Map<String, Object> toSessionDocument(ChatSession row, List<Map<String, Object>> history) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("session_id", row.getSessionId());
        m.put("student_id", row.getStudentId());
        m.put("usercode", row.getUsercode());
        m.put("username", row.getUsername());
        m.put("role_name", row.getRoleName());
        m.put("model_level", row.getModelLevel());
        m.put("created_at", formatInstant(row.getCreatedAt()));
        m.put("history", history);
        return m;
    }

    private String formatInstant(Instant ins) {
        if (ins == null) {
            return "";
        }
        return DateTimeFormatter.ISO_INSTANT.format(ins);
    }

    private void validateStudentExists(String studentId) {
        Integer xh = parseXh(studentId);
        BizStudentInfo student = bizStudentInfoService.getOne(
                new LambdaQueryWrapper<BizStudentInfo>().eq(BizStudentInfo::getXh, xh).last("limit 1"));
        if (student == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "student_id 不存在");
        }
    }

    private Integer parseXh(String studentId) {
        String cleaned = studentId == null ? "" : studentId.trim();
        if (cleaned.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "student_id 不能为空");
        }
        try {
            return Integer.valueOf(cleaned);
        } catch (NumberFormatException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "student_id 必须为数字学号");
        }
    }

    private static String normalizeSessionId(String sessionId) {
        String s = sessionId == null ? "" : sessionId.trim();
        if (s.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "session_id 不能为空");
        }
        return s;
    }

    public record ChatInferenceSnapshot(String studentId, String usercode, List<Map<String, Object>> history) {
    }
}
