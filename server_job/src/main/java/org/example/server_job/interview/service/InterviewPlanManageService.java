package org.example.server_job.interview.service;

import org.example.server_job.interview.dto.InterviewPlanSaveRequest;

import java.util.Map;

/**
 * 题目大纲管理：列表、详情、CRUD（仅绑定二级行业）。
 */
public interface InterviewPlanManageService {

    /** 按学号筛选大纲列表（每个 plan_id 仅返回最新版本） */
    Map<String, Object> listByStudent(String studentId, String status, String industryCategoryId);

    /** 大纲详情：基础信息 + 模块标签 + 题目列表 + 可选版本列表 */
    Map<String, Object> getDetail(String studentId, String planId, Integer version);

    /** 在二级行业下新建大纲；studentIdQuery 为 URL ?student_id= 兜底 */
    Map<String, Object> create(InterviewPlanSaveRequest request, String studentIdQuery);

    /** 编辑升版：version + 1 全新 INSERT；studentIdQuery 为 URL ?student_id= 兜底 */
    Map<String, Object> revise(String planId, InterviewPlanSaveRequest request, String studentIdQuery);

    /** 删除大纲（全部版本） */
    Map<String, Object> delete(String studentId, String planId);
}
