package org.example.server_job.interview.api.controller;

import org.example.server_job.interview.dto.InterviewPlanSaveRequest;
import org.example.server_job.interview.service.InterviewPlanManageService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 题目大纲管理 API：列表与详情（V2 关系表）。
 */
@RestController
@RequestMapping("/api/interview/plans")
public class InterviewPlanManageApiController {

    private final InterviewPlanManageService planManageService;

    public InterviewPlanManageApiController(InterviewPlanManageService planManageService) {
        this.planManageService = planManageService;
    }

    @GetMapping
    public Map<String, Object> list(
            @RequestParam("student_id") String studentId,
            @RequestParam(value = "status", required = false) String status,
            @RequestParam(value = "industry_category_id", required = false) String industryCategoryId
    ) {
        return planManageService.listByStudent(studentId, status, industryCategoryId);
    }

    @GetMapping("/{planId}")
    public Map<String, Object> detail(
            @PathVariable("planId") String planId,
            @RequestParam("student_id") String studentId,
            @RequestParam(value = "version", required = false) Integer version
    ) {
        return planManageService.getDetail(studentId, planId, version);
    }

    @PostMapping
    public Map<String, Object> create(
            @RequestParam(value = "student_id", required = false) String studentId,
            @RequestBody InterviewPlanSaveRequest body
    ) {
        return planManageService.create(body, studentId);
    }

    @PutMapping("/{planId}")
    public Map<String, Object> revise(
            @PathVariable("planId") String planId,
            @RequestParam(value = "student_id", required = false) String studentId,
            @RequestBody InterviewPlanSaveRequest body
    ) {
        return planManageService.revise(planId, body, studentId);
    }

    @DeleteMapping("/{planId}")
    public Map<String, Object> delete(
            @PathVariable("planId") String planId,
            @RequestParam("student_id") String studentId
    ) {
        return planManageService.delete(studentId, planId);
    }
}
