package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 系统字典表 {@code sys_code} 实体。
 * <p>
 * 按 {@code BM}（类型编码）分组，{@code DM} 为字典项编码，{@code FID} 指向父级实现省市区等级联。
 * 供岗位、企业等主数据字段翻译及前端下拉选项使用。
 * </p>
 */
@Data
@TableName("sys_code")
public class SysCode {

    @TableId("ID")
    private String id;

    @TableField("FID")
    private String fid;

    @TableField("NAME")
    private String name;

    @TableField("DM")
    private String dm;

    @TableField("MC")
    private String mc;

    @TableField("BM")
    private String bm;

    @TableField("LBMC")
    private String lbmc;
}
