package org.example.server_job.interview.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * 题目大纲新增/升版请求体。
 * industry_category_id 必须为 level=2 的行业 ID。
 * JSON 字段使用 snake_case（与前端 planForm 一致）。
 * 注：Java record 上 @JsonNaming 对反序列化无效，须用 @JsonProperty 显式映射。
 */
public record InterviewPlanSaveRequest(
        @JsonProperty("student_id") String studentId,
        @JsonProperty("industry_category_id") String industryCategoryId,
        @JsonProperty("plan_id") String planId,
        @JsonProperty("title") String title,
        @JsonProperty("target_role") String targetRole,
        @JsonProperty("introduction") String introduction,
        @JsonProperty("suitable_audience") String suitableAudience,
        @JsonProperty("status") String status,
        @JsonProperty("module_tags") List<String> moduleTags,
        @JsonProperty("questions") List<InterviewPlanQuestionSaveItem> questions
) {
}
