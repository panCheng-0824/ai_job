package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 大纲面试模块标签（如「技术基础」），与行业分类不同。
 */
@Data
@TableName("interview_plan_module_tags")
public class InterviewPlanModuleTagEntity {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    @TableField("plan_row_id")
    private String planRowId;

    @TableField("tag_name")
    private String tagName;

    @TableField("sort_no")
    private Integer sortNo;
}
