package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("t_biz_company_info")
public class BizCompanyInfo {

    @TableId("id")
    private String id;

    @TableField("companySize")
    private String companySize;

    @TableField("companyName")
    private String companyName;

    @TableField("website")
    private String website;

    @TableField("area")
    private String area;

    @TableField("address")
    private String address;

    @TableField("companyType")
    private String companyType;
}
