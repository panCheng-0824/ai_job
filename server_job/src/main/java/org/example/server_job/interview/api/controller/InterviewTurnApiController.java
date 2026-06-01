package org.example.server_job.interview.api.controller;

import org.example.server_job.interview.dto.InterviewTurnRequest;
import org.example.server_job.interview.service.InterviewTurnService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 对外 API — 单轮答题 /turn（幂等 + 调 ai_job + MySQL 事务）。
 */
@RestController
@RequestMapping("/api/interview")
public class InterviewTurnApiController {

    private final InterviewTurnService turnService;

    public InterviewTurnApiController(InterviewTurnService turnService) {
        this.turnService = turnService;
    }

    @PostMapping("/{id}/turn")
    public ResponseEntity<Map<String, Object>> turn(
            @PathVariable("id") String interviewSessionId,
            @RequestBody InterviewTurnRequest body
    ) throws Exception {
        return ResponseEntity.ok(turnService.processTurn(interviewSessionId, body));
    }
}
