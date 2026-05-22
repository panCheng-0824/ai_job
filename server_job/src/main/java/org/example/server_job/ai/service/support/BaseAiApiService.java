package org.example.server_job.ai.service.support;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.nio.charset.StandardCharsets;

public abstract class BaseAiApiService {

    private static final Logger log = LogManager.getLogger(BaseAiApiService.class);

    @FunctionalInterface
    protected interface ThrowingSupplier<T> {
        T get() throws Exception;
    }

    protected ResponseEntity<byte[]> guard(ThrowingSupplier<ResponseEntity<byte[]>> action) {
        try {
            return action.get();
        } catch (Exception ex) {
            log.error("调用 ai_job 失败, reason={}", ex.getMessage(), ex);
            String body = "{\"detail\":\"调用 ai_job 失败: " + safeMessage(ex.getMessage()) + "\"}";
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(body.getBytes(StandardCharsets.UTF_8));
        }
    }

    private String safeMessage(String message) {
        if (message == null) {
            return "unknown";
        }
        return message.replace("\"", "'");
    }
}
