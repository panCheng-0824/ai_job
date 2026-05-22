package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDate;

@Data
@TableName("t_biz_family_info")
public class BizFamilyInfo {

    @TableField("xh")
    private Integer xh;

    @TableField("jzxn")
    private String jzxn;

    @TableField("ybrgx")
    private String ybrgx;

    @TableField("jzcsrq")
    private LocalDate jzcsrq;

    @TableField("zjlx")
    private String zjlx;

    @TableField("jzzjh")
    private String jzzjh;

    @TableField("jzdw")
    private String jzdw;

    @TableField("jzzw")
    private String jzzw;

    @TableField("jzzy")
    private String jzzy;

    @TableField("jayzbm")
    private String jayzbm;

    @TableField("jalxdh")
    private String jalxdh;

    @TableField("jzsj")
    private String jzsj;

    @TableField("pjysr")
    private Double pjysr;
}
