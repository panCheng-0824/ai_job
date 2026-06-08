package org.example.server_job.biz.vo;

import lombok.Data;

import java.util.List;

/**
 * 岗位关键字分组展示：{@code job_gjz_fz} 分组名 + {@code job_gjz} 关键字名称列表。
 */
@Data
public class BizJobGjzGroupVO {

    private String groupName;
    private List<String> keywords;
}
