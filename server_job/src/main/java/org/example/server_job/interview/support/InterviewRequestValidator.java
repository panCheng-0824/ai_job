package org.example.server_job.interview.support;

import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

/**
 * 对外 API 请求参数校验（学号、幂等键等）。
 */
public final class InterviewRequestValidator {

    private InterviewRequestValidator() {
    }

    public static String requireStudentId(String studentId) {
        if (studentId == null || studentId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "student_id 不能为空");
        }
        return studentId.trim();
    }

    /**
     * 优先取 body 中的 student_id，缺失时回退 query 参数（与列表/删除 API 一致）。
     */
    public static String requireStudentId(String fromBody, String fromQuery) {
        if (fromBody != null && !fromBody.isBlank()) {
            return fromBody.trim();
        }
        return requireStudentId(fromQuery);
    }

    public static String requireIdempotencyKey(String key) {
        if (key == null || key.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "idempotency_key 不能为空");
        }
        return key.trim();
    }
}
