package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;
import org.example.server_job.interview.entity.StudentInterviewAnswerEntity;
import org.example.server_job.interview.mapper.InterviewPlanQuestionMapper;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 学生答题行与大纲题目表关联，批量解析题干等展示字段。
 *
 * <p>优先按 {@code iq_row_id} 主键批量查；未命中时再按
 * {@code plan_id + plan_version + question_id} 兜底（避免主键拼接差异导致题干为空）。
 */
@Component
public class StudentInterviewAnswerEnrichSupport {

    private final InterviewPlanQuestionMapper questionMapper;

    public StudentInterviewAnswerEnrichSupport(InterviewPlanQuestionMapper questionMapper) {
        this.questionMapper = questionMapper;
    }

    /**
     * 为每条答题行解析题干。
     *
     * @return key 为答题行 {@code answer_row_id}，value 为 question_text
     */
    public Map<String, String> loadQuestionTextByAnswers(List<StudentInterviewAnswerEntity> answers) {
        if (answers == null || answers.isEmpty()) {
            return Collections.emptyMap();
        }
        Map<String, String> byIqRowId = loadQuestionTextByIqRowIds(answers);
        Map<String, String> out = new HashMap<>();
        for (StudentInterviewAnswerEntity a : answers) {
            if (a == null || a.getAnswerRowId() == null) {
                continue;
            }
            String text = resolveQuestionText(a, byIqRowId);
            out.put(a.getAnswerRowId(), text == null ? "" : text);
        }
        return out;
    }

    /**
     * 按 {@code iq_row_id} 批量加载题干（内部使用）。
     */
    Map<String, String> loadQuestionTextByIqRowIds(List<StudentInterviewAnswerEntity> answers) {
        Set<String> iqRowIds = answers.stream()
                .map(StudentInterviewAnswerEntity::getIqRowId)
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .collect(Collectors.toSet());
        if (iqRowIds.isEmpty()) {
            return Collections.emptyMap();
        }
        List<InterviewPlanQuestionEntity> rows = questionMapper.selectBatchIds(iqRowIds);
        Map<String, String> out = new HashMap<>();
        for (InterviewPlanQuestionEntity row : rows) {
            if (row == null || row.getIqRowId() == null) {
                continue;
            }
            out.put(row.getIqRowId().trim(), nullToEmpty(row.getQuestionText()));
        }
        return out;
    }

    private String resolveQuestionText(StudentInterviewAnswerEntity answer, Map<String, String> byIqRowId) {
        String iqKey = answer.getIqRowId() == null ? "" : answer.getIqRowId().trim();
        if (!iqKey.isEmpty()) {
            String hit = byIqRowId.get(iqKey);
            if (hit != null && !hit.isBlank()) {
                return hit;
            }
        }
        return lookupByPlanQuestion(
                answer.getPlanId(),
                answer.getPlanVersion(),
                answer.getQuestionId(),
                answer.getSeqNo()
        );
    }

    /**
     * 兜底：按大纲版本 + 题目业务 ID 或序号查题干。
     */
    private String lookupByPlanQuestion(String planId, Integer planVersion, String questionId, Integer seqNo) {
        if (planId == null || planId.isBlank()) {
            return "";
        }
        int ver = planVersion == null || planVersion <= 0 ? 1 : planVersion;
        String planRowId = InterviewIds.planRowId(planId.trim(), ver);

        if (questionId != null && !questionId.isBlank()) {
            InterviewPlanQuestionEntity byQid = questionMapper.selectOne(
                    Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                            .eq(InterviewPlanQuestionEntity::getPlanRowId, planRowId)
                            .eq(InterviewPlanQuestionEntity::getQuestionId, questionId.trim())
                            .last("LIMIT 1")
            );
            if (byQid != null) {
                return nullToEmpty(byQid.getQuestionText());
            }
            // 若 iq_row_id 因超长被截断，尝试重建主键再查
            String rebuiltIq = InterviewIds.questionRowId(planRowId, questionId.trim());
            InterviewPlanQuestionEntity byRebuilt = questionMapper.selectById(rebuiltIq);
            if (byRebuilt != null) {
                return nullToEmpty(byRebuilt.getQuestionText());
            }
        }

        if (seqNo != null && seqNo >= 0) {
            InterviewPlanQuestionEntity bySeq = questionMapper.selectOne(
                    Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                            .eq(InterviewPlanQuestionEntity::getPlanRowId, planRowId)
                            .eq(InterviewPlanQuestionEntity::getSeqNo, seqNo)
                            .last("LIMIT 1")
            );
            if (bySeq != null) {
                return nullToEmpty(bySeq.getQuestionText());
            }
        }
        return "";
    }

    private static String nullToEmpty(String v) {
        return v == null ? "" : v;
    }
}
