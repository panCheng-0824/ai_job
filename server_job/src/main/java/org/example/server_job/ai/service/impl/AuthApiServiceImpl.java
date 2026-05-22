package org.example.server_job.ai.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.service.AuthApiService;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.biz.support.StudentPortraitChineseJsonTranslator;
import org.example.server_job.biz.vo.BizStudentPortraitVO;
import org.example.server_job.client.redis.RedisStringClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.NOT_FOUND;

@Service
public class AuthApiServiceImpl implements AuthApiService {

    private static final Logger log = LogManager.getLogger(AuthApiServiceImpl.class);

    private final BizStudentInfoService bizStudentInfoService;
    private final RedisStringClient redis;
    private final ObjectMapper objectMapper;

    @Value("${student.redis-key-prefix:student:profile:}")
    private String studentProfileKeyPrefix;

    @Value("${student.cache-ttl-hours:168}")
    private long studentProfileTtlHours;

    public AuthApiServiceImpl(
            BizStudentInfoService bizStudentInfoService,
            RedisStringClient redis,
            ObjectMapper objectMapper
    ) {
        this.bizStudentInfoService = bizStudentInfoService;
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

    @Override
    public Map<String, Object> login(String body) {
        log.info("登录请求收到, bodyLength={}", body == null ? 0 : body.length());
        String studentIdRaw = extractStudentId(body);
        Integer xh = normalizeStudentId(studentIdRaw);
        log.info("登录参数解析完成, studentIdRaw={}, normalizedXh={}", studentIdRaw, xh);

        BizStudentInfo student = bizStudentInfoService.getOne(new LambdaQueryWrapper<BizStudentInfo>()
                .eq(BizStudentInfo::getXh, xh)
                .last("limit 1"));
        if (student == null) {
            log.warn("登录失败, 原因=学生不存在, normalizedXh={}", xh);
            throw new ResponseStatusException(NOT_FOUND, "student_id 不存在");
        }

        try {
            BizStudentPortraitVO portrait = bizStudentInfoService.getStudentPortraitByXh(xh);
            String key = studentProfileKeyPrefix + xh;
            String portraitJson = StudentPortraitChineseJsonTranslator.toRedisJson(objectMapper, portrait);
            redis.set(key, portraitJson,
                    Duration.ofHours(Math.max(1, studentProfileTtlHours)));
            log.info("学生画像已写入 Redis, key={}, ttlHours={}", key, studentProfileTtlHours);
        } catch (Exception ex) {
            log.error("登录后写入学生画像到 Redis 失败, xh={}, reason={}", xh, ex.getMessage(), ex);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("success", true);
        result.put("student_id", String.valueOf(xh));
        result.put("name", student.getXm());
        result.put("message", "登录成功");
        log.info("登录成功, studentId={}, name={}", xh, student.getXm());
        return result;
    }

    private String extractStudentId(String body) {
        try {
            JsonNode root = objectMapper.readTree(body == null ? "{}" : body);
            return root.path("student_id").asText("").trim();
        } catch (Exception ex) {
            log.warn("登录请求解析失败, 原因=请求体不是合法 JSON", ex);
            throw new ResponseStatusException(BAD_REQUEST, "请求体必须是合法 JSON");
        }
    }

    private Integer normalizeStudentId(String studentIdRaw) {
        String cleaned = studentIdRaw == null ? "" : studentIdRaw.trim();
        if (cleaned.isEmpty()) {
            log.warn("登录参数校验失败, 原因=student_id 为空");
            throw new ResponseStatusException(BAD_REQUEST, "student_id 不能为空");
        }
        String upper = cleaned.toUpperCase();
        if (upper.startsWith("STU")) {
            cleaned = cleaned.substring(3).trim();
        }
        try {
            return Integer.valueOf(cleaned);
        } catch (NumberFormatException ex) {
            log.warn("登录参数校验失败, 原因=student_id 格式非法, studentIdRaw={}", studentIdRaw);
            throw new ResponseStatusException(BAD_REQUEST, "student_id 格式不正确");
        }
    }
}
