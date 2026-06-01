package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 面试大纲基础信息实体，对应表 {@code interview_plan_basics}。
 * 逻辑主键 (plan_id, version)，物理主键 plan_row_id = plan_id#version。
 */
@Data
@TableName("interview_plan_basics")
public class InterviewPlanBasicsEntity {

    @TableId(value = "plan_row_id", type = IdType.INPUT)
    private String planRowId;

    @TableField("plan_id")
    private String planId;

    private Integer version;

    private String title;

    @TableField("target_role")
    private String targetRole;

    private String introduction;

    @TableField("suitable_audience")
    private String suitableAudience;

    @TableField("industry_category_id")
    private String industryCategoryId;

    @TableField("industry_classify_confidence")
    private BigDecimal industryClassifyConfidence;

    @TableField("industry_classify_reason")
    private String industryClassifyReason;

    @TableField("industry_classify_source")
    private String industryClassifySource;

    @TableField("industry_classified_at")
    private LocalDateTime industryClassifiedAt;

    @TableField("source_material_hash")
    private String sourceMaterialHash;

    @TableField("rubric_version")
    private String rubricVersion;

    @TableField("planner_model")
    private String plannerModel;

    @TableField("question_count")
    private Integer questionCount;

    @TableField("estimated_minutes")
    private Integer estimatedMinutes;

    private String visibility;

    private String status;

    @TableField("cache_hit_id")
    private String cacheHitId;

    @TableField("student_id")
    private String studentId;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;
}
