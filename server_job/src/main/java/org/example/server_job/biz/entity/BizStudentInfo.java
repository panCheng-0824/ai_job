package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDate;

@Data
@TableName("t_biz_student_info")
public class BizStudentInfo {

    @TableField("xxmc")
    private String xxmc;

    @TableField("yxmc")
    private String yxmc;

    @TableField("csrq")
    private LocalDate csrq;

    @TableField("zymc")
    private String zymc;

    @TableField("bjmc")
    private String bjmc;

    @TableField("xm")
    private String xm;

    @TableField("xh")
    private Integer xh;

    @TableField("zjh")
    private String zjh;

    @TableField("mz")
    private String mz;

    @TableField("xl")
    private String xl;

    @TableField("bynd")
    private Integer bynd;

    @TableField("byjj")
    private String byjj;

    @TableField("xb")
    private String xb;

    @TableField("pjjd")
    private Double pjjd;

    @TableField("tccj")
    private String tccj;
}
