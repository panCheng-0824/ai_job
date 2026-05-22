package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("student_company_review_tag")
public class StudentCompanyReviewTag {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long companyReviewId;

    private String tagId;
}
