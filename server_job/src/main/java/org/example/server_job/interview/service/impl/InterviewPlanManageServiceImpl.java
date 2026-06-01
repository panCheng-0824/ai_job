package org.example.server_job.interview.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.interview.dto.InterviewPlanSaveRequest;
import org.example.server_job.interview.entity.InterviewIndustryCategoryEntity;
import org.example.server_job.interview.entity.InterviewPlanBasicsEntity;
import org.example.server_job.interview.entity.InterviewPlanModuleTagEntity;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;
import org.example.server_job.interview.mapper.InterviewIndustryCategoryMapper;
import org.example.server_job.interview.mapper.InterviewPlanBasicsMapper;
import org.example.server_job.interview.mapper.InterviewPlanModuleTagMapper;
import org.example.server_job.interview.mapper.InterviewPlanQuestionMapper;
import org.example.server_job.interview.service.InterviewPlanManageService;
import org.example.server_job.interview.support.InterviewIds;
import org.example.server_job.interview.support.InterviewPlanQuestionExtrasSupport;
import org.example.server_job.interview.support.InterviewPlanWriteSupport;
import org.example.server_job.interview.support.InterviewPlanWriteValidator;
import org.example.server_job.interview.support.InterviewRequestValidator;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 大纲列表、详情与 CRUD（读/写 V2 表）。
 */
@Service
public class InterviewPlanManageServiceImpl implements InterviewPlanManageService {

    private final InterviewPlanBasicsMapper basicsMapper;
    private final InterviewPlanModuleTagMapper tagMapper;
    private final InterviewPlanQuestionMapper questionMapper;
    private final InterviewIndustryCategoryMapper industryMapper;
    private final InterviewPlanWriteValidator writeValidator;
    private final InterviewPlanWriteSupport writeSupport;
    private final InterviewPlanQuestionExtrasSupport questionExtrasSupport;

    public InterviewPlanManageServiceImpl(
            InterviewPlanBasicsMapper basicsMapper,
            InterviewPlanModuleTagMapper tagMapper,
            InterviewPlanQuestionMapper questionMapper,
            InterviewIndustryCategoryMapper industryMapper,
            InterviewPlanWriteValidator writeValidator,
            InterviewPlanWriteSupport writeSupport,
            InterviewPlanQuestionExtrasSupport questionExtrasSupport
    ) {
        this.basicsMapper = basicsMapper;
        this.tagMapper = tagMapper;
        this.questionMapper = questionMapper;
        this.industryMapper = industryMapper;
        this.writeValidator = writeValidator;
        this.writeSupport = writeSupport;
        this.questionExtrasSupport = questionExtrasSupport;
    }

    @Override
    public Map<String, Object> listByStudent(String studentId, String status, String industryCategoryId) {
        String sid = InterviewRequestValidator.requireStudentId(studentId);
        var query = Wrappers.<InterviewPlanBasicsEntity>lambdaQuery()
                .eq(InterviewPlanBasicsEntity::getStudentId, sid)
                .orderByDesc(InterviewPlanBasicsEntity::getCreatedAt);
        if (status != null && !status.isBlank()) {
            query.eq(InterviewPlanBasicsEntity::getStatus, status.trim());
        }
        if (industryCategoryId != null && !industryCategoryId.isBlank()) {
            applyIndustryFilter(query, industryCategoryId.trim());
        }
        List<InterviewPlanBasicsEntity> rows = basicsMapper.selectList(query);
        List<InterviewPlanBasicsEntity> latestRows = keepLatestVersionPerPlan(rows);
        List<Map<String, Object>> items = new ArrayList<>();
        for (InterviewPlanBasicsEntity row : latestRows) {
            items.add(toListItem(row));
        }
        return Map.of("student_id", sid, "items", items, "count", items.size());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> create(InterviewPlanSaveRequest request, String studentIdQuery) {
        String sid = InterviewRequestValidator.requireStudentId(request.studentId(), studentIdQuery);
        writeValidator.validateSave(request, true);
        String planId = request.planId() != null && !request.planId().isBlank()
                ? request.planId().trim()
                : InterviewIds.newPlanId();
        InterviewPlanBasicsEntity row = writeSupport.insertPlanVersion(sid, planId, 1, request);
        return Map.of(
                "plan_id", row.getPlanId(),
                "version", row.getVersion(),
                "plan_row_id", row.getPlanRowId(),
                "item", toListItem(row)
        );
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> revise(String planId, InterviewPlanSaveRequest request, String studentIdQuery) {
        String sid = InterviewRequestValidator.requireStudentId(request.studentId(), studentIdQuery);
        InterviewPlanBasicsEntity latest = writeValidator.requireOwnedPlan(sid, planId);
        writeValidator.validateSave(request, false);
        int nextVersion = latest.getVersion() + 1;
        InterviewPlanSaveRequest merged = mergeIndustryForRevise(request, latest);
        InterviewPlanBasicsEntity row = writeSupport.insertPlanVersion(sid, planId, nextVersion, merged);
        return Map.of(
                "plan_id", row.getPlanId(),
                "version", row.getVersion(),
                "plan_row_id", row.getPlanRowId(),
                "item", toListItem(row)
        );
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> delete(String studentId, String planId) {
        String sid = InterviewRequestValidator.requireStudentId(studentId);
        writeValidator.requireOwnedPlan(sid, planId);
        writeValidator.ensureCanDelete(planId);
        writeSupport.deletePlanAllVersions(planId);
        return Map.of("deleted", true, "plan_id", planId);
    }

    private static InterviewPlanSaveRequest mergeIndustryForRevise(
            InterviewPlanSaveRequest request,
            InterviewPlanBasicsEntity latest
    ) {
        String industryId = request.industryCategoryId() != null && !request.industryCategoryId().isBlank()
                ? request.industryCategoryId()
                : latest.getIndustryCategoryId();
        return new InterviewPlanSaveRequest(
                request.studentId(),
                industryId,
                request.planId(),
                request.title(),
                request.targetRole(),
                request.introduction(),
                request.suitableAudience(),
                request.status(),
                request.moduleTags(),
                request.questions()
        );
    }

    @Override
    public Map<String, Object> getDetail(String studentId, String planId, Integer version) {
        String sid = InterviewRequestValidator.requireStudentId(studentId);
        if (planId == null || planId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "plan_id 不能为空");
        }
        InterviewPlanBasicsEntity basics = findBasics(planId, version);
        if (!sid.equals(basics.getStudentId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该大纲");
        }
        Map<String, Object> out = new LinkedHashMap<>(toListItem(basics));
        out.put("introduction", basics.getIntroduction());
        out.put("suitable_audience", basics.getSuitableAudience());
        out.put("module_tags", loadTags(basics.getPlanRowId()));
        out.put("questions", loadQuestions(basics.getPlanRowId()));
        List<Map<String, Object>> versions = loadVersionOptions(sid, planId, basics.getVersion());
        out.put("versions", versions);
        out.put("latest_version", resolveLatestVersion(versions));
        return out;
    }

    private void applyIndustryFilter(
            com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<InterviewPlanBasicsEntity> query,
            String industryCategoryId
    ) {
        InterviewIndustryCategoryEntity cat = industryMapper.selectById(industryCategoryId);
        if (cat != null && cat.getLevel() != null && cat.getLevel() == 1) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请使用二级行业分类筛选大纲");
        }
        writeValidator.requireLevel2Industry(industryCategoryId);
        query.eq(InterviewPlanBasicsEntity::getIndustryCategoryId, industryCategoryId);
    }

    private List<InterviewPlanBasicsEntity> keepLatestVersionPerPlan(List<InterviewPlanBasicsEntity> rows) {
        Map<String, InterviewPlanBasicsEntity> latest = new LinkedHashMap<>();
        for (InterviewPlanBasicsEntity row : rows) {
            String pid = row.getPlanId();
            InterviewPlanBasicsEntity existing = latest.get(pid);
            if (existing == null || row.getVersion() > existing.getVersion()) {
                latest.put(pid, row);
            }
        }
        return new ArrayList<>(latest.values());
    }

    private InterviewPlanBasicsEntity findBasics(String planId, Integer version) {
        if (version != null && version > 0) {
            InterviewPlanBasicsEntity row = basicsMapper.selectById(InterviewIds.planRowId(planId, version));
            if (row != null) {
                return row;
            }
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "大纲版本不存在");
        }
        List<InterviewPlanBasicsEntity> latest = basicsMapper.selectList(
                Wrappers.<InterviewPlanBasicsEntity>lambdaQuery()
                        .eq(InterviewPlanBasicsEntity::getPlanId, planId)
                        .orderByDesc(InterviewPlanBasicsEntity::getVersion)
                        .last("LIMIT 1")
        );
        if (latest.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "大纲不存在");
        }
        return latest.get(0);
    }

    /**
     * 加载同一 plan_id 下全部版本摘要，供详情页版本切换。
     */
    private List<Map<String, Object>> loadVersionOptions(String studentId, String planId, int currentVersion) {
        List<InterviewPlanBasicsEntity> rows = basicsMapper.selectList(
                Wrappers.<InterviewPlanBasicsEntity>lambdaQuery()
                        .eq(InterviewPlanBasicsEntity::getPlanId, planId)
                        .eq(InterviewPlanBasicsEntity::getStudentId, studentId)
                        .orderByDesc(InterviewPlanBasicsEntity::getVersion)
        );
        int latestVersion = rows.isEmpty() ? currentVersion : rows.get(0).getVersion();
        List<Map<String, Object>> versions = new ArrayList<>();
        for (InterviewPlanBasicsEntity row : rows) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("version", row.getVersion());
            item.put("status", row.getStatus());
            item.put("question_count", row.getQuestionCount());
            item.put("created_at", row.getCreatedAt());
            item.put("is_latest", row.getVersion() != null && row.getVersion().equals(latestVersion));
            item.put("is_current", row.getVersion() != null && row.getVersion() == currentVersion);
            versions.add(item);
        }
        return versions;
    }

    private static Integer resolveLatestVersion(List<Map<String, Object>> versions) {
        if (versions == null || versions.isEmpty()) {
            return null;
        }
        Object v = versions.get(0).get("version");
        return v instanceof Number n ? n.intValue() : null;
    }

    private Map<String, Object> toListItem(InterviewPlanBasicsEntity row) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("plan_row_id", row.getPlanRowId());
        m.put("plan_id", row.getPlanId());
        m.put("version", row.getVersion());
        m.put("title", row.getTitle());
        m.put("target_role", row.getTargetRole());
        m.put("industry_category_id", row.getIndustryCategoryId());
        m.put("industry_label", resolveIndustryLabel(row.getIndustryCategoryId()));
        m.put("question_count", row.getQuestionCount());
        m.put("status", row.getStatus());
        m.put("created_at", row.getCreatedAt());
        return m;
    }

    private String resolveIndustryLabel(String categoryId) {
        if (categoryId == null || categoryId.isBlank()) {
            return "";
        }
        InterviewIndustryCategoryEntity cat = industryMapper.selectById(categoryId);
        if (cat == null) {
            return categoryId;
        }
        if (cat.getLevel() != null && cat.getLevel() == 2 && cat.getParentId() != null) {
            InterviewIndustryCategoryEntity parent = industryMapper.selectById(cat.getParentId());
            if (parent != null) {
                return parent.getCategoryName() + " / " + cat.getCategoryName();
            }
        }
        return cat.getCategoryName();
    }

    private List<String> loadTags(String planRowId) {
        List<InterviewPlanModuleTagEntity> tags = tagMapper.selectList(
                Wrappers.<InterviewPlanModuleTagEntity>lambdaQuery()
                        .eq(InterviewPlanModuleTagEntity::getPlanRowId, planRowId)
                        .orderByAsc(InterviewPlanModuleTagEntity::getSortNo)
        );
        List<String> names = new ArrayList<>();
        for (InterviewPlanModuleTagEntity t : tags) {
            names.add(t.getTagName());
        }
        return names;
    }

    private List<Map<String, Object>> loadQuestions(String planRowId) {
        List<InterviewPlanQuestionEntity> rows = questionMapper.selectList(
                Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanRowId, planRowId)
                        .orderByAsc(InterviewPlanQuestionEntity::getSeqNo)
        );
        InterviewPlanQuestionExtrasSupport.PlanQuestionExtrasSnapshot extras =
                questionExtrasSupport.loadSnapshotByPlanRowId(planRowId);
        List<Map<String, Object>> list = new ArrayList<>();
        for (InterviewPlanQuestionEntity q : rows) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("iq_row_id", q.getIqRowId());
            m.put("question_id", q.getQuestionId());
            m.put("seq_no", q.getSeqNo());
            m.put("text", q.getQuestionText());
            m.put("weight", q.getWeight());
            m.put("thinking_hint", q.getThinkingHint());
            m.put("timeout_seconds", q.getTimeoutSeconds());
            m.put("reference_answer", q.getReferenceAnswer());
            m.put("dimensions", extras.dimensionsOf(q.getIqRowId()));
            m.put("preset_followups", extras.followupsOf(q.getIqRowId()));
            m.put("eval_criteria", extras.criteriaOf(q.getIqRowId()));
            list.add(m);
        }
        return list;
    }
}
