package org.example.server_job.student.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.example.server_job.biz.entity.BizStudentInfo;
import org.example.server_job.biz.service.BizStudentInfoService;
import org.example.server_job.biz.vo.BizStudentPortraitVO;
import org.example.server_job.client.redis.RedisStringClient;
import org.example.server_job.storage.MinioObjectStorageService;
import org.example.server_job.student.entity.StudentProfileExt;
import org.example.server_job.student.mapper.StudentProfileExtMapper;
import org.example.server_job.student.service.StudentProfileExtService;
import org.example.server_job.student.support.StudentProfileMergeSupport;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.NOT_FOUND;
import static org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE;

@Service
public class StudentProfileExtServiceImpl implements StudentProfileExtService {

    private static final int MAX_TAGS = 20;
    private static final int MAX_TAG_LEN = 20;
    private static final int MAX_QUERY_LEN = 2000;
    private static final Set<String> ALLOWED_IMAGE_TYPES = Set.of(
            "image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"
    );

    private final StudentProfileExtMapper profileExtMapper;
    private final BizStudentInfoService bizStudentInfoService;
    private final RedisStringClient redis;
    private final ObjectMapper objectMapper;
    private final MinioObjectStorageService objectStorage;

    @Value("${student.redis-key-prefix:student:profile:}")
    private String studentProfileKeyPrefix;

    public StudentProfileExtServiceImpl(
            StudentProfileExtMapper profileExtMapper,
            BizStudentInfoService bizStudentInfoService,
            RedisStringClient redis,
            ObjectMapper objectMapper,
            @Autowired(required = false) MinioObjectStorageService objectStorage
    ) {
        this.profileExtMapper = profileExtMapper;
        this.bizStudentInfoService = bizStudentInfoService;
        this.redis = redis;
        this.objectMapper = objectMapper;
        this.objectStorage = objectStorage;
    }

    @Override
    public Map<String, Object> getMergedProfile(String studentId) {
        String sid = normalizeStudentId(studentId);
        BizStudentPortraitVO portrait = loadPortrait(sid);
        StudentProfileExt ext = profileExtMapper.selectById(sid);
        ObjectNode merged = StudentProfileMergeSupport.merge(objectMapper, portrait, ext);
        Map<String, Object> out = new LinkedHashMap<>(StudentProfileMergeSupport.toApiMap(objectMapper, merged));
        out.put("student_id", sid);
        return out;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> updateProfile(String studentId, JsonNode body) {
        String sid = normalizeStudentId(studentId);
        BizStudentPortraitVO portrait = loadPortrait(sid);
        if (body == null || body.isMissingNode()) {
            throw new ResponseStatusException(BAD_REQUEST, "请求体不能为空");
        }

        StudentProfileExt ext = profileExtMapper.selectById(sid);
        if (ext == null) {
            ext = newExt(sid, portrait);
        }

        if (body.has("contact")) {
            applyContact(ext, body.get("contact"));
        }
        if (body.has("job_intent")) {
            JsonNode current = StudentProfileMergeSupport.readJobIntent(objectMapper, ext);
            ObjectNode merged = ((ObjectNode) current.deepCopy());
            applyJobIntent(merged, body.get("job_intent"));
            ext.setJobIntentJson(StudentProfileMergeSupport.writeJson(objectMapper, merged));
        }
        if (body.has("ability")) {
            JsonNode current = StudentProfileMergeSupport.readAbility(objectMapper, ext, portrait,
                    StudentProfileMergeSupport.readJobIntent(objectMapper, ext));
            ObjectNode merged = ((ObjectNode) current.deepCopy());
            applyAbility(merged, body.get("ability"), portrait);
            ext.setAbilityJson(StudentProfileMergeSupport.writeJson(objectMapper, merged));
        }

        ext.setUpdatedAt(LocalDateTime.now());
        if (profileExtMapper.selectById(sid) == null) {
            ext.setCreatedAt(LocalDateTime.now());
            profileExtMapper.insert(ext);
        } else {
            profileExtMapper.updateById(ext);
        }

        invalidatePortraitCache(sid, portrait);
        return getMergedProfile(sid);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> uploadAvatar(String studentId, MultipartFile file) {
        if (objectStorage == null) {
            throw new ResponseStatusException(SERVICE_UNAVAILABLE, "对象存储未启用，无法上传头像");
        }
        String sid = normalizeStudentId(studentId);
        BizStudentPortraitVO portrait = loadPortrait(sid);
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(BAD_REQUEST, "请选择头像文件");
        }
        String contentType = file.getContentType();
        if (!StringUtils.hasText(contentType) || !ALLOWED_IMAGE_TYPES.contains(contentType.toLowerCase())) {
            throw new ResponseStatusException(BAD_REQUEST, "仅支持 JPG / PNG / WebP / GIF 图片");
        }
        String publicUrl;
        try {
            publicUrl = objectStorage.uploadAvatar(
                    sid,
                    file.getInputStream(),
                    file.getSize(),
                    contentType,
                    file.getOriginalFilename()
            );
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new ResponseStatusException(BAD_REQUEST, "读取头像文件失败");
        }

        StudentProfileExt ext = profileExtMapper.selectById(sid);
        if (ext == null) {
            ext = newExt(sid, portrait);
        }
        ext.setAvatarUrl(publicUrl);
        ext.setUpdatedAt(LocalDateTime.now());
        if (profileExtMapper.selectById(sid) == null) {
            ext.setCreatedAt(LocalDateTime.now());
            profileExtMapper.insert(ext);
        } else {
            profileExtMapper.updateById(ext);
        }
        invalidatePortraitCache(sid, portrait);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("student_id", sid);
        out.put("avatar_url", publicUrl);
        out.put("profile", getMergedProfile(sid));
        return out;
    }

    private StudentProfileExt newExt(String sid, BizStudentPortraitVO portrait) {
        StudentProfileExt ext = new StudentProfileExt();
        ext.setStudentId(sid);
        ext.setJobIntentJson(StudentProfileMergeSupport.writeJson(
                objectMapper, StudentProfileMergeSupport.defaultJobIntent(objectMapper)
        ));
        ext.setAbilityJson(StudentProfileMergeSupport.writeJson(
                objectMapper, StudentProfileMergeSupport.defaultAbility(objectMapper, portrait)
        ));
        return ext;
    }

    private void applyContact(StudentProfileExt ext, JsonNode contact) {
        if (contact == null || contact.isMissingNode()) {
            return;
        }
        if (contact.has("phone")) {
            ext.setPhone(trimOrNull(contact.path("phone").asText(null)));
        }
        if (contact.has("email")) {
            ext.setEmail(trimOrNull(contact.path("email").asText(null)));
        }
        if (contact.has("campus_experience")) {
            ext.setCampusExperience(trimOrNull(contact.path("campus_experience").asText(null)));
        }
        if (contact.has("avatar_url")) {
            ext.setAvatarUrl(trimOrNull(contact.path("avatar_url").asText(null)));
        }
    }

    private void applyJobIntent(ObjectNode target, JsonNode patch) {
        if (patch == null || patch.isMissingNode()) {
            return;
        }
        if (patch.has("targetRoles")) {
            target.set("targetRoles", readStringArray(patch.get("targetRoles"), MAX_TAGS, MAX_TAG_LEN));
        }
        if (patch.has("targetCities")) {
            target.set("targetCities", readStringArray(patch.get("targetCities"), 10, 20));
        }
        if (patch.has("targetCompanies")) {
            target.set("targetCompanies", readStringArray(patch.get("targetCompanies"), 10, 40));
        }
        if (patch.has("salaryMin")) {
            target.set("salaryMin", readSalaryNode(patch.get("salaryMin")));
        }
        if (patch.has("salaryMax")) {
            target.set("salaryMax", readSalaryNode(patch.get("salaryMax")));
        }
        if (patch.has("salaryNegotiable")) {
            target.put("salaryNegotiable", patch.path("salaryNegotiable").asBoolean(true));
        }
        if (patch.has("queryText")) {
            String q = patch.path("queryText").asText("").trim();
            target.put("queryText", q.length() <= MAX_QUERY_LEN ? q : q.substring(0, MAX_QUERY_LEN));
        }
    }

    private void applyAbility(ObjectNode target, JsonNode patch, BizStudentPortraitVO portrait) {
        if (patch == null || patch.isMissingNode()) {
            return;
        }
        if (patch.has("tags")) {
            target.set("tags", readStringArray(patch.get("tags"), MAX_TAGS, MAX_TAG_LEN));
        }
        if (patch.has("radar")) {
            JsonNode radarPatch = patch.get("radar");
            ObjectNode radar = target.has("radar") && target.get("radar").isObject()
                    ? (ObjectNode) target.get("radar").deepCopy()
                    : StudentProfileMergeSupport.computeDefaultRadar(objectMapper, portrait);
            for (String key : List.of("professional", "communication", "office", "comprehensive", "practice")) {
                if (radarPatch.has(key)) {
                    radar.put(key, clampRadar(radarPatch.path(key).asInt(0)));
                }
            }
            target.set("radar", radar);
            target.put("radarSource", "manual");
        }
        if (patch.has("radarSource")) {
            target.put("radarSource", patch.path("radarSource").asText("manual"));
        }
    }

    private ArrayNode readStringArray(JsonNode node, int maxCount, int maxLen) {
        ArrayNode arr = objectMapper.createArrayNode();
        if (node == null || !node.isArray()) {
            return arr;
        }
        int count = 0;
        for (JsonNode item : node) {
            if (count >= maxCount) {
                break;
            }
            String s = item.asText("").trim();
            if (s.isEmpty()) {
                continue;
            }
            arr.add(s.length() <= maxLen ? s : s.substring(0, maxLen));
            count++;
        }
        return arr;
    }

    private JsonNode readSalaryNode(JsonNode node) {
        if (node == null || node.isNull()) {
            return objectMapper.nullNode();
        }
        int v = node.asInt(-1);
        if (v < 0) {
            return objectMapper.nullNode();
        }
        return objectMapper.getNodeFactory().numberNode(Math.min(999999, v));
    }

    private static int clampRadar(int v) {
        return Math.max(0, Math.min(100, v));
    }

    private BizStudentPortraitVO loadPortrait(String sid) {
        Integer xh = Integer.valueOf(sid);
        BizStudentPortraitVO portrait = bizStudentInfoService.getStudentPortraitByXh(xh);
        if (portrait.getStudentInfo() == null) {
            throw new ResponseStatusException(NOT_FOUND, "学生不存在");
        }
        return portrait;
    }

    private void invalidatePortraitCache(String sid, BizStudentPortraitVO portrait) {
        try {
            StudentProfileExt ext = profileExtMapper.selectById(sid);
            ObjectNode merged = StudentProfileMergeSupport.merge(objectMapper, portrait, ext);
            String key = studentProfileKeyPrefix + sid;
            redis.set(key, objectMapper.writeValueAsString(StudentProfileMergeSupport.toApiMap(objectMapper, merged)));
        } catch (Exception ignored) {
            redis.delete(studentProfileKeyPrefix + sid);
        }
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

    private static String trimOrNull(String value) {
        if (value == null) {
            return null;
        }
        String t = value.trim();
        return t.isEmpty() ? null : t;
    }
}
