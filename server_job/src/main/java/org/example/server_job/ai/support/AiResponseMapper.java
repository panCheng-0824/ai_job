package org.example.server_job.ai.support;

import org.example.server_job.ai.client.AiJobHttpResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class AiResponseMapper {

    public ResponseEntity<byte[]> toResponseEntity(AiJobHttpResponse upstream) {
        HttpHeaders headers = new HttpHeaders();
        upstream.headers().forEach((name, values) -> {
            if (skipHeader(name)) {
                return;
            }
            for (String value : values) {
                headers.add(name, value);
            }
        });
        return new ResponseEntity<>(upstream.body(), headers, HttpStatus.valueOf(upstream.statusCode()));
    }

    private boolean skipHeader(String header) {
        List<String> blocked = List.of(
                HttpHeaders.CONTENT_LENGTH,
                HttpHeaders.CONNECTION,
                HttpHeaders.HOST
        );
        return blocked.stream().anyMatch(h -> h.equalsIgnoreCase(header));
    }
}
