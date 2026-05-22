package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("t_biz_xlzx_zx")
public class BizXlzxZx {

    @TableField("wid")
    private String wid;

    @TableField("xh")
    private Integer xh;

    @TableField("nd")
    private Integer nd;

    @TableField("zxyt")
    private String zxyt;

    @TableField("zxxg")
    private String zxxg;

    @TableField("zxsj")
    private String zxsj;
}
