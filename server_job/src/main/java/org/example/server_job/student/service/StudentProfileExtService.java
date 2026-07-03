package org.example.server_job.student.service;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

/**
 * 学生自助画像扩展：读取合并画像、分段更新、缓存失效。
 */
public interface StudentProfileExtService {

    Map<String, Object> getMergedProfile(String studentId);

    Map<String, Object> updateProfile(String studentId, JsonNode body);

    Map<String, Object> uploadAvatar(String studentId, MultipartFile file);
}
