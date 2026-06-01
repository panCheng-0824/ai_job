package org.example.server_job.interview.api.controller;

import com.fasterxml.jackson.databind.JsonNode;
import org.example.server_job.interview.dto.InterviewPlanConfirmRequest;
import org.example.server_job.interview.dto.InterviewPlanPreviewRequest;
import org.example.server_job.interview.dto.InterviewPlanStartRequest;
import org.example.server_job.interview.service.InterviewPlanService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 对外 API — 规划阶段（web_job 调用）。
 *
 * <p>仅做路由注册，业务在 {@link InterviewPlanService}。
 */
@RestController
@RequestMapping("/api/interview/plan")
public class InterviewPlanApiController {

    private final InterviewPlanService planService;

    public InterviewPlanApiController(InterviewPlanService planService) {
        this.planService = planService;
    }

    @PostMapping("/preview")
    public ResponseEntity<JsonNode> preview(@RequestBody InterviewPlanPreviewRequest body) throws Exception {
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .body(planService.preview(body));
    }

    @PostMapping("/confirm")
    public ResponseEntity<Map<String, Object>> confirm(@RequestBody InterviewPlanConfirmRequest body)
            throws Exception {
        return ResponseEntity.ok(planService.confirm(body));
    }

    /**
     * 学生确认大纲后：按 plan_id 创建面试会话与「我的面试记录」行（大纲须已 MQ 入库）。
     */
    @PostMapping("/start")
    public ResponseEntity<Map<String, Object>> start(@RequestBody InterviewPlanStartRequest body) {
        return ResponseEntity.ok(planService.start(body));
    }
}
