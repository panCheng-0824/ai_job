package org.example.server_job.biz.dto;

import lombok.Data;

/**
 * 岗位按企业维度（单位性质 / 行业）聚合统计行。
 */
@Data
public class JobFacetCountRow {

    /** 原始分组键：dwxz 或 hylx 的字符串形式 */
    private String code;

    private Long total;

    private Long synced;
}
