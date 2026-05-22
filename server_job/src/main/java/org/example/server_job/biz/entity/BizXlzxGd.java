package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("t_biz_xlzx_gd")
public class BizXlzxGd {

    @TableField("xh")
    private Integer xh;

    @TableField("wid")
    private String wid;

    @TableField("sqid")
    private String sqid;

    @TableField("tjsj")
    private String tjsj;

    @TableField("xqwt")
    private String xqwt;

    @TableField("wtpg")
    private String wtpg;

    @TableField("zxxg")
    private String zxxg;

    @TableField("xszt")
    private String xszt;

    @TableField("yxhz")
    private String yxhz;

    @TableField("qtqk")
    private String qtqk;
}
