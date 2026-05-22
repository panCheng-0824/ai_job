package org.example.server_job.student.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.student.entity.StudentResume;
import org.example.server_job.student.mapper.StudentResumeMapper;
import org.example.server_job.student.service.StudentResumeService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.FORBIDDEN;
import static org.springframework.http.HttpStatus.NOT_FOUND;

@Service
public class StudentResumeServiceImpl implements StudentResumeService {

    private static final ZoneId ZONE = ZoneId.systemDefault();

    private final StudentResumeMapper studentResumeMapper;
    private final BizStudentInfoService bizStudentInfoService;
    private final ObjectMapper objectMapper;

    public StudentResumeServiceImpl(
            StudentResumeMapper studentResumeMapper,
            BizStudentInfoService bizStudentInfoService,
            ObjectMapper objectMapper
    ) {
        this.studentResumeMapper = studentResumeMapper;
        this.bizStudentInfoService = bizStudentInfoService;
        this.objectMapper = objectMapper;
    }

    @Override
    public Map<String, Object> listStore(String studentId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        repairDefaultsIfMissing(sid);
        List<StudentResume> rows = studentResumeMapper.selectList(
                Wrappers.<StudentResume>lambdaQuery()
                        .eq(StudentResume::getStudentId, sid)
                        .orderByDesc(StudentResume::getUpdatedAt)
        );
        String defaultResumeId = rows.stream()
                .filter(r -> Boolean.TRUE.equals(r.getIsDefault()))
                .map(StudentResume::getId)
                .findFirst()
                .orElse(null);
        List<Map<String, Object>> resumes = new ArrayList<>();
        for (StudentResume r : rows) {
            resumes.add(toApiRecord(r));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("defaultResumeId", defaultResumeId);
        out.put("resumes", resumes);
        return out;
    }

    @Override
    public Map<String, Object> get(String studentId, String resumeId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        if (resumeId == null || resumeId.isBlank()) {
            throw new ResponseStatusException(BAD_REQUEST, "resume_id 不能为空");
        }
        StudentResume r = studentResumeMapper.selectById(resumeId);
        if (r == null || !sid.equals(r.getStudentId())) {
            throw new ResponseStatusException(NOT_FOUND, "简历不存在");
        }
        return toApiRecord(r);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> upsert(String studentId, String resumeId, JsonNode body) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        if (resumeId == null || resumeId.isBlank()) {
            throw new ResponseStatusException(BAD_REQUEST, "resume_id 不能为空");
        }
        JsonNode contentNode = body.get("content");
        if (contentNode == null || contentNode.isNull() || !contentNode.isObject()) {
            throw new ResponseStatusException(BAD_REQUEST, "content 必须为对象");
        }
        final String contentJson;
        try {
            contentJson = objectMapper.writeValueAsString(contentNode);
        } catch (JsonProcessingException e) {
            throw new ResponseStatusException(BAD_REQUEST, "content 无法序列化");
        }
        String templateId = body.path("templateId").asText("");
        String displayName = body.path("displayName").asText("").trim();
        if (displayName.isEmpty()) {
            throw new ResponseStatusException(BAD_REQUEST, "displayName 不能为空");
        }
        boolean setGlobalDefault = body.path("setGlobalDefault").asBoolean(false);
        boolean setSeriesDefault = !body.has("setSeriesDefault") || body.path("setSeriesDefault").asBoolean(true);
        String seriesIdBody = body.path("seriesId").asText("").trim();
        String resolvedSeries = seriesIdBody.isEmpty() ? resumeId : seriesIdBody;
        assertSeriesConsistent(sid, resolvedSeries);

        StudentResume existing = studentResumeMapper.selectById(resumeId);
        if (existing != null && !sid.equals(existing.getStudentId())) {
            throw new ResponseStatusException(FORBIDDEN, "无权操作该简历");
        }

        LocalDateTime now = LocalDateTime.now().truncatedTo(ChronoUnit.MILLIS);

        if (existing == null) {
            StudentResume ins = new StudentResume();
            ins.setId(resumeId);
            ins.setStudentId(sid);
            ins.setSeriesId(resolvedSeries);
            ins.setTemplateId(templateId);
            ins.setDisplayName(displayName);
            ins.setContentJson(contentJson);
            ins.setIsSeriesDefault(setSeriesDefault);
            ins.setIsDefault(false);
            long createdMs = body.path("createdAt").asLong(0);
            if (createdMs > 0) {
                ins.setCreatedAt(LocalDateTime.ofInstant(Instant.ofEpochMilli(createdMs), ZONE));
            } else {
                ins.setCreatedAt(now);
            }
            ins.setUpdatedAt(now);
            studentResumeMapper.insert(ins);
            if (setSeriesDefault) {
                clearSeriesDefaultExcept(sid, resolvedSeries, resumeId);
            }
            applyGlobalDefaultOnSave(sid, resumeId, setGlobalDefault);
        } else {
            String series = existing.getSeriesId() != null && !existing.getSeriesId().isBlank()
                    ? existing.getSeriesId() : resolvedSeries;
            existing.setTemplateId(templateId);
            existing.setDisplayName(displayName);
            existing.setContentJson(contentJson);
            existing.setUpdatedAt(now);
            if (setSeriesDefault) {
                existing.setIsSeriesDefault(true);
                clearSeriesDefaultExcept(sid, series, resumeId);
            }
            studentResumeMapper.updateById(existing);
            applyGlobalDefaultOnSave(sid, resumeId, setGlobalDefault);
        }

        repairDefaultsIfMissing(sid);
        return listStore(sid);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> delete(String studentId, String resumeId) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        StudentResume r = studentResumeMapper.selectById(resumeId);
        if (r == null || !sid.equals(r.getStudentId())) {
            throw new ResponseStatusException(NOT_FOUND, "简历不存在");
        }
        String series = r.getSeriesId();
        studentResumeMapper.deleteById(resumeId);
        repairDefaultsIfMissing(sid);
        if (series != null && !series.isBlank()) {
            repairSeriesDefaultForSeries(sid, series);
        }
        return listStore(sid);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> setDefault(String studentId, String resumeId, String scope) {
        String sid = normalizeStudentId(studentId);
        ensureStudent(sid);
        StudentResume r = studentResumeMapper.selectById(resumeId);
        if (r == null || !sid.equals(r.getStudentId())) {
            throw new ResponseStatusException(NOT_FOUND, "简历不存在");
        }
        String normalizedScope = scope == null ? "series" : scope.trim().toLowerCase();
        if ("global".equals(normalizedScope)) {
            clearGlobalDefaultExcept(sid, resumeId);
            String series = r.getSeriesId() != null && !r.getSeriesId().isBlank() ? r.getSeriesId() : resumeId;
            clearSeriesDefaultExcept(sid, series, resumeId);
        } else if ("series".equals(normalizedScope)) {
            String series = r.getSeriesId() != null && !r.getSeriesId().isBlank() ? r.getSeriesId() : resumeId;
            clearSeriesDefaultExcept(sid, series, resumeId);
        } else {
            throw new ResponseStatusException(BAD_REQUEST, "scope 须为 series 或 global");
        }
        return listStore(sid);
    }

    /** 保存时：显式要求设为全局默认，或学号下尚无任何全局默认时自动设定。 */
    private void applyGlobalDefaultOnSave(String studentId, String resumeId, boolean explicitGlobal) {
        long globalCount = studentResumeMapper.selectCount(
                Wrappers.<StudentResume>lambdaQuery()
                        .eq(StudentResume::getStudentId, studentId)
                        .eq(StudentResume::getIsDefault, true)
        );
        if (explicitGlobal || globalCount == 0) {
            clearGlobalDefaultExcept(studentId, resumeId);
        }
    }

    private void clearGlobalDefaultExcept(String studentId, String keepResumeId) {
        studentResumeMapper.update(
                null,
                Wrappers.<StudentResume>lambdaUpdate()
                        .eq(StudentResume::getStudentId, studentId)
                        .ne(StudentResume::getId, keepResumeId)
                        .set(StudentResume::getIsDefault, false)
        );
        studentResumeMapper.update(
                null,
                Wrappers.<StudentResume>lambdaUpdate()
                        .eq(StudentResume::getId, keepResumeId)
                        .set(StudentResume::getIsDefault, true)
        );
    }

    private void clearSeriesDefaultExcept(String studentId, String seriesId, String keepResumeId) {
        studentResumeMapper.update(
                null,
                Wrappers.<StudentResume>lambdaUpdate()
                        .eq(StudentResume::getStudentId, studentId)
                        .eq(StudentResume::getSeriesId, seriesId)
                        .ne(StudentResume::getId, keepResumeId)
                        .set(StudentResume::getIsSeriesDefault, false)
        );
        studentResumeMapper.update(
                null,
                Wrappers.<StudentResume>lambdaUpdate()
                        .eq(StudentResume::getId, keepResumeId)
                        .set(StudentResume::getIsSeriesDefault, true)
        );
    }

    private void repairDefaultsIfMissing(String studentId) {
        repairGlobalDefaultIfMissing(studentId);
        List<StudentResume> rows = studentResumeMapper.selectList(
                Wrappers.<StudentResume>lambdaQuery().eq(StudentResume::getStudentId, studentId)
        );
        Set<String> seriesIds = new LinkedHashSet<>();
        for (StudentResume r : rows) {
            String ser = r.getSeriesId() != null && !r.getSeriesId().isBlank() ? r.getSeriesId() : r.getId();
            seriesIds.add(ser);
        }
        for (String ser : seriesIds) {
            repairSeriesDefaultForSeries(studentId, ser);
        }
    }

    private void repairGlobalDefaultIfMissing(String studentId) {
        long total = studentResumeMapper.selectCount(
                Wrappers.<StudentResume>lambdaQuery().eq(StudentResume::getStudentId, studentId)
        );
        if (total == 0) {
            return;
        }
        long def = studentResumeMapper.selectCount(
                Wrappers.<StudentResume>lambdaQuery()
                        .eq(StudentResume::getStudentId, studentId)
                        .eq(StudentResume::getIsDefault, true)
        );
        if (def > 0) {
            return;
        }
        List<StudentResume> newest = studentResumeMapper.selectList(
                Wrappers.<StudentResume>lambdaQuery()
                        .eq(StudentResume::getStudentId, studentId)
                        .orderByDesc(StudentResume::getUpdatedAt)
                        .last("LIMIT 1")
        );
        if (!newest.isEmpty()) {
            clearGlobalDefaultExcept(studentId, newest.get(0).getId());
        }
    }

    private void repairSeriesDefaultForSeries(String studentId, String seriesId) {
        long total = studentResumeMapper.selectCount(
                Wrappers.<StudentResume>lambdaQuery()
                        .eq(StudentResume::getStudentId, studentId)
                        .eq(StudentResume::getSeriesId, seriesId)
        );
        if (total == 0) {
            return;
        }
        long def = studentResumeMapper.selectCount(
                Wrappers.<StudentResume>lambdaQuery()
                        .eq(StudentResume::getStudentId, studentId)
                        .eq(StudentResume::getSeriesId, seriesId)
                        .eq(StudentResume::getIsSeriesDefault, true)
        );
        if (def > 0) {
            return;
        }
        List<StudentResume> newest = studentResumeMapper.selectList(
                Wrappers.<StudentResume>lambdaQuery()
                        .eq(StudentResume::getStudentId, studentId)
                        .eq(StudentResume::getSeriesId, seriesId)
                        .orderByDesc(StudentResume::getUpdatedAt)
                        .last("LIMIT 1")
        );
        if (!newest.isEmpty()) {
            clearSeriesDefaultExcept(studentId, seriesId, newest.get(0).getId());
        }
    }

    private void assertSeriesConsistent(String studentId, String seriesId) {
        if (seriesId == null || seriesId.isBlank()) {
            return;
        }
        StudentResume any = studentResumeMapper.selectOne(
                Wrappers.<StudentResume>lambdaQuery()
                        .eq(StudentResume::getSeriesId, seriesId)
                        .last("LIMIT 1")
        );
        if (any != null && !studentId.equals(any.getStudentId())) {
            throw new ResponseStatusException(FORBIDDEN, "无权使用该简历分组");
        }
    }

    private Map<String, Object> parseContentMap(String contentJson) {
        try {
            if (contentJson == null || contentJson.isBlank()) {
                return new LinkedHashMap<>();
            }
            return objectMapper.readValue(contentJson, new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            return new LinkedHashMap<>();
        }
    }

    private Map<String, Object> toApiRecord(StudentResume r) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", r.getId());
        String ser = r.getSeriesId() != null && !r.getSeriesId().isBlank() ? r.getSeriesId() : r.getId();
        m.put("seriesId", ser);
        m.put("templateId", r.getTemplateId() != null ? r.getTemplateId() : "");
        m.put("displayName", r.getDisplayName() != null ? r.getDisplayName() : "");
        m.put("content", parseContentMap(r.getContentJson()));
        m.put("createdAt", toEpochMilli(r.getCreatedAt()));
        m.put("updatedAt", toEpochMilli(r.getUpdatedAt()));
        m.put("isDefault", Boolean.TRUE.equals(r.getIsDefault()));
        m.put("isSeriesDefault", Boolean.TRUE.equals(r.getIsSeriesDefault()));
        return m;
    }

    private long toEpochMilli(LocalDateTime t) {
        if (t == null) {
            return 0L;
        }
        return t.atZone(ZONE).toInstant().toEpochMilli();
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

    private void ensureStudent(String canonicalStudentId) {
        Integer xh = Integer.valueOf(canonicalStudentId);
        BizStudentInfo one = bizStudentInfoService.getOne(Wrappers.<BizStudentInfo>lambdaQuery()
                .eq(BizStudentInfo::getXh, xh)
                .last("LIMIT 1"));
        if (one == null) {
            throw new ResponseStatusException(NOT_FOUND, "学生不存在");
        }
    }
}
