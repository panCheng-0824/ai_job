package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("student_favorite_job")
public class StudentFavoriteJob {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String studentId;

    private String jobId;

    private LocalDateTime createdAt;
}
