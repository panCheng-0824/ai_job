package org.example.server_job.interview.service;

import org.example.server_job.interview.dto.InterviewIndustryCategorySaveRequest;

import java.util.Map;

/**
 * 行业分类字典：查询、维护 CRUD。
 */
public interface InterviewIndustryCategoryService {

    /**
     * 查询行业分类列表。
     *
     * @param purpose      可选 intent / classify
     * @param tree         是否树形
     * @param includeAll   true 含 disabled；维护页用
     */
    Map<String, Object> listCategories(String purpose, boolean tree, boolean includeAll);

    /** 单条详情（含时间戳） */
    Map<String, Object> getDetail(String categoryId);

    /** 新增分类 */
    Map<String, Object> create(InterviewIndustryCategorySaveRequest request);

    /** 修改分类（category_id 不可变） */
    Map<String, Object> update(String categoryId, InterviewIndustryCategorySaveRequest request);

    /** 删除分类（有子级或大纲引用时拒绝） */
    Map<String, Object> delete(String categoryId);
}
