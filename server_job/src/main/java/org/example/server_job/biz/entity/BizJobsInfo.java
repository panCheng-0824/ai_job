package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("t_biz_jobs_info")
public class BizJobsInfo {

    @TableId("id")
    private String id;

    @TableField("source")
    private String source;

    @TableField("companyId")
    private String companyId;

    @TableField("industry")
    private String industry;

    @TableField("jobNumb")
    private String jobNumb;

    @TableField("jobType")
    private String jobType;

    @TableField("majorReq")
    private String majorReq;

    @TableField("companyName")
    private String companyName;

    @TableField("area")
    private String area;

    @TableField("useKeyWords")
    private String useKeyWords;

    @TableField("create_time")
    private String createTime;

    @TableField("html")
    private String html;

    @TableField("synRag")
    private String synRag;

    @TableField("ragMdPath")
    private String ragMdPath;



    @TableField("jobName")
    private String jobName;

    @TableField("address")
    private String address;

    @TableField("companyType")
    private String companyType;

    @TableField("publishTime")
    private String publishTime;

    @TableField("salaryRange")
    private String salaryRange;

    @TableField("education")
    private String education;

    @TableField("vacancies")
    private String vacancies;

    @TableField("content")
    private String content;

    @TableField("postingTitle")
    private String postingTitle;
}
