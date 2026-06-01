package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 大纲题目考察维度，对应表 {@code interview_plan_question_dimensions}。
 *
 * <p>与 {@link InterviewPlanQuestionEntity} 一对多，替代 payload_json 内 {@code dimensions[]}。
 */
@Data
@TableName("interview_plan_question_dimensions")
public class InterviewPlanQuestionDimensionEntity {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 所属题目物理主键 */
    @TableField("iq_row_id")
    private String iqRowId;

    /** 考察维度编码，如 communication / technical_depth */
    @TableField("dimension_code")
    private String dimensionCode;

    @TableField("sort_no")
    private Integer sortNo;
}
