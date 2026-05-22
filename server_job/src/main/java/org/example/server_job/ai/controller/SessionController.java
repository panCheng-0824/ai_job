package org.example.server_job.ai.controller;

import org.example.server_job.ai.service.ChatApiService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class SessionController {

    private final ChatApiService chatApiService;

    public SessionController(ChatApiService chatApiService) {
        this.chatApiService = chatApiService;
    }

    @GetMapping("/session-id")
    public ResponseEntity<byte[]> generateSessionId(@RequestParam("student_id") String studentId) {
        return chatApiService.generateSessionId(studentId);
    }
}
