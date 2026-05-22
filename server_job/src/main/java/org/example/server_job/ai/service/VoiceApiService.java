package org.example.server_job.ai.service;

import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

public interface VoiceApiService {

    ResponseEntity<byte[]> transcribe(MultipartFile file, String modelLevel);

    ResponseEntity<byte[]> speech(String jsonBody);

    ResponseEntity<byte[]> spokenSummary(String jsonBody);

    ResponseEntity<StreamingResponseBody> speechStream(String jsonBody);

    ResponseEntity<StreamingResponseBody> spokenSummaryStream(String jsonBody);

    ResponseEntity<byte[]> spokenSummaryText(String jsonBody);
}
