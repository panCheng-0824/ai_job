package org.example.server_job.ai.controller;

import org.example.server_job.ai.service.VoiceApiService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

@RestController
@RequestMapping("/api")
public class VoiceController {

    private final VoiceApiService voiceApiService;

    public VoiceController(VoiceApiService voiceApiService) {
        this.voiceApiService = voiceApiService;
    }

    @PostMapping("/voice/transcribe")
    public ResponseEntity<byte[]> transcribe(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "model_level", defaultValue = "mid") String modelLevel) {
        return voiceApiService.transcribe(file, modelLevel);
    }

    @PostMapping("/voice/speech")
    public ResponseEntity<byte[]> speech(@RequestBody String body) {
        return voiceApiService.speech(body);
    }

    @PostMapping("/voice/spoken-summary")
    public ResponseEntity<byte[]> spokenSummary(@RequestBody String body) {
        return voiceApiService.spokenSummary(body);
    }

    @PostMapping("/voice/speech/stream")
    public ResponseEntity<StreamingResponseBody> speechStream(@RequestBody String body) {
        return voiceApiService.speechStream(body);
    }

    @PostMapping("/voice/spoken-summary/stream")
    public ResponseEntity<StreamingResponseBody> spokenSummaryStream(@RequestBody String body) {
        return voiceApiService.spokenSummaryStream(body);
    }

    @PostMapping("/voice/spoken-summary/text")
    public ResponseEntity<byte[]> spokenSummaryText(@RequestBody String body) {
        return voiceApiService.spokenSummaryText(body);
    }
}
