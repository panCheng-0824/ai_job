package org.example.server_job.student.service;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.Map;

/**
 * 学生智能匹配历史：列表查询与保存（每生最多 5 条）。
 */
public interface StudentJobMatchHistoryService {

    /**
     * 查询该学生全部历史（按时间倒序，最多 5 条）。
     */
    Map<String, Object> listHistory(String studentId);

    /**
     * 保存一次成功匹配记录；若超过 5 条则删除最旧记录。
     *
     * @param studentId 学号
     * @param body      含 query、settings、jobs、recommendation 等字段
     */
    Map<String, Object> saveHistory(String studentId, JsonNode body);
}
