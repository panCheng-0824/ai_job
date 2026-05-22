package org.example.server_job.ai.controller;

import org.example.server_job.ai.service.ChatApiService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.request.async.WebAsyncTask;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.time.Duration;

@RestController
@RequestMapping("/api/chat-sessions")
public class ChatController {

    private final ChatApiService chatApiService;
    private final long chatStreamAsyncTimeoutMs;

    public ChatController(
            ChatApiService chatApiService,
            @Value("${chat.stream.async-request-timeout:30m}") Duration chatStreamAsyncTimeout
    ) {
        this.chatApiService = chatApiService;
        this.chatStreamAsyncTimeoutMs = chatStreamAsyncTimeout.toMillis();
    }

    @GetMapping
    public ResponseEntity<byte[]> listSessions(@RequestParam("student_id") String studentId) {
        return chatApiService.listSessions(studentId);
    }

    @GetMapping("/{sessionId}")
    public ResponseEntity<byte[]> getSession(@PathVariable String sessionId) {
        return chatApiService.getSession(sessionId);
    }

    @GetMapping("/{sessionId}/history")
    public ResponseEntity<byte[]> getHistory(@PathVariable String sessionId) {
        return chatApiService.getSessionHistory(sessionId);
    }

    @PostMapping("/init")
    public ResponseEntity<byte[]> initSession(@RequestBody String body) {
        return chatApiService.initSession(body);
    }

    @DeleteMapping("/{sessionId}")
    public ResponseEntity<byte[]> deleteSession(@PathVariable String sessionId) {
        return chatApiService.deleteSession(sessionId);
    }

    @PostMapping("/{sessionId}/messages")
    public ResponseEntity<byte[]> sendMessage(@PathVariable String sessionId, @RequestBody String body) {
        return chatApiService.sendMessage(sessionId, body);
    }

    @PostMapping("/{sessionId}/messages/stop")
    public ResponseEntity<byte[]> stopStream(@PathVariable String sessionId) {
        return chatApiService.stopStream(sessionId);
    }

    @GetMapping("/{sessionId}/messages/stream")
    public WebAsyncTask<ResponseEntity<StreamingResponseBody>> streamMessage(
            @PathVariable String sessionId,
            @RequestParam String message,
            @RequestParam(name = "use_role_pipeline", defaultValue = "true") Boolean useRolePipeline,
            @RequestParam(name = "use_adversarial_harness", defaultValue = "false") Boolean useAdversarialHarness,
            @RequestParam(name = "adversarial_desc", defaultValue = "") String adversarialDesc
    ) {
        return new WebAsyncTask<>(chatStreamAsyncTimeoutMs, () ->
                chatApiService.streamMessage(
                        sessionId,
                        message,
                        useRolePipeline,
                        useAdversarialHarness,
                        adversarialDesc
                )
        );
    }

    /** 携带引用卡片/长上下文时用 POST，避免 GET 查询串过长。 */
    @PostMapping("/{sessionId}/messages/stream")
    public WebAsyncTask<ResponseEntity<StreamingResponseBody>> streamMessagePost(
            @PathVariable String sessionId,
            @RequestBody String body
    ) {
        return new WebAsyncTask<>(chatStreamAsyncTimeoutMs, () ->
                chatApiService.streamMessagePost(sessionId, body)
        );
    }
}
