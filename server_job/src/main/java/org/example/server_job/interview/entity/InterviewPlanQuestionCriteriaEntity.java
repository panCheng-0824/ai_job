package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 大纲题目评分标准键值，对应表 {@code interview_plan_question_criteria}。
 *
 * <p>与 {@link InterviewPlanQuestionEntity} 一对多，替代 payload_json 内 {@code eval_criteria} 对象。
 */
@Data
@TableName("interview_plan_question_criteria")
public class InterviewPlanQuestionCriteriaEntity {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 所属题目物理主键 */
    @TableField("iq_row_id")
    private String iqRowId;

    /** 评分项键，如 clarity / depth */
    @TableField("criterion_key")
    private String criterionKey;

    /** 评分项描述（列长 512，写入时会截断） */
    @TableField("criterion_value")
    private String criterionValue;

    @TableField("sort_no")
    private Integer sortNo;
}
