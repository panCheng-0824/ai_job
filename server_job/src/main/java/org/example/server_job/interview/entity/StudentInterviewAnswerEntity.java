package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 学生逐题答题记录，映射大纲题目与面试会话。
 */
@Data
@TableName("student_interview_answers")
public class StudentInterviewAnswerEntity {

    @TableId(value = "answer_row_id", type = IdType.INPUT)
    private String answerRowId;

    @TableField("interview_session_id")
    private String interviewSessionId;

    @TableField("student_id")
    private String studentId;

    @TableField("record_id")
    private String recordId;

    @TableField("plan_id")
    private String planId;

    @TableField("plan_version")
    private Integer planVersion;

    @TableField("iq_row_id")
    private String iqRowId;

    @TableField("question_id")
    private String questionId;

    @TableField("seq_no")
    private Integer seqNo;

    @TableField("answer_status")
    private String answerStatus;

    @TableField("answer_text")
    private String answerText;

    private BigDecimal score;

    @TableField("evaluator_comment")
    private String evaluatorComment;

    @TableField("turn_id")
    private String turnId;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("answered_at")
    private LocalDateTime answeredAt;

    @TableField("summarized_at")
    private LocalDateTime summarizedAt;
}
