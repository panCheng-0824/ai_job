package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;
import org.example.server_job.interview.entity.StudentInterviewAnswerEntity;
import org.example.server_job.interview.mapper.InterviewPlanQuestionMapper;
import org.example.server_job.interview.mapper.StudentInterviewAnswerMapper;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 组装写入 Redis ctx 的题目快照（含附属子表与逐题答题状态）。
 *
 * <p>题目字段与大纲详情 API 返回结构对齐，供 ai_job 只读 Redis 构造 ContextBundle。
 */
@Component
public class InterviewContextQuestionSnapshotSupport {

    static final String STATUS_PENDING = "pending";
    static final String STATUS_IN_PROGRESS = "in_progress";
    static final String STATUS_COMPLETED = "completed";

    private final InterviewPlanQuestionMapper questionMapper;
    private final InterviewPlanQuestionExtrasSupport extrasSupport;
    private final StudentInterviewAnswerMapper answerMapper;

    public InterviewContextQuestionSnapshotSupport(
            InterviewPlanQuestionMapper questionMapper,
            InterviewPlanQuestionExtrasSupport extrasSupport,
            StudentInterviewAnswerMapper answerMapper
    ) {
        this.questionMapper = questionMapper;
        this.extrasSupport = extrasSupport;
        this.answerMapper = answerMapper;
    }

    /**
     * 加载大纲全部题目快照，并合并 {@code student_interview_answers.answer_status}。
     *
     * @param planRowId 大纲物理主键
     * @param recordId  学生面试记录 ID；可为空则全部 {@link #STATUS_PENDING}
     */
    public List<Map<String, Object>> buildQuestionSnapshots(String planRowId, String recordId) {
        List<InterviewPlanQuestionEntity> rows = questionMapper.selectList(
                Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanRowId, planRowId)
                        .orderByAsc(InterviewPlanQuestionEntity::getSeqNo)
        );
        InterviewPlanQuestionExtrasSupport.PlanQuestionExtrasSnapshot extras =
                extrasSupport.loadSnapshotByPlanRowId(planRowId);
        Map<Integer, String> statusBySeq = loadAnswerStatusBySeq(recordId);

        List<Map<String, Object>> out = new ArrayList<>(rows.size());
        for (InterviewPlanQuestionEntity q : rows) {
            int seq = q.getSeqNo() == null ? 0 : q.getSeqNo();
            String status = statusBySeq.getOrDefault(seq, STATUS_PENDING);
            out.add(toSnapshot(q, extras, status));
        }
        return out;
    }

    /** 将指定 seq 标记为进行中，其余 pending/completed 不变 */
    public void markInProgressAt(List<Map<String, Object>> questions, int seqNo) {
        if (questions == null) {
            return;
        }
        for (Map<String, Object> q : questions) {
            int seq = toInt(q.get("seq_no"), -1);
            String st = String.valueOf(q.getOrDefault("answer_status", STATUS_PENDING));
            if (seq == seqNo && !STATUS_COMPLETED.equals(st)) {
                q.put("answer_status", STATUS_IN_PROGRESS);
            }
        }
    }

    /** 题完结：completedSeq 标记 completed，下一题（若存在）标记 in_progress */
    public void applyCompletedAt(List<Map<String, Object>> questions, int completedSeqNo) {
        if (questions == null) {
            return;
        }
        int nextSeq = completedSeqNo + 1;
        for (Map<String, Object> q : questions) {
            int seq = toInt(q.get("seq_no"), -1);
            if (seq == completedSeqNo) {
                q.put("answer_status", STATUS_COMPLETED);
            } else if (seq == nextSeq) {
                q.put("answer_status", STATUS_IN_PROGRESS);
            }
        }
    }

    /** 单题快照（含 dimensions / preset_followups / eval_criteria / answer_status） */
    public Map<String, Object> toSnapshot(
            InterviewPlanQuestionEntity q,
            InterviewPlanQuestionExtrasSupport.PlanQuestionExtrasSnapshot extras,
            String answerStatus
    ) {
        String iqRowId = nullToEmpty(q.getIqRowId());
        Map<String, Object> snap = new LinkedHashMap<>();
        snap.put("id", nullToEmpty(q.getQuestionId()));
        snap.put("iq_row_id", iqRowId);
        snap.put("text", nullToEmpty(q.getQuestionText()));
        snap.put("thinking_hint", nullToEmpty(q.getThinkingHint()));
        snap.put("timeout_seconds", q.getTimeoutSeconds() == null ? 300 : q.getTimeoutSeconds());
        snap.put("reference_answer", nullToEmpty(q.getReferenceAnswer()));
        snap.put("weight", q.getWeight() == null ? 1.0 : q.getWeight().doubleValue());
        snap.put("seq_no", q.getSeqNo() == null ? 0 : q.getSeqNo());
        snap.put("dimensions", new ArrayList<>(extras.dimensionsOf(iqRowId)));
        snap.put("preset_followups", new ArrayList<>(extras.followupsOf(iqRowId)));
        snap.put("eval_criteria", new LinkedHashMap<>(extras.criteriaOf(iqRowId)));
        snap.put("answer_status", answerStatus == null || answerStatus.isBlank() ? STATUS_PENDING : answerStatus);
        return snap;
    }

    private Map<Integer, String> loadAnswerStatusBySeq(String recordId) {
        Map<Integer, String> map = new LinkedHashMap<>();
        if (recordId == null || recordId.isBlank()) {
            return map;
        }
        List<StudentInterviewAnswerEntity> rows = answerMapper.selectList(
                Wrappers.<StudentInterviewAnswerEntity>lambdaQuery()
                        .eq(StudentInterviewAnswerEntity::getRecordId, recordId.trim())
                        .orderByAsc(StudentInterviewAnswerEntity::getSeqNo)
        );
        for (StudentInterviewAnswerEntity row : rows) {
            if (row.getSeqNo() == null) {
                continue;
            }
            String st = row.getAnswerStatus() == null ? STATUS_PENDING : row.getAnswerStatus().trim();
            map.put(row.getSeqNo(), st.isEmpty() ? STATUS_PENDING : st);
        }
        return map;
    }

    @SuppressWarnings("unchecked")
    static List<Map<String, Object>> copyQuestionList(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return new ArrayList<>();
        }
        List<Map<String, Object>> out = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                out.add(new LinkedHashMap<>((Map<String, Object>) map));
            }
        }
        return out;
    }

    private static int toInt(Object v, int fallback) {
        if (v == null) {
            return fallback;
        }
        if (v instanceof Number n) {
            return n.intValue();
        }
        try {
            return Integer.parseInt(String.valueOf(v));
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    private static String nullToEmpty(String s) {
        return s == null ? "" : s;
    }
}
