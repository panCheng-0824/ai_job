package org.example.server_job.ai.controller;

import org.example.server_job.interview.service.StudentInterviewRecordService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 学生「我的面试记录」API，路径风格与 {@link StudentResumeController} 一致。
 */
@RestController
@RequestMapping("/api/me/interview-records")
public class StudentInterviewRecordController {

    private final StudentInterviewRecordService recordService;

    public StudentInterviewRecordController(StudentInterviewRecordService recordService) {
        this.recordService = recordService;
    }

    @GetMapping
    public Map<String, Object> list(
            @RequestParam("student_id") String studentId,
            @RequestParam(value = "summary_status", required = false) String summaryStatus
    ) {
        return recordService.listByStudent(studentId, summaryStatus);
    }

    /**
     * 聊天气泡「开始/进入」：按 plan_id + chat_session_id 判断是否已创建面试记录。
     */
    @GetMapping("/lookup")
    public Map<String, Object> lookup(
            @RequestParam("student_id") String studentId,
            @RequestParam("plan_id") String planId,
            @RequestParam("chat_session_id") String chatSessionId
    ) {
        return recordService.lookupByPlanAndChat(studentId, planId, chatSessionId);
    }

    @GetMapping("/{recordId}")
    public Map<String, Object> detail(
            @PathVariable("recordId") String recordId,
            @RequestParam("student_id") String studentId
    ) {
        return recordService.getDetail(studentId, recordId);
    }

    @GetMapping("/{recordId}/answers")
    public Map<String, Object> answers(
            @PathVariable("recordId") String recordId,
            @RequestParam("student_id") String studentId
    ) {
        return recordService.listAnswers(studentId, recordId);
    }

    @DeleteMapping("/{recordId}")
    public Map<String, Object> delete(
            @PathVariable("recordId") String recordId,
            @RequestParam("student_id") String studentId
    ) {
        return recordService.delete(studentId, recordId);
    }
}
