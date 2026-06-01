package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/** 面试报告实体，对应表 {@code interview_reports}。 */
@Data
@TableName("interview_reports")
public class InterviewReportEntity {

    @TableId(value = "report_id", type = IdType.INPUT)
    private String reportId;

    @TableField("interview_session_id")
    private String interviewSessionId;

    @TableField("student_id")
    private String studentId;

    @TableField("payload_json")
    private String payloadJson;

    @TableField("rubric_version")
    private String rubricVersion;

    @TableField("scorer_model")
    private String scorerModel;

    @TableField("total_score")
    private BigDecimal totalScore;

    @TableField("generated_at")
    private LocalDateTime generatedAt;
}
