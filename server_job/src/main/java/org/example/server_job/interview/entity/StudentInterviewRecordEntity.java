package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 学生面试总结记录，对应「我的面试记录」列表一行。
 */
@Data
@TableName("student_interview_records")
public class StudentInterviewRecordEntity {

    @TableId(value = "record_id", type = IdType.INPUT)
    private String recordId;

    @TableField("student_id")
    private String studentId;

    @TableField("interview_session_id")
    private String interviewSessionId;

    @TableField("chat_session_id")
    private String chatSessionId;

    @TableField("plan_id")
    private String planId;

    @TableField("plan_version")
    private Integer planVersion;

    @TableField("industry_category_id")
    private String industryCategoryId;

    @TableField("target_role")
    private String targetRole;

    @TableField("plan_title")
    private String planTitle;

    @TableField("session_status")
    private String sessionStatus;

    @TableField("summary_status")
    private String summaryStatus;

    @TableField("total_score")
    private BigDecimal totalScore;

    @TableField("report_id")
    private String reportId;

    @TableField("question_total")
    private Integer questionTotal;

    @TableField("question_answered")
    private Integer questionAnswered;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("summary_at")
    private LocalDateTime summaryAt;

    @TableField("completed_at")
    private LocalDateTime completedAt;
}
