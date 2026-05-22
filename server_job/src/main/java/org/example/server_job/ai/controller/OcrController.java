package org.example.server_job.ai.controller;

import org.example.server_job.ai.service.OcrApiService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/ocr")
public class OcrController {

    private final OcrApiService ocrApiService;

    public OcrController(OcrApiService ocrApiService) {
        this.ocrApiService = ocrApiService;
    }

    @PostMapping("/recognize")
    public ResponseEntity<byte[]> recognize(@RequestBody String body) {
        return ocrApiService.recognizeByPath(body);
    }

    @PostMapping("/recognize-url")
    public ResponseEntity<byte[]> recognizeUrl(@RequestBody String body) {
        return ocrApiService.recognizeByUrl(body);
    }

    @PostMapping("/recognize-upload")
    public ResponseEntity<byte[]> recognizeUpload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "lang", defaultValue = "ch") String lang,
            @RequestParam(value = "use_angle_cls", defaultValue = "true") Boolean useAngleCls
    ) {
        return ocrApiService.recognizeUpload(file, lang, useAngleCls);
    }
}
