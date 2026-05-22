package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 学生简历的一条「副本」记录。同一学号可有多份逻辑简历（不同 {@link #seriesId}），
 * 同一份逻辑简历下可有多个副本（不同 {@link #id}，展示名常带时间戳后缀）。
 */
@Data
@TableName("student_resume")
public class StudentResume {

    @TableId(type = IdType.INPUT)
    private String id;

    private String studentId;

    private String seriesId;

    private String templateId;

    private String displayName;

    private String contentJson;

    /** 学号下对话/规划师引用的全局默认副本 */
    private Boolean isDefault;

    /** 同一 {@link #seriesId} 下编辑与加载时优先使用的默认副本 */
    private Boolean isSeriesDefault;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
