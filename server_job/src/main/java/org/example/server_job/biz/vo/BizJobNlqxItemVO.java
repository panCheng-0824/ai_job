package org.example.server_job.biz.vo;

import lombok.Data;

/**
 * 岗位能力需求（{@code job_nl}）单项：编码、短标签、字典完整描述。
 */
@Data
public class BizJobNlqxItemVO {

    /** {@code job_nl.DM}，如 I、S、C */
    private String code;

    /** 短标签，如「调研型(I)」 */
    private String label;

    /** 字典完整 NAME（含类型说明） */
    private String detail;
}
