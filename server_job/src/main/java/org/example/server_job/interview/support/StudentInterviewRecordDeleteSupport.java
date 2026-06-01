package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.interview.entity.InterviewAuditLogEntity;
import org.example.server_job.interview.entity.InterviewReportEntity;
import org.example.server_job.interview.entity.InterviewTurnEntity;
import org.example.server_job.interview.entity.StudentInterviewAnswerEntity;
import org.example.server_job.interview.entity.StudentInterviewRecordEntity;
import org.example.server_job.interview.mapper.InterviewAuditLogMapper;
import org.example.server_job.interview.mapper.InterviewReportMapper;
import org.example.server_job.interview.mapper.InterviewSessionMapper;
import org.example.server_job.interview.mapper.InterviewTurnMapper;
import org.example.server_job.interview.mapper.StudentInterviewAnswerMapper;
import org.example.server_job.interview.mapper.StudentInterviewRecordMapper;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/**
 * 删除学生面试记录及关联会话数据（不删大纲题库）。
 *
 * <p>级联：Redis ctx/qsess → 逐题答题 → 回合 → 报告 → 审计 → 总结记录 → 面试会话。
 */
@Component
public class StudentInterviewRecordDeleteSupport {

    private final StudentInterviewRecordMapper recordMapper;
    private final StudentInterviewAnswerMapper answerMapper;
    private final InterviewSessionMapper sessionMapper;
    private final InterviewTurnMapper turnMapper;
    private final InterviewReportMapper reportMapper;
    private final InterviewAuditLogMapper auditLogMapper;
    private final InterviewContextRedisDeleteSupport contextRedisDeleteSupport;

    public StudentInterviewRecordDeleteSupport(
            StudentInterviewRecordMapper recordMapper,
            StudentInterviewAnswerMapper answerMapper,
            InterviewSessionMapper sessionMapper,
            InterviewTurnMapper turnMapper,
            InterviewReportMapper reportMapper,
            InterviewAuditLogMapper auditLogMapper,
            InterviewContextRedisDeleteSupport contextRedisDeleteSupport
    ) {
        this.recordMapper = recordMapper;
        this.answerMapper = answerMapper;
        this.sessionMapper = sessionMapper;
        this.turnMapper = turnMapper;
        this.reportMapper = reportMapper;
        this.auditLogMapper = auditLogMapper;
        this.contextRedisDeleteSupport = contextRedisDeleteSupport;
    }

    /**
     * 删除指定学生的单条面试记录（须为 record 所属学号）。
     *
     * @return 被删 record_id 与 interview_session_id
     */
    @Transactional(rollbackFor = Exception.class)
    public DeleteResult deleteOwnedRecord(String studentId, String recordId) {
        String sid = InterviewRequestValidator.requireStudentId(studentId);
        if (recordId == null || recordId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "record_id 不能为空");
        }
        StudentInterviewRecordEntity row = recordMapper.selectById(recordId.trim());
        if (row == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "面试记录不存在");
        }
        if (!sid.equals(row.getStudentId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权删除该记录");
        }

        String sessionId = row.getInterviewSessionId() == null ? "" : row.getInterviewSessionId().trim();
        String chatSessionId = row.getChatSessionId() == null ? "" : row.getChatSessionId().trim();

        // 先清 Redis，避免 MySQL 删完后 ctx 仍被 ai_job 误读
        contextRedisDeleteSupport.deleteForRecord(sid, recordId.trim(), chatSessionId, sessionId);

        answerMapper.delete(
                Wrappers.<StudentInterviewAnswerEntity>lambdaQuery()
                        .eq(StudentInterviewAnswerEntity::getRecordId, recordId.trim())
        );

        if (!sessionId.isEmpty()) {
            turnMapper.delete(
                    Wrappers.<InterviewTurnEntity>lambdaQuery()
                            .eq(InterviewTurnEntity::getInterviewSessionId, sessionId)
            );
            reportMapper.delete(
                    Wrappers.<InterviewReportEntity>lambdaQuery()
                            .eq(InterviewReportEntity::getInterviewSessionId, sessionId)
            );
            if (row.getReportId() != null && !row.getReportId().isBlank()) {
                reportMapper.deleteById(row.getReportId().trim());
            }
            auditLogMapper.delete(
                    Wrappers.<InterviewAuditLogEntity>lambdaQuery()
                            .eq(InterviewAuditLogEntity::getInterviewSessionId, sessionId)
            );
        }

        recordMapper.deleteById(recordId.trim());
        if (!sessionId.isEmpty()) {
            sessionMapper.deleteById(sessionId);
        }

        return new DeleteResult(recordId.trim(), sessionId);
    }

    /** 删除结果摘要 */
    public record DeleteResult(String recordId, String interviewSessionId) {
    }
}
