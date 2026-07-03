package org.example.server_job.student.service;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.Map;

/**
 * 学生智能匹配历史：列表查询与保存（不限制条数）。
 */
public interface StudentJobMatchHistoryService {

    /**
     * 分页查询该学生匹配历史（按时间倒序）。
     *
     * @param page     页码，从 1 开始
     * @param pageSize 每页条数，默认 8
     */
    Map<String, Object> listHistory(String studentId, Integer page, Integer pageSize);

    /**
     * 保存一次成功匹配记录。
     *
     * @param studentId 学号
     * @param body      含 query、settings、jobs、recommendation 等字段
     */
    Map<String, Object> saveHistory(String studentId, JsonNode body);
}
