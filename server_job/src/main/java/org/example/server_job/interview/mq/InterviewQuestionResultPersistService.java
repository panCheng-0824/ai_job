package org.example.server_job.interview.mq;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.entity.StudentInterviewAnswerEntity;
import org.example.server_job.interview.entity.StudentInterviewRecordEntity;
import org.example.server_job.interview.mapper.InterviewSessionMapper;
import org.example.server_job.interview.mapper.StudentInterviewAnswerMapper;
import org.example.server_job.interview.mapper.StudentInterviewRecordMapper;
import org.example.server_job.interview.support.InterviewContextRedisSupport;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 消费 {@code interview.question.completed}：落库逐题答题并刷新 Redis ctx。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class InterviewQuestionResultPersistService {

    static final String EVENT_QUESTION_COMPLETED = "interview.question.completed";

    private final ObjectMapper objectMapper;
    private final StudentInterviewAnswerMapper answerMapper;
    private final StudentInterviewRecordMapper recordMapper;
    private final InterviewSessionMapper sessionMapper;
    private final InterviewContextRedisSupport contextRedis;

    /**
     * 解析 MQ 信封；命中题完结事件时更新 DB 与 Redis。
     *
     * @return 是否已处理
     */
    @Transactional(rollbackFor = Exception.class)
    public boolean tryPersistFromEnvelopeJson(String rawJson) {
        if (rawJson == null || rawJson.isBlank()) {
            return false;
        }
        try {
            JsonNode root = objectMapper.readTree(rawJson);
            if (!EVENT_QUESTION_COMPLETED.equals(text(root, "event_type"))) {
                return false;
            }
            JsonNode payload = root.path("payload");
            if (!payload.isObject()) {
                log.warn("interview.question.completed 缺少 payload");
                return false;
            }
            String studentId = text(payload, "student_id");
            String recordId = text(payload, "record_id");
            String sessionId = text(payload, "interview_session_id");
            String questionId = text(payload, "question_id");
            int seqNo = payload.path("seq_no").asInt(-1);
            if (studentId.isBlank() || recordId.isBlank()) {
                log.warn("interview.question.completed 缺少 student_id/record_id");
                return false;
            }

            StudentInterviewAnswerEntity row = findAnswerRow(recordId, questionId, seqNo);
            if (row == null) {
                log.warn("未找到答题行 record={} question={} seq={}", recordId, questionId, seqNo);
                return false;
            }
            if ("completed".equalsIgnoreCase(row.getAnswerStatus())) {
                log.info("题已完结，幂等跳过 record={} seq={}", recordId, seqNo);
                return true;
            }

            LocalDateTime now = LocalDateTime.now();
            row.setAnswerStatus("completed");
            row.setAnswerText(text(payload, "answer_text"));
            row.setTurnId(text(payload, "turn_id"));
            row.setEvaluatorComment(text(payload.path("evaluator_json"), "reason"));
            row.setAnsweredAt(now);
            JsonNode scoreNode = payload.path("scorer_json").path("total_score");
            if (!scoreNode.isMissingNode() && scoreNode.isNumber()) {
                row.setScore(BigDecimal.valueOf(scoreNode.asDouble()));
            }
            answerMapper.updateById(row);

            bumpSessionAndRecord(sessionId, recordId, seqNo, now);
            contextRedis.advanceAfterQuestionCompleted(studentId, recordId, seqNo);
            log.info(
                    "题完结已落库 record={} seq={} question={}",
                    recordId,
                    seqNo,
                    questionId
            );
            return true;
        } catch (Exception ex) {
            log.error("interview.question.completed 落库失败: {}", ex.getMessage(), ex);
            return false;
        }
    }

    private StudentInterviewAnswerEntity findAnswerRow(String recordId, String questionId, int seqNo) {
        if (seqNo >= 0) {
            var rows = answerMapper.selectList(
                    Wrappers.<StudentInterviewAnswerEntity>lambdaQuery()
                            .eq(StudentInterviewAnswerEntity::getRecordId, recordId)
                            .eq(StudentInterviewAnswerEntity::getSeqNo, seqNo)
                            .last("LIMIT 1")
            );
            if (!rows.isEmpty()) {
                return rows.get(0);
            }
        }
        if (questionId != null && !questionId.isBlank()) {
            var rows = answerMapper.selectList(
                    Wrappers.<StudentInterviewAnswerEntity>lambdaQuery()
                            .eq(StudentInterviewAnswerEntity::getRecordId, recordId)
                            .eq(StudentInterviewAnswerEntity::getQuestionId, questionId.trim())
                            .last("LIMIT 1")
            );
            if (!rows.isEmpty()) {
                return rows.get(0);
            }
        }
        return null;
    }

    private void bumpSessionAndRecord(String sessionId, String recordId, int completedSeqNo, LocalDateTime now) {
        if (sessionId != null && !sessionId.isBlank()) {
            InterviewSessionEntity session = sessionMapper.selectById(sessionId);
            if (session != null) {
                session.setCurrentQuestionIndex(completedSeqNo + 1);
                session.setPhase("question");
                session.setStatus("in_progress");
                session.setUpdatedAt(now);
                sessionMapper.updateById(session);
            }
        }
        StudentInterviewRecordEntity record = recordMapper.selectById(recordId);
        if (record != null) {
            int answered = record.getQuestionAnswered() == null ? 0 : record.getQuestionAnswered();
            record.setQuestionAnswered(answered + 1);
            record.setSessionStatus("in_progress");
            recordMapper.updateById(record);
        }
    }

    private static String text(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return v == null || v.isNull() ? "" : v.asText("");
    }
}
