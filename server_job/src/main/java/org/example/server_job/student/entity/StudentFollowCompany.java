package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("student_follow_company")
public class StudentFollowCompany {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String studentId;

    private String creditCode;

    private LocalDateTime createdAt;
}
