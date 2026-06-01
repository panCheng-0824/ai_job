package org.example.server_job.interview.service;

import java.util.Map;

/**
 * 学生「我的面试记录」：总结列表、详情、逐题答题。
 */
public interface StudentInterviewRecordService {

    Map<String, Object> listByStudent(String studentId, String summaryStatus);

    Map<String, Object> getDetail(String studentId, String recordId);

    Map<String, Object> listAnswers(String studentId, String recordId);

    /** 删除单条面试记录及关联会话（不删大纲题库）。 */
    Map<String, Object> delete(String studentId, String recordId);

    /**
     * 按学号 + 大纲 plan_id + 门户 chat_session_id 精确查找是否已创建面试记录。
     */
    Map<String, Object> lookupByPlanAndChat(String studentId, String planId, String chatSessionId);
}
