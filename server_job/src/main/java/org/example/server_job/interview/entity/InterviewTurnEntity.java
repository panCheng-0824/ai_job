package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 面试回合实体，对应表 {@code interview_turns}（幂等键唯一约束）。 */
@Data
@TableName("interview_turns")
public class InterviewTurnEntity {

    @TableId(value = "turn_id", type = IdType.INPUT)
    private String turnId;

    @TableField("interview_session_id")
    private String interviewSessionId;

    @TableField("student_id")
    private String studentId;

    @TableField("idempotency_key")
    private String idempotencyKey;

    private String action;

    @TableField("payload_json")
    private String payloadJson;

    @TableField("result_snapshot_json")
    private String resultSnapshotJson;

    @TableField("processed_at")
    private LocalDateTime processedAt;
}
