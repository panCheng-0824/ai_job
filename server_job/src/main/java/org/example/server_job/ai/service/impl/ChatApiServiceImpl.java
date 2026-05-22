package org.example.server_job.ai.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import okhttp3.Response;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.client.AiJobGatewayService;
import org.example.server_job.ai.client.AiJobHttpResponse;
import org.example.server_job.ai.service.ChatApiService;
import org.example.server_job.ai.support.AiResponseMapper;
import org.example.server_job.chat.service.ChatSessionApplicationService;
import org.example.server_job.chat.support.ChatSseRelay;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.async.AsyncRequestNotUsableException;
import org.springframework.web.context.request.async.AsyncRequestTimeoutException;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.InterruptedIOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

@Service
public class ChatApiServiceImpl implements ChatApiService {

    private static final Logger log = LogManager.getLogger(ChatApiServiceImpl.class);

    private final AiJobGatewayService gatewayService;
    private final AiResponseMapper responseMapper;
    private final ChatSessionApplicationService chatSessionService;
    private final ObjectMapper objectMapper;

    public ChatApiServiceImpl(
            AiJobGatewayService gatewayService,
            AiResponseMapper responseMapper,
            ChatSessionApplicationService chatSessionService,
            ObjectMapper objectMapper
    ) {
        this.gatewayService = gatewayService;
        this.responseMapper = responseMapper;
        this.chatSessionService = chatSessionService;
        this.objectMapper = objectMapper;
    }

    @Override
    public ResponseEntity<byte[]> listSessions(String studentId) {
        log.info("查询会话列表开始, studentId={}", studentId);
        try {
            List<Map<String, Object>> data = chatSessionService.listSessionsDocument(studentId);
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(objectMapper.writeValueAsBytes(data));
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("查询会话列表失败, studentId={}, reason={}", studentId, ex.getMessage(), ex);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(errorJsonBytes("读取会话列表失败: " + ex.getMessage()));
        }
    }

    @Override
    public ResponseEntity<byte[]> getSession(String sessionId) {
        log.info("查询会话详情开始, sessionId={}", sessionId);
        try {
            Map<String, Object> doc = chatSessionService.getSessionDocument(sessionId);
            if (doc == null) {
                return ResponseEntity.status(HttpStatus.NOT_FOUND).body(errorJsonBytes("会话不存在"));
            }
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(objectMapper.writeValueAsBytes(doc));
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("查询会话详情失败, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(errorJsonBytes("读取会话失败: " + ex.getMessage()));
        }
    }

    @Override
    public ResponseEntity<byte[]> getSessionHistory(String sessionId) {
        log.info("查询会话历史开始, sessionId={}", sessionId);
        try {
            Map<String, Object> doc = chatSessionService.getHistoryDocument(sessionId);
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(objectMapper.writeValueAsBytes(doc));
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("查询会话历史失败, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(errorJsonBytes("读取会话历史失败: " + ex.getMessage()));
        }
    }

    @Override
    public ResponseEntity<byte[]> initSession(String body) {
        log.info("初始化会话请求开始, bodyLength={}", body == null ? 0 : body.length());
        try {
            Map<String, Object> payload = chatSessionService.initSession(body);
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(objectMapper.writeValueAsBytes(payload));
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("初始化会话失败, reason={}", ex.getMessage(), ex);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(errorJsonBytes("初始化会话失败: " + ex.getMessage()));
        }
    }

    @Override
    public ResponseEntity<byte[]> deleteSession(String sessionId) {
        log.info("删除会话请求开始, sessionId={}", sessionId);
        try {
            chatSessionService.deleteSession(sessionId);
            Map<String, Object> payload = Map.of("deleted", true, "session_id", sessionId.trim());
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(objectMapper.writeValueAsBytes(payload));
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("删除会话失败, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(errorJsonBytes("删除会话失败: " + ex.getMessage()));
        }
    }

    @Override
    public ResponseEntity<byte[]> generateSessionId(String studentId) {
        log.info("生成会话ID请求开始, studentId={}", studentId);
        try {
            Map<String, Object> payload = chatSessionService.generateSessionId(studentId);
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(objectMapper.writeValueAsBytes(payload));
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("生成会话ID失败, studentId={}, reason={}", studentId, ex.getMessage(), ex);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(errorJsonBytes("生成会话ID失败: " + ex.getMessage()));
        }
    }

    @Override
    public ResponseEntity<byte[]> sendMessage(String sessionId, String body) {
        log.info("发送会话消息请求开始, sessionId={}, bodyLength={}", sessionId, body == null ? 0 : body.length());
        try {
            ChatSessionApplicationService.ChatInferenceSnapshot snap = chatSessionService.requireInferenceSnapshot(sessionId);
            JsonNode root = objectMapper.readTree(body == null ? "{}" : body);
            String message = root.path("message").asText("").trim();
            if (message.isEmpty()) {
                return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errorJsonBytes("message 不能为空"));
            }
            boolean useRolePipeline = root.path("use_role_pipeline").asBoolean(true);
            boolean useAdversarialHarness = root.path("use_adversarial_harness").asBoolean(false);
            String adversarialDesc = root.path("adversarial_desc").asText("");

            String messageContext = root.path("message_context").asText("").trim();
            JsonNode contextCards = root.get("context_cards");
            String upstreamBody = buildInternalChatPayload(
                    sessionId,
                    snap.studentId(),
                    snap.usercode(),
                    message,
                    messageContext,
                    contextCards,
                    snap.history(),
                    useRolePipeline,
                    useAdversarialHarness,
                    adversarialDesc
            );
            AiJobHttpResponse upstream = gatewayService.postJson("/internal/chat/complete", upstreamBody);
            if (upstream.statusCode() >= 200 && upstream.statusCode() < 300) {
                try {
                    chatSessionService.persistCompleteResponseHistory(sessionId, upstream.body());
                } catch (Exception ex) {
                    log.error("持久化非流式对话结果失败, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
                }
            }
            return responseMapper.toResponseEntity(upstream);
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("发送会话消息失败, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(errorJsonBytes("调用 ai_job 失败: " + ex.getMessage()));
        }
    }

    @Override
    public ResponseEntity<byte[]> stopStream(String sessionId) {
        log.info("停止流式会话请求开始, sessionId={}", sessionId);
        try {
            return responseMapper.toResponseEntity(
                    gatewayService.postJson("/chat-sessions/" + sessionId + "/messages/stop", "{}"));
        } catch (Exception ex) {
            log.error("停止流式会话失败, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(errorJsonBytes("调用 ai_job 失败: " + ex.getMessage()));
        }
    }

    @Override
    public ResponseEntity<StreamingResponseBody> streamMessagePost(String sessionId, String body) {
        log.info("启动流式会话 POST 请求, sessionId={}, bodyLength={}", sessionId, body == null ? 0 : body.length());
        try {
            JsonNode root = objectMapper.readTree(body == null || body.isBlank() ? "{}" : body);
            String display = root.path("message").asText("").trim();
            String hidden = root.path("message_context").asText("").trim();
            JsonNode cardsNode = root.get("context_cards");
            boolean hasCards = cardsNode != null && cardsNode.isArray() && !cardsNode.isEmpty();
            if (display.isEmpty() && hidden.isEmpty() && !hasCards) {
                return streamValidationError("message 不能为空");
            }
            boolean urp = !root.has("use_role_pipeline") || root.path("use_role_pipeline").asBoolean(true);
            boolean uah = root.path("use_adversarial_harness").asBoolean(false);
            String ad = root.path("adversarial_desc").asText("");
            ChatSessionApplicationService.ChatInferenceSnapshot snap =
                    chatSessionService.requireInferenceSnapshot(sessionId);
            String upstreamBody = buildInternalChatPayload(
                    sessionId,
                    snap.studentId(),
                    snap.usercode(),
                    display,
                    hidden,
                    cardsNode,
                    snap.history(),
                    urp,
                    uah,
                    ad
            );
            return relayInternalChatStream(sessionId, upstreamBody);
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("流式会话 POST 处理失败, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
            return streamGatewayError("调用 ai_job 流式接口失败");
        }
    }

    @Override
    public ResponseEntity<StreamingResponseBody> streamMessage(
            String sessionId,
            String message,
            Boolean useRolePipeline,
            Boolean useAdversarialHarness,
            String adversarialDesc
    ) {
        log.info("启动流式会话请求开始, sessionId={}, messageLength={}, useRolePipeline={}, useAdversarialHarness={}",
                sessionId,
                message == null ? 0 : message.length(),
                useRolePipeline,
                useAdversarialHarness);
        final String userMessage = message == null ? "" : message.trim();
        if (userMessage.isEmpty()) {
            return streamValidationError("message 不能为空");
        }

        try {
            ChatSessionApplicationService.ChatInferenceSnapshot snap = chatSessionService.requireInferenceSnapshot(sessionId);
            boolean urp = useRolePipeline == null || useRolePipeline;
            boolean uah = useAdversarialHarness != null && useAdversarialHarness;
            String ad = adversarialDesc == null ? "" : adversarialDesc;

            String upstreamBody = buildInternalChatPayload(
                    sessionId,
                    snap.studentId(),
                    snap.usercode(),
                    userMessage,
                    "",
                    null,
                    snap.history(),
                    urp,
                    uah,
                    ad
            );
            return relayInternalChatStream(sessionId, upstreamBody);
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("流式会话处理失败, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
            return streamGatewayError("调用 ai_job 流式接口失败");
        }
    }

    private ResponseEntity<StreamingResponseBody> relayInternalChatStream(String sessionId, String upstreamBody)
            throws Exception {
        Response upstream = gatewayService.streamPostJson("/internal/chat/stream", upstreamBody);
        if (!upstream.isSuccessful()) {
            try (Response u = upstream) {
                String detail = u.body() != null ? u.body().string() : "upstream error";
                StreamingResponseBody errBody = out -> {
                    String payload = objectMapper.writeValueAsString(Map.of("detail", detail));
                    String sse = "event: error\ndata: " + payload + "\n\n";
                    out.write(sse.getBytes(StandardCharsets.UTF_8));
                    out.flush();
                };
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.TEXT_EVENT_STREAM);
                return new ResponseEntity<>(errBody, headers, HttpStatus.BAD_GATEWAY);
            }
        }

        final Response streamResponse = upstream;
        StreamingResponseBody body = outputStream -> {
            try (Response u = streamResponse; InputStream in = u.body() == null ? InputStream.nullInputStream() : u.body().byteStream()) {
                ChatSseRelay.relay(in, outputStream, doneJson -> {
                    try {
                        chatSessionService.persistDoneJson(sessionId, doneJson);
                    } catch (Exception ex) {
                        log.error("持久化流式对话结果失败, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
                    }
                });
                outputStream.flush();
            } catch (Exception ex) {
                if (isBenignSseClientDisconnect(ex)) {
                    log.debug("流式转发被客户端关闭或响应已结束(与语音播报无关), sessionId={}", sessionId);
                } else {
                    log.error("流式转发异常, sessionId={}, reason={}", sessionId, ex.getMessage(), ex);
                    throw ex;
                }
            }
        };
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.TEXT_EVENT_STREAM);
        return new ResponseEntity<>(body, headers, HttpStatus.valueOf(streamResponse.code()));
    }

    private ResponseEntity<StreamingResponseBody> streamValidationError(String detail) {
        StreamingResponseBody errBody = out -> {
            String sse = "event: error\ndata: {\"detail\":\"" + detail.replace("\"", "'") + "\"}\n\n";
            out.write(sse.getBytes(StandardCharsets.UTF_8));
            out.flush();
        };
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.TEXT_EVENT_STREAM);
        return new ResponseEntity<>(errBody, headers, HttpStatus.BAD_REQUEST);
    }

    private ResponseEntity<StreamingResponseBody> streamGatewayError(String detail) {
        StreamingResponseBody errBody = out -> {
            String payload = "{\"detail\":\"" + detail.replace("\"", "'") + "\"}";
            String sse = "event: error\ndata: " + payload + "\n\n";
            out.write(sse.getBytes(StandardCharsets.UTF_8));
            out.flush();
        };
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.TEXT_EVENT_STREAM);
        return new ResponseEntity<>(errBody, headers, HttpStatus.BAD_GATEWAY);
    }

    private String buildInternalChatPayload(
            String sessionId,
            String studentId,
            String usercode,
            String message,
            String messageContext,
            JsonNode contextCards,
            List<Map<String, Object>> history,
            boolean useRolePipeline,
            boolean useAdversarialHarness,
            String adversarialDesc
    ) throws Exception {
        ObjectNode node = objectMapper.createObjectNode();
        node.put("session_id", sessionId.trim());
        node.put("student_id", studentId == null ? "" : studentId.trim());
        node.put("usercode", usercode);
        node.put("message", message);
        if (messageContext != null && !messageContext.isBlank()) {
            node.put("message_context", messageContext);
        }
        if (contextCards != null && contextCards.isArray() && !contextCards.isEmpty()) {
            node.set("context_cards", contextCards);
        }
        ArrayNode hist = objectMapper.createArrayNode();
        for (Map<String, Object> turn : history) {
            ObjectNode t = objectMapper.createObjectNode();
            t.put("role", String.valueOf(turn.getOrDefault("role", "")));
            t.put("content", String.valueOf(turn.getOrDefault("content", "")));
            t.put("ts", String.valueOf(turn.getOrDefault("ts", "")));
            Object cards = turn.get("context_cards");
            if (cards instanceof List<?> list && !list.isEmpty()) {
                t.set("context_cards", objectMapper.valueToTree(list));
            }
            Object mc = turn.get("message_context");
            if (mc != null) {
                String s = String.valueOf(mc).trim();
                if (!s.isEmpty()) {
                    t.put("message_context", s);
                }
            }
            Object jr = turn.get("job_recommend");
            if (jr instanceof Map<?, ?> jrMap && !jrMap.isEmpty()) {
                t.set("job_recommend", objectMapper.valueToTree(jrMap));
            }
            hist.add(t);
        }
        node.set("history", hist);
        node.put("use_role_pipeline", useRolePipeline);
        node.put("use_adversarial_harness", useAdversarialHarness);
        node.put("adversarial_desc", adversarialDesc == null ? "" : adversarialDesc);
        return objectMapper.writeValueAsString(node);
    }

    /**
     * 浏览器关闭 EventSource、刷新页面、主动 stop、异步超时/完成后仍写响应、异步取消导致上游读阻塞被中断等常见，不应按业务错误打 ERROR。
     */
    private static boolean isBenignSseClientDisconnect(Throwable ex) {
        for (Throwable t = ex; t != null; t = t.getCause()) {
            if (t instanceof AsyncRequestNotUsableException) {
                return true;
            }
            if (t instanceof AsyncRequestTimeoutException) {
                return true;
            }
            if (t instanceof InterruptedIOException) {
                return true;
            }
            String name = t.getClass().getName();
            if (name.contains("ClientAbortException") || name.contains("EofException")) {
                return true;
            }
        }
        return false;
    }

    private byte[] errorJsonBytes(String detail) {
        try {
            return objectMapper.writeValueAsBytes(Map.of("detail", detail));
        } catch (Exception ex) {
            return ("{\"detail\":\"" + detail.replace("\"", "'") + "\"}").getBytes(StandardCharsets.UTF_8);
        }
    }
}
