package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.example.server_job.interview.entity.StudentInterviewAnswerEntity;
import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.mapper.InterviewSessionMapper;
import org.example.server_job.interview.mapper.StudentInterviewAnswerMapper;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 会话加载与 JSON 视图转换（多 Service 共用）。
 * V2：答题历史从 {@code student_interview_answers} 组装，不再读 answers_json。
 */
@Component
public class InterviewSessionSupport {

    private final InterviewSessionMapper sessionMapper;
    private final StudentInterviewAnswerMapper answerMapper;
    private final InterviewPlanAssembler planAssembler;
    private final ObjectMapper objectMapper;

    public InterviewSessionSupport(
            InterviewSessionMapper sessionMapper,
            StudentInterviewAnswerMapper answerMapper,
            InterviewPlanAssembler planAssembler,
            ObjectMapper objectMapper
    ) {
        this.sessionMapper = sessionMapper;
        this.answerMapper = answerMapper;
        this.planAssembler = planAssembler;
        this.objectMapper = objectMapper;
    }

    /**
     * 按 ID 加载会话并校验学号归属。
     */
    public InterviewSessionEntity requireSession(String sessionId, String studentId) {
        InterviewSessionEntity session = sessionMapper.selectById(sessionId);
        if (session == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "面试会话不存在");
        }
        if (studentId != null && !studentId.isBlank() && !studentId.equals(session.getStudentId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该面试会话");
        }
        return session;
    }

    public InterviewSessionEntity findSessionOrThrow(String sessionId) {
        InterviewSessionEntity session = sessionMapper.selectById(sessionId);
        if (session == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会话不存在");
        }
        return session;
    }

    /**
     * 加载大纲 JSON 字符串（V2 优先，V1 回退）。
     */
    public String loadPlanJson(String planId, int version) {
        return planAssembler.loadPlanJson(planId, version);
    }

    public Map<String, Object> sessionToMap(InterviewSessionEntity session) {
        try {
            return objectMapper.readValue(sessionToJson(session), Map.class);
        } catch (Exception e) {
            Map<String, Object> m = new HashMap<>();
            m.put("interview_session_id", session.getInterviewSessionId());
            m.put("status", session.getStatus());
            return m;
        }
    }

    public String sessionToJson(InterviewSessionEntity session) throws Exception {
        ObjectNode n = objectMapper.createObjectNode();
        n.put("interview_session_id", session.getInterviewSessionId());
        n.put("student_id", session.getStudentId());
        n.put("chat_session_id", session.getChatSessionId());
        n.put("plan_id", session.getPlanId());
        n.put("plan_version", session.getPlanVersion());
        n.put("status", session.getStatus());
        n.put("phase", session.getPhase());
        n.put("current_question_index", session.getCurrentQuestionIndex());
        n.put("lock_version", session.getLockVersion());
        n.put("report_id", session.getReportId());
        n.put("token_budget_used", session.getTokenBudgetUsed());
        if (session.getSnapshotsJson() != null) {
            n.set("snapshots", objectMapper.readTree(session.getSnapshotsJson()));
        }
        n.set("answers", buildAnswersArray(session.getInterviewSessionId()));
        return objectMapper.writeValueAsString(n);
    }

    /** 从 V2 答题表组装 answers 数组，供 state API 与 context-bundle 使用 */
    private ArrayNode buildAnswersArray(String sessionId) throws Exception {
        List<StudentInterviewAnswerEntity> rows = answerMapper.selectList(
                Wrappers.<StudentInterviewAnswerEntity>lambdaQuery()
                        .eq(StudentInterviewAnswerEntity::getInterviewSessionId, sessionId)
                        .orderByAsc(StudentInterviewAnswerEntity::getSeqNo)
        );
        ArrayNode arr = objectMapper.createArrayNode();
        for (StudentInterviewAnswerEntity a : rows) {
            ObjectNode item = objectMapper.createObjectNode();
            item.put("question_id", a.getQuestionId());
            item.put("answer_status", a.getAnswerStatus());
            if (a.getAnswerText() != null) {
                item.put("final_answer", a.getAnswerText());
            }
            if (a.getScore() != null) {
                item.put("score", a.getScore().doubleValue());
            }
            arr.add(item);
        }
        return arr;
    }
}
