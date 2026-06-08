package org.example.server_job.ai.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.Response;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.client.AiJobGatewayService;
import org.example.server_job.ai.service.AiSearchApiService;
import org.example.server_job.ai.service.support.BaseAiApiService;
import org.example.server_job.ai.support.AiResponseMapper;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * ai_search 中转：同步 JSON + NDJSON chunked HTTP 流式透传（非 SSE）。
 */
@Service
public class AiSearchApiServiceImpl extends BaseAiApiService implements AiSearchApiService {

    private static final Logger log = LogManager.getLogger(AiSearchApiServiceImpl.class);
    private static final String NDJSON_MEDIA = "application/x-ndjson; charset=utf-8";

    private final AiJobGatewayService gatewayService;
    private final AiResponseMapper responseMapper;
    private final ObjectMapper objectMapper;

    public AiSearchApiServiceImpl(
            AiJobGatewayService gatewayService,
            AiResponseMapper responseMapper,
            ObjectMapper objectMapper
    ) {
        this.gatewayService = gatewayService;
        this.responseMapper = responseMapper;
        this.objectMapper = objectMapper;
    }

    @Override
    public ResponseEntity<byte[]> crawl(String jsonBody) {
        log.info("智能采集同步请求开始, bodyLength={}", jsonBody == null ? 0 : jsonBody.length());
        return guard(() -> responseMapper.toResponseEntity(
                gatewayService.postJson("/ai-search/crawl", jsonBody == null ? "{}" : jsonBody)));
    }

    @Override
    public ResponseEntity<StreamingResponseBody> crawlStream(String jsonBody) {
        log.info("智能采集流式请求开始, bodyLength={}", jsonBody == null ? 0 : jsonBody.length());
        try {
            Response upstream = gatewayService.streamPostJson(
                    "/ai-search/crawl/stream",
                    jsonBody == null ? "{}" : jsonBody);
            return relayStreamingNdjson(upstream);
        } catch (IOException ex) {
            log.error("智能采集流式调用失败, reason={}", ex.getMessage(), ex);
            return streamingJsonError(HttpStatus.BAD_GATEWAY, "调用 ai_job 智能采集流式接口失败");
        }
    }

    /**
     * 透传 ai_job NDJSON 流：按字节块转发，保持 Content-Type 与 chunked 语义。
     */
    private ResponseEntity<StreamingResponseBody> relayStreamingNdjson(Response upstream) throws IOException {
        if (!upstream.isSuccessful()) {
            try (Response u = upstream) {
                String detail = u.body() != null ? u.body().string() : "upstream error";
                log.warn("智能采集流式上游失败, status={}, detail={}", u.code(), detail);
                return streamingJsonError(HttpStatus.BAD_GATEWAY, detail);
            }
        }

        final Response streamResp = upstream;
        HttpHeaders headers = new HttpHeaders();
        String ct = streamResp.header("Content-Type");
        if (ct != null && !ct.isBlank()) {
            headers.add(HttpHeaders.CONTENT_TYPE, ct);
        } else {
            headers.setContentType(org.springframework.http.MediaType.parseMediaType(NDJSON_MEDIA));
        }
        headers.set(HttpHeaders.CACHE_CONTROL, "no-cache");
        headers.set("X-Accel-Buffering", "no");

        StreamingResponseBody body = outputStream -> {
            try (Response u = streamResp;
                 InputStream in = u.body() == null ? InputStream.nullInputStream() : u.body().byteStream()) {
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) != -1) {
                    outputStream.write(buf, 0, n);
                    outputStream.flush();
                }
            }
        };
        return new ResponseEntity<>(body, headers, HttpStatus.valueOf(streamResp.code()));
    }

    private ResponseEntity<StreamingResponseBody> streamingJsonError(HttpStatus status, String message) {
        try {
            byte[] errBody = objectMapper.writeValueAsBytes(Map.of("detail", message == null ? "" : message));
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);
            StreamingResponseBody errStream = out -> {
                out.write(errBody);
                out.flush();
            };
            return new ResponseEntity<>(errStream, headers, status);
        } catch (Exception ex) {
            log.error("构造 JSON 错误流失败, reason={}", ex.getMessage(), ex);
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);
            StreamingResponseBody errStream = out -> {
                byte[] fallback = "{\"detail\":\"网关错误\"}".getBytes(StandardCharsets.UTF_8);
                out.write(fallback);
                out.flush();
            };
            return new ResponseEntity<>(errStream, headers, status);
        }
    }
}
