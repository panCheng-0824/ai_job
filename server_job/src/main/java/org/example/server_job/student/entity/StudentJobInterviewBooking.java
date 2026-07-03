package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("student_job_interview_booking")
public class StudentJobInterviewBooking {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String studentId;

    private String jobId;

    private String jobTitle;

    private String companyName;

    private String source;

    private LocalDateTime createdAt;
}
