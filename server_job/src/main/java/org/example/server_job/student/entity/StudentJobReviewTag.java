package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("student_job_review_tag")
public class StudentJobReviewTag {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long jobReviewId;

    private String tagId;
}
