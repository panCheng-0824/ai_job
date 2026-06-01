package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 审计日志实体，对应表 {@code interview_audit_logs}。 */
@Data
@TableName("interview_audit_logs")
public class InterviewAuditLogEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("interview_session_id")
    private String interviewSessionId;

    @TableField("student_id")
    private String studentId;

    @TableField("event_type")
    private String eventType;

    private String actor;

    @TableField("detail_json")
    private String detailJson;

    @TableField("trace_id")
    private String traceId;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
