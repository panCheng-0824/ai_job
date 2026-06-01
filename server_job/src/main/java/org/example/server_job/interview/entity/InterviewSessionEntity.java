package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 面试会话实体，对应表 {@code interview_sessions}。
 * 进度、超时、评分真相源；与 chat_session_id 松耦合关联。
 */
@Data
@TableName("interview_sessions")
public class InterviewSessionEntity {

    @TableId(value = "interview_session_id", type = IdType.INPUT)
    private String interviewSessionId;

    @TableField("student_id")
    private String studentId;

    @TableField("chat_session_id")
    private String chatSessionId;

    @TableField("plan_id")
    private String planId;

    @TableField("plan_version")
    private Integer planVersion;

    private String status;

    private String phase;

    @TableField("current_question_index")
    private Integer currentQuestionIndex;

    @TableField("lock_version")
    private Integer lockVersion;

    @TableField("snapshots_json")
    private String snapshotsJson;

    /** V2 已迁移库无此列；保留字段仅兼容旧库双写期，新库请执行 v2_upgrade 后忽略 */
    @TableField(value = "answers_json", exist = false)
    private String answersJson;

    @TableField("report_id")
    private String reportId;

    @TableField("token_budget_used")
    private Integer tokenBudgetUsed;

    @TableField("scorer_version")
    private String scorerVersion;

    @TableField("graph_checkpoint_id")
    private String graphCheckpointId;

    @TableField("meta_json")
    private String metaJson;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;

    @TableField("completed_at")
    private LocalDateTime completedAt;
}
