package org.example.server_job.ai.controller;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.student.service.StudentResumeService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

import static org.springframework.http.HttpStatus.BAD_REQUEST;

/**
 * 学生简历：与 web_job ResumeRecord / localStorage 结构对齐（见 GET 返回体）。
 */
@RestController
@RequestMapping("/api/me")
public class StudentResumeController {

    private final StudentResumeService studentResumeService;
    private final ObjectMapper objectMapper;

    public StudentResumeController(StudentResumeService studentResumeService, ObjectMapper objectMapper) {
        this.studentResumeService = studentResumeService;
        this.objectMapper = objectMapper;
    }

    @GetMapping("/resumes")
    public Map<String, Object> list(@RequestParam("student_id") String studentId) {
        return studentResumeService.listStore(studentId);
    }

    @GetMapping("/resumes/{resumeId}")
    public Map<String, Object> get(
            @PathVariable("resumeId") String resumeId,
            @RequestParam("student_id") String studentId
    ) {
        return studentResumeService.get(studentId, resumeId);
    }

    @PutMapping("/resumes/{resumeId}")
    public Map<String, Object> upsert(
            @PathVariable("resumeId") String resumeId,
            @RequestParam("student_id") String studentId,
            @RequestBody String body
    ) {
        JsonNode n;
        try {
            n = objectMapper.readTree(body == null || body.isBlank() ? "{}" : body);
        } catch (JsonProcessingException e) {
            throw new ResponseStatusException(BAD_REQUEST, "请求体不是合法 JSON");
        }
        return studentResumeService.upsert(studentId, resumeId, n);
    }

    @DeleteMapping("/resumes/{resumeId}")
    public Map<String, Object> delete(
            @PathVariable("resumeId") String resumeId,
            @RequestParam("student_id") String studentId
    ) {
        return studentResumeService.delete(studentId, resumeId);
    }

    @PostMapping("/resumes/{resumeId}/default")
    public Map<String, Object> setDefault(
            @PathVariable("resumeId") String resumeId,
            @RequestParam("student_id") String studentId,
            @RequestParam(value = "scope", defaultValue = "series") String scope
    ) {
        return studentResumeService.setDefault(studentId, resumeId, scope);
    }
}
