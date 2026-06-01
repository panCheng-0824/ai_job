package org.example.server_job.interview.api.controller;

import org.example.server_job.interview.service.InterviewReportQueryService;
import org.example.server_job.interview.service.InterviewSessionLifecycleService;
import org.example.server_job.interview.service.InterviewSessionQueryService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 对外 API — 会话查询与生命周期。
 */
@RestController
@RequestMapping("/api/interview")
public class InterviewSessionApiController {

    private final InterviewSessionQueryService sessionQueryService;
    private final InterviewSessionLifecycleService lifecycleService;
    private final InterviewReportQueryService reportQueryService;

    public InterviewSessionApiController(
            InterviewSessionQueryService sessionQueryService,
            InterviewSessionLifecycleService lifecycleService,
            InterviewReportQueryService reportQueryService
    ) {
        this.sessionQueryService = sessionQueryService;
        this.lifecycleService = lifecycleService;
        this.reportQueryService = reportQueryService;
    }

    @GetMapping("/sessions")
    public ResponseEntity<Map<String, Object>> listSessions(@RequestParam("student_id") String studentId) {
        return ResponseEntity.ok(sessionQueryService.listByStudent(studentId));
    }

    @PostMapping("/{id}/start")
    public ResponseEntity<Map<String, Object>> start(
            @PathVariable("id") String interviewSessionId,
            @RequestParam("student_id") String studentId
    ) {
        return ResponseEntity.ok(lifecycleService.start(interviewSessionId, studentId));
    }

    @GetMapping("/{id}/state")
    public ResponseEntity<Map<String, Object>> state(
            @PathVariable("id") String interviewSessionId,
            @RequestParam("student_id") String studentId
    ) {
        return ResponseEntity.ok(sessionQueryService.getState(interviewSessionId, studentId));
    }

    @PostMapping("/{id}/abandon")
    public ResponseEntity<Map<String, Object>> abandon(
            @PathVariable("id") String interviewSessionId,
            @RequestParam("student_id") String studentId
    ) {
        return ResponseEntity.ok(lifecycleService.abandon(interviewSessionId, studentId));
    }

    @GetMapping("/{id}/report")
    public ResponseEntity<Map<String, Object>> report(
            @PathVariable("id") String interviewSessionId,
            @RequestParam("student_id") String studentId
    ) {
        return ResponseEntity.ok(reportQueryService.getReport(interviewSessionId, studentId));
    }
}
