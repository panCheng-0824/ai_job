package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.interview.dto.InterviewPlanQuestionSaveItem;
import org.example.server_job.interview.dto.InterviewPlanSaveRequest;
import org.example.server_job.interview.entity.InterviewPlanBasicsEntity;
import org.example.server_job.interview.entity.InterviewPlanModuleTagEntity;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;
import org.example.server_job.interview.mapper.InterviewPlanBasicsMapper;
import org.example.server_job.interview.mapper.InterviewPlanModuleTagMapper;
import org.example.server_job.interview.mapper.InterviewPlanQuestionMapper;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * 大纲多表写入：基础信息、模块标签、题目；及按 plan_id 级联删除。
 */
@Component
public class InterviewPlanWriteSupport {

    private final InterviewPlanBasicsMapper basicsMapper;
    private final InterviewPlanModuleTagMapper tagMapper;
    private final InterviewPlanQuestionMapper questionMapper;
    private final InterviewPlanQuestionExtrasSupport questionExtrasSupport;

    public InterviewPlanWriteSupport(
            InterviewPlanBasicsMapper basicsMapper,
            InterviewPlanModuleTagMapper tagMapper,
            InterviewPlanQuestionMapper questionMapper,
            InterviewPlanQuestionExtrasSupport questionExtrasSupport
    ) {
        this.basicsMapper = basicsMapper;
        this.tagMapper = tagMapper;
        this.questionMapper = questionMapper;
        this.questionExtrasSupport = questionExtrasSupport;
    }

    /**
     * 插入一个新版本的大纲（含标签与题目）。
     */
    public InterviewPlanBasicsEntity insertPlanVersion(
            String studentId,
            String planId,
            int version,
            InterviewPlanSaveRequest req
    ) {
        String planRowId = InterviewIds.planRowId(planId, version);
        LocalDateTime now = LocalDateTime.now();

        InterviewPlanBasicsEntity basics = new InterviewPlanBasicsEntity();
        basics.setPlanRowId(planRowId);
        basics.setPlanId(planId);
        basics.setVersion(version);
        basics.setTitle(req.title().trim());
        basics.setTargetRole(trimOrEmpty(req.targetRole()));
        basics.setIntroduction(trimOrEmpty(req.introduction()));
        basics.setSuitableAudience(trimOrEmpty(req.suitableAudience()));
        basics.setIndustryCategoryId(req.industryCategoryId().trim());
        basics.setIndustryClassifySource("manual");
        basics.setVisibility("private");
        basics.setStatus(normalizeStatus(req.status()));
        basics.setStudentId(studentId);
        basics.setRubricVersion("v1");
        basics.setCreatedAt(now);
        basics.setUpdatedAt(now);

        int questionCount = insertQuestions(planRowId, planId, version, req.questions(), now);
        basics.setQuestionCount(questionCount);
        insertModuleTags(planRowId, req.moduleTags());
        basicsMapper.insert(basics);
        return basics;
    }

    /**
     * 删除 plan_id 下全部版本及子表（题目维度/追问/评分、模块标签、基础行）。
     *
     * <p>先按 plan_row_id 逐版本删除，再按 plan_id 兜底清理残留，避免 basics 已删而题目孤儿。
     */
    public void deletePlanAllVersions(String planId) {
        if (planId == null || planId.isBlank()) {
            return;
        }
        String pid = planId.trim();
        Set<String> planRowIds = collectPlanRowIds(pid);
        for (String planRowId : planRowIds) {
            deletePlanRow(planRowId);
        }
        purgeOrphansByPlanId(pid);
    }

    /** 汇总 basics 与 questions 中出现的 plan_row_id */
    private Set<String> collectPlanRowIds(String planId) {
        Set<String> planRowIds = new LinkedHashSet<>();
        List<InterviewPlanBasicsEntity> basicsRows = basicsMapper.selectList(
                Wrappers.<InterviewPlanBasicsEntity>lambdaQuery()
                        .eq(InterviewPlanBasicsEntity::getPlanId, planId)
                        .select(InterviewPlanBasicsEntity::getPlanRowId)
        );
        for (InterviewPlanBasicsEntity row : basicsRows) {
            if (row.getPlanRowId() != null && !row.getPlanRowId().isBlank()) {
                planRowIds.add(row.getPlanRowId());
            }
        }
        List<InterviewPlanQuestionEntity> questionRows = questionMapper.selectList(
                Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanId, planId)
                        .select(InterviewPlanQuestionEntity::getPlanRowId)
        );
        for (InterviewPlanQuestionEntity q : questionRows) {
            if (q.getPlanRowId() != null && !q.getPlanRowId().isBlank()) {
                planRowIds.add(q.getPlanRowId());
            }
        }
        return planRowIds;
    }

    /** 按 plan_id 兜底删除残留题目、标签与基础行 */
    private void purgeOrphansByPlanId(String planId) {
        List<InterviewPlanQuestionEntity> remainingQuestions = questionMapper.selectList(
                Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanId, planId)
                        .select(InterviewPlanQuestionEntity::getIqRowId)
        );
        for (InterviewPlanQuestionEntity q : remainingQuestions) {
            questionExtrasSupport.deleteByIqRowId(q.getIqRowId());
        }
        questionMapper.delete(
                Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanId, planId)
        );
        tagMapper.delete(
                Wrappers.<InterviewPlanModuleTagEntity>lambdaQuery()
                        .likeRight(InterviewPlanModuleTagEntity::getPlanRowId, planId + "#")
        );
        basicsMapper.delete(
                Wrappers.<InterviewPlanBasicsEntity>lambdaQuery()
                        .eq(InterviewPlanBasicsEntity::getPlanId, planId)
        );
    }

    private void deletePlanRow(String planRowId) {
        if (planRowId == null || planRowId.isBlank()) {
            return;
        }
        // 先删题目附属子表，再删主表，避免孤儿数据
        questionExtrasSupport.deleteByPlanRowId(planRowId);
        questionMapper.delete(
                Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanRowId, planRowId)
        );
        tagMapper.delete(
                Wrappers.<InterviewPlanModuleTagEntity>lambdaQuery()
                        .eq(InterviewPlanModuleTagEntity::getPlanRowId, planRowId)
        );
        basicsMapper.deleteById(planRowId);
    }

    private void insertModuleTags(String planRowId, List<String> tags) {
        if (tags == null || tags.isEmpty()) {
            return;
        }
        int sort = 0;
        for (String raw : tags) {
            String name = raw == null ? "" : raw.trim();
            if (name.isEmpty()) {
                continue;
            }
            InterviewPlanModuleTagEntity tag = new InterviewPlanModuleTagEntity();
            tag.setPlanRowId(planRowId);
            tag.setTagName(name);
            tag.setSortNo(sort++);
            tagMapper.insert(tag);
        }
    }

    private int insertQuestions(
            String planRowId,
            String planId,
            int version,
            List<InterviewPlanQuestionSaveItem> questions,
            LocalDateTime now
    ) {
        int seq = 0;
        for (InterviewPlanQuestionSaveItem q : questions) {
            String questionId = q.questionId() != null && !q.questionId().isBlank()
                    ? q.questionId().trim()
                    : "q" + String.format("%03d", seq + 1);
            InterviewPlanQuestionEntity row = new InterviewPlanQuestionEntity();
            row.setIqRowId(InterviewIds.questionRowId(planRowId, questionId));
            row.setPlanRowId(planRowId);
            row.setPlanId(planId);
            row.setPlanVersion(version);
            row.setQuestionId(questionId);
            row.setSeqNo(seq++);
            row.setQuestionText(q.text().trim());
            row.setWeight(BigDecimal.valueOf(q.weight() != null ? q.weight() : 1.0));
            row.setThinkingHint(trimOrEmpty(q.thinkingHint()));
            row.setTimeoutSeconds(q.timeoutSeconds() != null && q.timeoutSeconds() > 0 ? q.timeoutSeconds() : 300);
            row.setReferenceAnswer("");
            row.setCreatedAt(now);
            questionMapper.insert(row);
        }
        return seq;
    }

    private static String normalizeStatus(String status) {
        if (status == null || status.isBlank()) {
            return "draft";
        }
        String s = status.trim().toLowerCase();
        if ("published".equals(s) || "archived".equals(s)) {
            return s;
        }
        return "draft";
    }

    private static String trimOrEmpty(String v) {
        return v == null ? "" : v.trim();
    }
}
