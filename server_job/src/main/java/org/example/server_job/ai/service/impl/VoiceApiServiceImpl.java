package org.example.server_job.ai.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import okhttp3.Response;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.client.AiJobGatewayService;
import org.example.server_job.ai.service.VoiceApiService;
import org.example.server_job.ai.service.support.BaseAiApiService;
import org.example.server_job.ai.support.AiResponseMapper;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;

@Service
public class VoiceApiServiceImpl extends BaseAiApiService implements VoiceApiService {

    private static final Logger log = LogManager.getLogger(VoiceApiServiceImpl.class);

    private final AiJobGatewayService gatewayService;
    private final AiResponseMapper responseMapper;
    private final ObjectMapper objectMapper;

    public VoiceApiServiceImpl(
            AiJobGatewayService gatewayService,
            AiResponseMapper responseMapper,
            ObjectMapper objectMapper
    ) {
        this.gatewayService = gatewayService;
        this.responseMapper = responseMapper;
        this.objectMapper = objectMapper;
    }

    @Override
    public ResponseEntity<byte[]> transcribe(MultipartFile file, String modelLevel) {
        log.info(
                "语音转写请求开始, filename={}, size={}, modelLevel={}",
                file == null ? "null" : file.getOriginalFilename(),
                file == null ? 0 : file.getSize(),
                modelLevel);
        return guard(() -> {
            if (file == null || file.isEmpty()) {
                throw new IllegalArgumentException("file 不能为空");
            }
            String filename = file.getOriginalFilename() == null ? "recording.webm" : file.getOriginalFilename();
            MediaType mediaType = MediaType.parse(
                    file.getContentType() == null ? "application/octet-stream" : file.getContentType());
            MultipartBody multipartBody = new MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart(
                            "file",
                            filename,
                            RequestBody.create(file.getBytes(), mediaType))
                    .addFormDataPart("model_level", modelLevel == null || modelLevel.isBlank() ? "mid" : modelLevel)
                    .build();
            return responseMapper.toResponseEntity(gatewayService.postMultipart("/voice/transcribe", multipartBody));
        });
    }

    @Override
    public ResponseEntity<byte[]> speech(String jsonBody) {
        log.info("TTS 请求开始, bodyLength={}", jsonBody == null ? 0 : jsonBody.length());
        return guard(() -> responseMapper.toResponseEntity(gatewayService.postJson("/voice/speech", jsonBody)));
    }

    @Override
    public ResponseEntity<byte[]> spokenSummary(String jsonBody) {
        log.info("spoken-summary 请求开始, bodyLength={}", jsonBody == null ? 0 : jsonBody.length());
        return guard(() -> responseMapper.toResponseEntity(gatewayService.postJson("/voice/spoken-summary", jsonBody)));
    }

    @Override
    public ResponseEntity<StreamingResponseBody> speechStream(String jsonBody) {
        log.info("TTS 流式请求开始, bodyLength={}", jsonBody == null ? 0 : jsonBody.length());
        try {
            Response upstream =
                    gatewayService.streamPostJson("/voice/speech/stream", jsonBody == null ? "{}" : jsonBody);
            return relayStreamingAudio(upstream, "TTS 流式");
        } catch (IOException ex) {
            log.error("TTS 流式调用失败, reason={}", ex.getMessage(), ex);
            return streamingJsonError(HttpStatus.BAD_GATEWAY, "调用 ai_job 流式 TTS 失败");
        }
    }

    @Override
    public ResponseEntity<StreamingResponseBody> spokenSummaryStream(String jsonBody) {
        log.info("spoken-summary 流式请求开始, bodyLength={}", jsonBody == null ? 0 : jsonBody.length());
        try {
            Response upstream =
                    gatewayService.streamPostJson("/voice/spoken-summary/stream", jsonBody == null ? "{}" : jsonBody);
            return relayStreamingAudio(upstream, "spoken-summary 流式");
        } catch (IOException ex) {
            log.error("spoken-summary 流式调用失败, reason={}", ex.getMessage(), ex);
            return streamingJsonError(HttpStatus.BAD_GATEWAY, "调用 ai_job 流式 spoken-summary 失败");
        }
    }

    @Override
    public ResponseEntity<byte[]> spokenSummaryText(String jsonBody) {
        log.info("spoken-summary/text 请求开始, bodyLength={}", jsonBody == null ? 0 : jsonBody.length());
        return guard(() -> responseMapper.toResponseEntity(
                gatewayService.postJson("/voice/spoken-summary/text", jsonBody)));
    }

    private ResponseEntity<StreamingResponseBody> relayStreamingAudio(Response upstream, String ctx) throws IOException {
        if (!upstream.isSuccessful()) {
            try (Response u = upstream) {
                String detail = u.body() != null ? u.body().string() : "upstream error";
                log.warn("{} 上游失败, status={}, detail={}", ctx, u.code(), detail);
                return streamingJsonError(HttpStatus.BAD_GATEWAY, detail);
            }
        }

        final Response streamResp = upstream;
        HttpHeaders headers = new HttpHeaders();
        String ct = streamResp.header("Content-Type");
        if (ct != null && !ct.isBlank()) {
            headers.add(HttpHeaders.CONTENT_TYPE, ct);
        } else {
            headers.setContentType(org.springframework.http.MediaType.parseMediaType("audio/mpeg"));
        }

        StreamingResponseBody body = outputStream -> {
            try (Response u = streamResp;
                 InputStream in = u.body() == null ? InputStream.nullInputStream() : u.body().byteStream()) {
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) != -1) {
                    outputStream.write(buf, 0, n);
                }
                outputStream.flush();
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
