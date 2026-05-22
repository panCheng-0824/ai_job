package org.example.server_job.ai.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.student.service.StudentPortalActivityService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 学生门户活动：收藏、关注、评价；数据在 MySQL（见 ai_job/sql/student_portal_activity_mysql8.sql），由 server_job 编排。
 */
@RestController
@RequestMapping("/api")
public class StudentPortalController {

    private final StudentPortalActivityService portalActivityService;
    private final ObjectMapper objectMapper;

    public StudentPortalController(StudentPortalActivityService portalActivityService, ObjectMapper objectMapper) {
        this.portalActivityService = portalActivityService;
        this.objectMapper = objectMapper;
    }

    @GetMapping("/review-tags")
    public Map<String, Object> reviewTags() {
        return portalActivityService.getReviewTags();
    }

    @GetMapping("/me/summary")
    public Map<String, Object> meSummary(@RequestParam("student_id") String studentId) {
        return portalActivityService.getMeSummary(studentId);
    }

    @GetMapping("/me/context")
    public Map<String, Object> meContext(
            @RequestParam("student_id") String studentId,
            @RequestParam(value = "job_id", required = false, defaultValue = "") String jobId,
            @RequestParam(value = "credit_code", required = false, defaultValue = "") String creditCode
    ) {
        return portalActivityService.getMeContext(studentId, jobId, creditCode);
    }

    @GetMapping("/me/favorites")
    public Map<String, Object> meFavorites(@RequestParam("student_id") String studentId) {
        return portalActivityService.getMeFavorites(studentId);
    }

    @PostMapping("/me/favorites/toggle")
    public Map<String, Object> meFavoritesToggle(@RequestBody String body) throws Exception {
        JsonNode n = objectMapper.readTree(body == null ? "{}" : body);
        return portalActivityService.toggleFavorite(
                n.path("student_id").asText(),
                n.path("job_id").asText()
        );
    }

    @GetMapping("/me/follows")
    public Map<String, Object> meFollows(@RequestParam("student_id") String studentId) {
        return portalActivityService.getMeFollows(studentId);
    }

    @PostMapping("/me/follows/toggle")
    public Map<String, Object> meFollowsToggle(@RequestBody String body) throws Exception {
        JsonNode n = objectMapper.readTree(body == null ? "{}" : body);
        return portalActivityService.toggleFollow(
                n.path("student_id").asText(),
                n.path("credit_code").asText()
        );
    }

    @GetMapping("/me/reviews/jobs")
    public Map<String, Object> meReviewsJobs(@RequestParam("student_id") String studentId) {
        return portalActivityService.listMyJobReviewsEnriched(studentId);
    }

    @GetMapping("/me/reviews/companies")
    public Map<String, Object> meReviewsCompanies(@RequestParam("student_id") String studentId) {
        return portalActivityService.listMyCompanyReviewsEnriched(studentId);
    }

    @PostMapping("/me/reviews/job")
    public Map<String, Object> meReviewsJob(@RequestBody String body) throws Exception {
        JsonNode n = objectMapper.readTree(body == null ? "{}" : body);
        return portalActivityService.upsertJobReview(
                n.path("student_id").asText(),
                n.path("job_id").asText(),
                n.path("stars").asInt(5),
                n.path("comment").asText(""),
                readStringList(n, "tags")
        );
    }

    @PostMapping("/me/reviews/company")
    public Map<String, Object> meReviewsCompany(@RequestBody String body) throws Exception {
        JsonNode n = objectMapper.readTree(body == null ? "{}" : body);
        return portalActivityService.upsertCompanyReview(
                n.path("student_id").asText(),
                n.path("credit_code").asText(),
                n.path("stars").asInt(5),
                n.path("comment").asText(""),
                readStringList(n, "tags")
        );
    }

    private static List<String> readStringList(JsonNode n, String field) {
        JsonNode arr = n.get(field);
        if (arr == null || !arr.isArray()) {
            return List.of();
        }
        List<String> out = new ArrayList<>();
        for (JsonNode x : arr) {
            String s = x.asText("").trim();
            if (!s.isEmpty()) {
                out.add(s);
            }
        }
        return out;
    }

    @DeleteMapping("/me/reviews/job")
    public Map<String, Object> deleteMeReviewsJob(
            @RequestParam("student_id") String studentId,
            @RequestParam("job_id") String jobId
    ) {
        return portalActivityService.deleteJobReview(studentId, jobId);
    }

    @DeleteMapping("/me/reviews/company")
    public Map<String, Object> deleteMeReviewsCompany(
            @RequestParam("student_id") String studentId,
            @RequestParam("credit_code") String creditCode
    ) {
        return portalActivityService.deleteCompanyReview(studentId, creditCode);
    }

    @GetMapping("/jobs/{jobId}/reviews")
    public Map<String, Object> publicJobReviews(@PathVariable String jobId) {
        return portalActivityService.aggregateJobReviews(jobId);
    }

    @GetMapping("/companies/{creditCode}/reviews")
    public Map<String, Object> publicCompanyReviews(@PathVariable String creditCode) {
        return portalActivityService.aggregateCompanyReviews(creditCode);
    }
}
