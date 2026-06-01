package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 大纲题目预设追问，对应表 {@code interview_plan_question_followups}。
 *
 * <p>与 {@link InterviewPlanQuestionEntity} 一对多，替代 payload_json 内 {@code preset_followups[]}。
 */
@Data
@TableName("interview_plan_question_followups")
public class InterviewPlanQuestionFollowupEntity {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 所属题目物理主键 */
    @TableField("iq_row_id")
    private String iqRowId;

    /** 追问顺序（0-based） */
    @TableField("seq_no")
    private Integer seqNo;

    /** 预设追问文案 */
    @TableField("followup_text")
    private String followupText;
}
