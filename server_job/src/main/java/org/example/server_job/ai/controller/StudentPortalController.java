package org.example.server_job.ai.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.student.service.StudentJobMatchHistoryService;
import org.example.server_job.student.service.StudentPortalActivityService;
import org.example.server_job.student.service.StudentProfileExtService;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;
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
    private final StudentJobMatchHistoryService jobMatchHistoryService;
    private final StudentProfileExtService profileExtService;
    private final ObjectMapper objectMapper;

    public StudentPortalController(
            StudentPortalActivityService portalActivityService,
            StudentJobMatchHistoryService jobMatchHistoryService,
            StudentProfileExtService profileExtService,
            ObjectMapper objectMapper
    ) {
        this.portalActivityService = portalActivityService;
        this.jobMatchHistoryService = jobMatchHistoryService;
        this.profileExtService = profileExtService;
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

    /** 合并学籍与学生扩展的完整画像（含求职意向、能力标签） */
    @GetMapping("/me/profile")
    public Map<String, Object> meProfile(@RequestParam("student_id") String studentId) {
        return profileExtService.getMergedProfile(studentId);
    }

    /** 分段更新学生自助画像（contact / job_intent / ability） */
    @PutMapping("/me/profile")
    public Map<String, Object> meProfileUpdate(
            @RequestParam("student_id") String studentId,
            @RequestBody String body
    ) throws Exception {
        JsonNode n = objectMapper.readTree(body == null ? "{}" : body);
        return profileExtService.updateProfile(studentId, n);
    }

    /** 上传学生头像至 MinIO 并写入画像 */
    @PostMapping("/me/profile/avatar")
    public Map<String, Object> meProfileAvatar(
            @RequestParam("student_id") String studentId,
            @RequestPart("file") MultipartFile file
    ) {
        return profileExtService.uploadAvatar(studentId, file);
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

    @GetMapping("/me/applications")
    public Map<String, Object> meApplications(@RequestParam("student_id") String studentId) {
        return portalActivityService.getMeApplications(studentId);
    }

    @PostMapping("/me/applications")
    public Map<String, Object> meApplicationsSubmit(@RequestBody String body) throws Exception {
        JsonNode n = objectMapper.readTree(body == null ? "{}" : body);
        return portalActivityService.submitJobApplication(
                n.path("student_id").asText(),
                n.path("job_id").asText(),
                n.path("resume_id").asText(""),
                n.path("source").asText("one_click")
        );
    }

    @GetMapping("/me/interview-bookings")
    public Map<String, Object> meInterviewBookings(@RequestParam("student_id") String studentId) {
        return portalActivityService.getMeInterviewBookings(studentId);
    }

    @PostMapping("/me/interview-bookings")
    public Map<String, Object> meInterviewBookingsSubmit(@RequestBody String body) throws Exception {
        JsonNode n = objectMapper.readTree(body == null ? "{}" : body);
        return portalActivityService.submitJobInterviewBooking(
                n.path("student_id").asText(),
                n.path("job_id").asText(),
                n.path("source").asText("job_card")
        );
    }

    /** 智能匹配历史列表（分页，按时间倒序，默认每页 8 条） */
    @GetMapping("/me/job-match-history")
    public Map<String, Object> meJobMatchHistory(
            @RequestParam("student_id") String studentId,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "8") Integer page_size
    ) {
        return jobMatchHistoryService.listHistory(studentId, page, page_size);
    }

    /** 保存一次成功匹配记录（返回岗位才算成功） */
    @PostMapping("/me/job-match-history")
    public Map<String, Object> meJobMatchHistorySave(@RequestBody String body) throws Exception {
        JsonNode n = objectMapper.readTree(body == null ? "{}" : body);
        String sid = n.path("student_id").asText();
        return jobMatchHistoryService.saveHistory(sid, n);
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
