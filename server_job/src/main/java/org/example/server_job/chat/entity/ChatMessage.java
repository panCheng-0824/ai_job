package org.example.server_job.chat.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("t_chat_message")
public class ChatMessage {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("session_id")
    private String sessionId;

    private String role;

    private String content;

    @TableField("extra_json")
    private String extraJson;

    @TableField("msg_ts")
    private String msgTs;

    @TableField("seq_no")
    private Integer seqNo;
}
