package org.example.server_job.student.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.student.entity.StudentJobMatchHistory;
import org.example.server_job.student.mapper.StudentJobMatchHistoryMapper;
import org.example.server_job.student.service.StudentJobMatchHistoryService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.NOT_FOUND;

/**
 * 学生智能匹配历史持久化：保存完整匹配快照，按时间维护最近 5 条。
 */
@Service
public class StudentJobMatchHistoryServiceImpl implements StudentJobMatchHistoryService {

    private static final int MAX_HISTORY = 5;
    private static final DateTimeFormatter ISO_TS = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    private final StudentJobMatchHistoryMapper historyMapper;
    private final BizStudentInfoService bizStudentInfoService;
    private final ObjectMapper objectMapper;

    public StudentJobMatchHistoryServiceImpl(
            StudentJobMatchHistoryMapper historyMapper,
            BizStudentInfoService bizStudentInfoService,
            ObjectMapper objectMapper
    ) {
        this.historyMapper = historyMapper;
        this.bizStudentInfoService = bizStudentInfoService;
        this.objectMapper = objectMapper;
    }

    @Override
    public Map<String, Object> listHistory(String studentId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        List<StudentJobMatchHistory> rows = historyMapper.selectList(
                Wrappers.<StudentJobMatchHistory>lambdaQuery()
                        .eq(StudentJobMatchHistory::getStudentId, sid)
                        .orderByDesc(StudentJobMatchHistory::getCreatedAt)
                        .last("LIMIT " + MAX_HISTORY)
        );
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudentJobMatchHistory row : rows) {
            items.add(toApiRecord(row));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("items", items);
        out.put("max_count", MAX_HISTORY);
        return out;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> saveHistory(String studentId, JsonNode body) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        if (body == null || body.isMissingNode()) {
            throw new ResponseStatusException(BAD_REQUEST, "请求体不能为空");
        }

        String queryText = body.path("query").asText("").trim();
        if (queryText.isEmpty()) {
            queryText = body.path("query_text").asText("").trim();
        }
        if (queryText.isEmpty()) {
            throw new ResponseStatusException(BAD_REQUEST, "query 不能为空");
        }

        JsonNode jobsNode = body.get("jobs");
        if (jobsNode == null || !jobsNode.isArray() || jobsNode.isEmpty()) {
            throw new ResponseStatusException(BAD_REQUEST, "jobs 不能为空（需至少返回一个岗位）");
        }

        JsonNode settingsNode = body.get("settings");
        if (settingsNode == null || settingsNode.isMissingNode() || settingsNode.isNull()) {
            settingsNode = objectMapper.createObjectNode();
        }
        JsonNode recommendationNode = body.get("recommendation");

        StudentJobMatchHistory row = new StudentJobMatchHistory();
        row.setStudentId(sid);
        row.setQueryText(truncate(queryText, 2000));
        row.setSettingsJson(writeJson(settingsNode));
        row.setJobsJson(writeJson(jobsNode));
        row.setRecommendationJson(
                recommendationNode == null || recommendationNode.isNull()
                        ? null
                        : writeJson(recommendationNode)
        );
        row.setJobCount(jobsNode.size());
        row.setCreatedAt(LocalDateTime.now());
        historyMapper.insert(row);

        trimOldestBeyondLimit(sid);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("saved", true);
        out.put("record", toApiRecord(
                historyMapper.selectById(row.getId())
        ));
        out.put("items", listHistory(sid).get("items"));
        return out;
    }

    /** 超过上限时按 created_at 升序删除最旧记录 */
    private void trimOldestBeyondLimit(String studentId) {
        List<StudentJobMatchHistory> all = historyMapper.selectList(
                Wrappers.<StudentJobMatchHistory>lambdaQuery()
                        .eq(StudentJobMatchHistory::getStudentId, studentId)
                        .orderByAsc(StudentJobMatchHistory::getCreatedAt)
        );
        int excess = all.size() - MAX_HISTORY;
        for (int i = 0; i < excess; i++) {
            historyMapper.deleteById(all.get(i).getId());
        }
    }

    private Map<String, Object> toApiRecord(StudentJobMatchHistory row) {
        if (row == null) {
            return Map.of();
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", row.getId());
        out.put("student_id", row.getStudentId());
        out.put("query", row.getQueryText());
        out.put("query_text", row.getQueryText());
        out.put("job_count", row.getJobCount() != null ? row.getJobCount() : 0);
        if (row.getCreatedAt() != null) {
            out.put("created_at", ISO_TS.format(row.getCreatedAt()));
        }
        out.put("settings", readJsonObject(row.getSettingsJson()));
        out.put("jobs", readJsonArray(row.getJobsJson()));
        out.put("recommendation", readJsonObject(row.getRecommendationJson()));
        return out;
    }

    private Object readJsonObject(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(raw, Object.class);
        } catch (JsonProcessingException e) {
            return Map.of("raw", raw);
        }
    }

    private List<Object> readJsonArray(String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(
                    raw,
                    objectMapper.getTypeFactory().constructCollectionType(List.class, Object.class)
            );
        } catch (JsonProcessingException e) {
            return List.of();
        }
    }

    private String writeJson(JsonNode node) {
        try {
            return objectMapper.writeValueAsString(node);
        } catch (JsonProcessingException e) {
            throw new ResponseStatusException(BAD_REQUEST, "JSON 序列化失败");
        }
    }

    private static String truncate(String text, int max) {
        if (text == null) {
            return "";
        }
        return text.length() <= max ? text : text.substring(0, max);
    }

    private String normalizeStudentId(String raw) {
        if (raw == null || raw.isBlank()) {
            throw new ResponseStatusException(BAD_REQUEST, "student_id 不能为空");
        }
        String cleaned = raw.trim();
        String upper = cleaned.toUpperCase();
        if (upper.startsWith("STU")) {
            cleaned = cleaned.substring(3).trim();
        }
        try {
            return String.valueOf(Integer.parseInt(cleaned));
        } catch (NumberFormatException e) {
            throw new ResponseStatusException(BAD_REQUEST, "student_id 格式不正确");
        }
    }

    private void ensureStudent(String studentId) {
        Integer xh = Integer.valueOf(studentId);
        BizStudentInfo one = bizStudentInfoService.getOne(
                Wrappers.<BizStudentInfo>lambdaQuery()
                        .eq(BizStudentInfo::getXh, xh)
                        .last("limit 1")
        );
        if (one == null) {
            throw new ResponseStatusException(NOT_FOUND, "学生不存在");
        }
    }
}
