package org.example.server_job.ai.controller;

import org.example.server_job.ai.service.AiSearchApiService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.request.async.WebAsyncTask;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.time.Duration;

/**
 * 智能网页采集 API：转发至 ai_job（同步 + NDJSON 流式，非 SSE）。
 */
@RestController
@RequestMapping("/api/ai-search")
public class AiSearchController {

    private final AiSearchApiService aiSearchApiService;
    private final Duration streamAsyncTimeout;

    public AiSearchController(
            AiSearchApiService aiSearchApiService,
            @Value("${ai-search.stream.async-request-timeout:10m}") Duration streamAsyncTimeout
    ) {
        this.aiSearchApiService = aiSearchApiService;
        this.streamAsyncTimeout = streamAsyncTimeout;
    }

    @PostMapping("/crawl")
    public ResponseEntity<byte[]> crawl(@RequestBody String body) {
        return aiSearchApiService.crawl(body);
    }

    /**
     * NDJSON chunked HTTP 流式采集：每行一个 JSON 事件（log / result / error）。
     */
    @PostMapping("/crawl/stream")
    public WebAsyncTask<ResponseEntity<StreamingResponseBody>> crawlStream(@RequestBody String body) {
        WebAsyncTask<ResponseEntity<StreamingResponseBody>> task =
                new WebAsyncTask<>(streamAsyncTimeout.toMillis(), () -> aiSearchApiService.crawlStream(body));
        task.onTimeout(() -> ResponseEntity.status(504).build());
        return task;
    }
}
