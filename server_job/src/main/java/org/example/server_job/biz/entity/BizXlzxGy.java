package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("t_biz_xlzx_gy")
public class BizXlzxGy {

    @TableField("wid")
    private String wid;

    @TableField("xh")
    private Integer xh;

    @TableField("zxid")
    private String zxid;

    @TableField("zssj")
    private String zssj;

    @TableField("zxgy")
    private String zxgy;
}
