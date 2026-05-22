package org.example.server_job.chat.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.Instant;

@Data
@TableName("t_chat_session")
public class ChatSession {

    @TableId(value = "session_id", type = IdType.INPUT)
    private String sessionId;

    @TableField("student_id")
    private String studentId;

    private String usercode;

    private String username;

    @TableField("role_name")
    private String roleName;

    @TableField("model_level")
    private String modelLevel;

    @TableField("created_at")
    private Instant createdAt;

    @TableField("updated_at")
    private Instant updatedAt;
}
