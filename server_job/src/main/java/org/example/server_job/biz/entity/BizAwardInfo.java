package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("t_biz_award_info")
public class BizAwardInfo {

    @TableField("xh")
    private Integer xh;

    @TableField("jxnd")
    private Integer jxnd;

    @TableField("xmmc")
    private String xmmc;

    @TableField("xmms")
    private String xmms;

    @TableField("xmlx")
    private String xmlx;
}
