package org.example.server_job.interview.dto;

/**
 * 行业分类新增/修改请求体。
 *
 * @param categoryId          可选；不传则按 categoryCode 生成
 * @param parentId            一级为空，二级必填
 * @param level               1 或 2
 * @param categoryCode        稳定编码
 * @param categoryName        展示名称
 * @param description         具体描述
 * @param intentKeywords      意图关键词，逗号分隔
 * @param enabledForIntent    是否参与意图识别
 * @param enabledForClassify  是否参与大纲分类
 * @param sortNo              排序
 * @param status              active / disabled
 */
public record InterviewIndustryCategorySaveRequest(
        String categoryId,
        String parentId,
        Integer level,
        String categoryCode,
        String categoryName,
        String description,
        String intentKeywords,
        Boolean enabledForIntent,
        Boolean enabledForClassify,
        Integer sortNo,
        String status
) {
}
