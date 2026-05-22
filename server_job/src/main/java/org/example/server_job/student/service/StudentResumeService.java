package org.example.server_job.student.service;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.Map;

public interface StudentResumeService {

    Map<String, Object> listStore(String studentId);

    Map<String, Object> get(String studentId, String resumeId);

    Map<String, Object> upsert(String studentId, String resumeId, JsonNode body);

    Map<String, Object> delete(String studentId, String resumeId);

    /**
     * @param scope {@code series} 仅设为本简历线默认；{@code global} 设为对话用全局默认
     */
    Map<String, Object> setDefault(String studentId, String resumeId, String scope);
}
