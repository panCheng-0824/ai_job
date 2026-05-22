package org.example.server_job.ai.service;

import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;

public interface OcrApiService {
    ResponseEntity<byte[]> recognizeByPath(String body);

    ResponseEntity<byte[]> recognizeByUrl(String body);

    ResponseEntity<byte[]> recognizeUpload(MultipartFile file, String lang, Boolean useAngleCls);
}
