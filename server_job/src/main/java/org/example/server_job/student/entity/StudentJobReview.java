package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("student_job_review")
public class StudentJobReview {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String studentId;

    private String jobId;

    private Integer stars;

    private String comment;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
