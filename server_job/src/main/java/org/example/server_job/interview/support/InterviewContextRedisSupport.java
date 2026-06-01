package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.client.redis.RedisStringClient;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;
import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.entity.StudentInterviewRecordEntity;
import org.example.server_job.interview.mapper.InterviewPlanQuestionMapper;
import org.example.server_job.interview.mapper.InterviewSessionMapper;
import org.example.server_job.interview.mapper.StudentInterviewRecordMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 面试整场进度 Redis 上下文（{@code interview:ctx:{student_id}:{record_id}}）。
 *
 * <p>创建会话时写入题目详情 + 逐题状态；题完结 MQ 消费后刷新指针与题目状态。
 */
@Component
public class InterviewContextRedisSupport {

    private static final Logger log = LoggerFactory.getLogger(InterviewContextRedisSupport.class);
    private static final Duration CTX_TTL = Duration.ofHours(24);

    private final RedisStringClient redis;
    private final ObjectMapper objectMapper;
    private final InterviewSessionMapper sessionMapper;
    private final StudentInterviewRecordMapper recordMapper;
    private final InterviewPlanQuestionMapper questionMapper;
    private final InterviewContextQuestionSnapshotSupport questionSnapshotSupport;

    public InterviewContextRedisSupport(
            RedisStringClient redis,
            ObjectMapper objectMapper,
            InterviewSessionMapper sessionMapper,
            StudentInterviewRecordMapper recordMapper,
            InterviewPlanQuestionMapper questionMapper,
            InterviewContextQuestionSnapshotSupport questionSnapshotSupport
    ) {
        this.redis = redis;
        this.objectMapper = objectMapper;
        this.sessionMapper = sessionMapper;
        this.recordMapper = recordMapper;
        this.questionMapper = questionMapper;
        this.questionSnapshotSupport = questionSnapshotSupport;
    }

    /** 创建面试记录后写入初始 ctx（题目详情 + 全部 pending），并返回 ctx_key */
    public String seedFromStart(
            String studentId,
            String recordId,
            String interviewSessionId,
            String chatSessionId,
            String planId,
            int planVersion,
            String planRowId,
            int questionTotal
    ) {
        List<Map<String, Object>> questions = questionSnapshotSupport.buildQuestionSnapshots(planRowId, recordId);
        InterviewPlanQuestionEntity first = loadQuestions(planRowId).stream().findFirst().orElse(null);

        Map<String, Object> ctx = baseCtx(
                studentId, recordId, interviewSessionId, chatSessionId, planId, planVersion, questionTotal
        );
        ctx.put("status", "ready");
        ctx.put("phase", "self_intro");
        ctx.put("current_question_index", 0);
        ctx.put("question_answered", 0);
        ctx.put("questions", questions);

        if (first != null) {
            applyCurrentQuestionPointers(ctx, first, questions);
        } else {
            ctx.put("current_question_id", "");
            ctx.put("current_iq_row_id", "");
            ctx.put("current_seq_no", 0);
            ctx.put("current_question", Map.of());
        }
        ctx.put("updated_at", LocalDateTime.now().toString());
        String key = InterviewRedisKeys.ctx(studentId, recordId);
        write(key, ctx);
        log.info("面试 ctx 已写入 Redis key={} session={} questions={}", key, interviewSessionId, questions.size());
        return key;
    }

    /** 读取 ctx；不存在时尝试从 DB 重建 */
    public Optional<Map<String, Object>> read(String studentId, String recordId) {
        String key = InterviewRedisKeys.ctx(studentId, recordId);
        Optional<Map<String, Object>> cached = readRaw(key);
        if (cached.isPresent()) {
            return cached;
        }
        return rebuildFromDb(studentId, recordId);
    }

    /** 题完结后推进进度、更新逐题 answer_status 并回写 Redis */
    public void advanceAfterQuestionCompleted(String studentId, String recordId, int completedSeqNo) {
        Optional<Map<String, Object>> opt = read(studentId, recordId);
        if (opt.isEmpty()) {
            rebuildFromDb(studentId, recordId);
            opt = read(studentId, recordId);
        }
        if (opt.isEmpty()) {
            return;
        }
        Map<String, Object> ctx = new LinkedHashMap<>(opt.get());
        String planId = String.valueOf(ctx.getOrDefault("plan_id", ""));
        int planVersion = toInt(ctx.get("plan_version"), 1);
        String planRowId = InterviewIds.planRowId(planId, planVersion);
        List<InterviewPlanQuestionEntity> planQuestions = loadQuestions(planRowId);

        List<Map<String, Object>> questionList = InterviewContextQuestionSnapshotSupport.copyQuestionList(
                ctx.get("questions")
        );
        if (questionList.isEmpty()) {
            questionList = questionSnapshotSupport.buildQuestionSnapshots(planRowId, recordId);
        }
        questionSnapshotSupport.applyCompletedAt(questionList, completedSeqNo);
        ctx.put("questions", questionList);

        int nextIndex = completedSeqNo + 1;
        int answered = toInt(ctx.get("question_answered"), 0) + 1;
        ctx.put("question_answered", answered);
        ctx.put("status", "in_progress");
        ctx.put("phase", "question");

        if (nextIndex >= planQuestions.size()) {
            ctx.put("status", "completed");
            ctx.put("phase", "completed");
            ctx.put("current_question_index", planQuestions.size());
            ctx.put("current_question_id", "");
            ctx.put("current_iq_row_id", "");
            ctx.put("current_seq_no", planQuestions.size());
            ctx.put("current_question", Map.of());
        } else {
            InterviewPlanQuestionEntity next = planQuestions.get(nextIndex);
            ctx.put("current_question_index", nextIndex);
            applyCurrentQuestionPointers(ctx, next, questionList);
        }
        ctx.put("updated_at", LocalDateTime.now().toString());
        write(InterviewRedisKeys.ctx(studentId, recordId), ctx);
    }

    /** 进入遮层：整场 in_progress，当前题 answer_status → in_progress */
    public void markInProgress(String studentId, String recordId) {
        read(studentId, recordId).ifPresent(existing -> {
            Map<String, Object> ctx = new LinkedHashMap<>(existing);
            if ("ready".equals(String.valueOf(ctx.get("status")))) {
                ctx.put("status", "in_progress");
            }
            int seq = toInt(ctx.get("current_seq_no"), 0);
            List<Map<String, Object>> questionList = InterviewContextQuestionSnapshotSupport.copyQuestionList(
                    ctx.get("questions")
            );
            questionSnapshotSupport.markInProgressAt(questionList, seq);
            ctx.put("questions", questionList);
            ctx.put("updated_at", LocalDateTime.now().toString());
            write(InterviewRedisKeys.ctx(studentId, recordId), ctx);
        });
    }

    private Optional<Map<String, Object>> rebuildFromDb(String studentId, String recordId) {
        StudentInterviewRecordEntity record = recordMapper.selectById(recordId);
        if (record == null || !studentId.equals(record.getStudentId())) {
            return Optional.empty();
        }
        InterviewSessionEntity session = sessionMapper.selectById(record.getInterviewSessionId());
        if (session == null) {
            return Optional.empty();
        }
        String planRowId = InterviewIds.planRowId(record.getPlanId(), record.getPlanVersion());
        String key = seedFromStart(
                studentId,
                recordId,
                record.getInterviewSessionId(),
                record.getChatSessionId(),
                record.getPlanId(),
                record.getPlanVersion() == null ? 1 : record.getPlanVersion(),
                planRowId,
                record.getQuestionTotal() == null ? 0 : record.getQuestionTotal()
        );
        Map<String, Object> ctx = readRaw(key).orElseGet(LinkedHashMap::new);
        ctx.put("current_question_index", session.getCurrentQuestionIndex() == null ? 0 : session.getCurrentQuestionIndex());
        ctx.put("question_answered", record.getQuestionAnswered() == null ? 0 : record.getQuestionAnswered());
        ctx.put("phase", session.getPhase() == null ? "question" : session.getPhase());
        ctx.put("status", session.getStatus() == null ? "in_progress" : session.getStatus());
        write(key, ctx);
        return Optional.of(ctx);
    }

    private static Map<String, Object> baseCtx(
            String studentId,
            String recordId,
            String interviewSessionId,
            String chatSessionId,
            String planId,
            int planVersion,
            int questionTotal
    ) {
        Map<String, Object> ctx = new LinkedHashMap<>();
        ctx.put("record_id", recordId);
        ctx.put("interview_session_id", interviewSessionId);
        ctx.put("student_id", studentId);
        ctx.put("chat_session_id", chatSessionId == null ? "" : chatSessionId);
        ctx.put("plan_id", planId);
        ctx.put("plan_version", planVersion);
        ctx.put("question_total", questionTotal);
        return ctx;
    }

    private void applyCurrentQuestionPointers(
            Map<String, Object> ctx,
            InterviewPlanQuestionEntity q,
            List<Map<String, Object>> questions
    ) {
        ctx.put("current_question_id", nullToEmpty(q.getQuestionId()));
        ctx.put("current_iq_row_id", nullToEmpty(q.getIqRowId()));
        ctx.put("current_seq_no", q.getSeqNo() == null ? 0 : q.getSeqNo());
        ctx.put("current_question", findSnapshotBySeq(questions, q.getSeqNo()));
    }

    private static Map<String, Object> findSnapshotBySeq(List<Map<String, Object>> questions, Integer seqNo) {
        int target = seqNo == null ? 0 : seqNo;
        for (Map<String, Object> snap : questions) {
            if (toInt(snap.get("seq_no"), -1) == target) {
                return snap;
            }
        }
        return Map.of();
    }

    private List<InterviewPlanQuestionEntity> loadQuestions(String planRowId) {
        return questionMapper.selectList(
                Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanRowId, planRowId)
                        .orderByAsc(InterviewPlanQuestionEntity::getSeqNo)
        );
    }

    private Optional<Map<String, Object>> readRaw(String key) {
        String raw = redis.get(key);
        if (raw == null || raw.isBlank()) {
            return Optional.empty();
        }
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = objectMapper.readValue(raw, Map.class);
            return Optional.of(map);
        } catch (JsonProcessingException e) {
            log.warn("解析 interview ctx 失败 key={}: {}", key, e.getMessage());
            return Optional.empty();
        }
    }

    private void write(String key, Map<String, Object> ctx) {
        try {
            redis.set(key, objectMapper.writeValueAsString(ctx), CTX_TTL);
        } catch (JsonProcessingException e) {
            log.error("写入 interview ctx 失败 key={}: {}", key, e.getMessage());
        }
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
