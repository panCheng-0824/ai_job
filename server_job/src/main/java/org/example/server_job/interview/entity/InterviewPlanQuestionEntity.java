package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 面试大纲单题实体，对应表 {@code interview_plan_questions}。
 */
@Data
@TableName("interview_plan_questions")
public class InterviewPlanQuestionEntity {

    @TableId(value = "iq_row_id", type = IdType.INPUT)
    private String iqRowId;

    @TableField("plan_row_id")
    private String planRowId;

    @TableField("plan_id")
    private String planId;

    @TableField("plan_version")
    private Integer planVersion;

    @TableField("question_id")
    private String questionId;

    @TableField("seq_no")
    private Integer seqNo;

    @TableField("question_text")
    private String questionText;

    private BigDecimal weight;

    @TableField("thinking_hint")
    private String thinkingHint;

    @TableField("timeout_seconds")
    private Integer timeoutSeconds;

    @TableField("reference_answer")
    private String referenceAnswer;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
