package org.example.server_job.interview.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.interview.entity.InterviewIndustryCategoryEntity;
import org.example.server_job.interview.entity.StudentInterviewAnswerEntity;
import org.example.server_job.interview.entity.StudentInterviewRecordEntity;
import org.example.server_job.interview.mapper.InterviewIndustryCategoryMapper;
import org.example.server_job.interview.mapper.StudentInterviewAnswerMapper;
import org.example.server_job.interview.mapper.StudentInterviewRecordMapper;
import org.example.server_job.interview.service.StudentInterviewRecordService;
import org.example.server_job.interview.support.InterviewRequestValidator;
import org.example.server_job.interview.support.StudentInterviewAnswerEnrichSupport;
import org.example.server_job.interview.support.StudentInterviewRecordDeleteSupport;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 「我的面试记录」列表、详情与逐题答题查询。
 */
@Service
public class StudentInterviewRecordServiceImpl implements StudentInterviewRecordService {

    private final StudentInterviewRecordMapper recordMapper;
    private final StudentInterviewAnswerMapper answerMapper;
    private final InterviewIndustryCategoryMapper industryMapper;
    private final StudentInterviewAnswerEnrichSupport answerEnrichSupport;
    private final StudentInterviewRecordDeleteSupport deleteSupport;

    public StudentInterviewRecordServiceImpl(
            StudentInterviewRecordMapper recordMapper,
            StudentInterviewAnswerMapper answerMapper,
            InterviewIndustryCategoryMapper industryMapper,
            StudentInterviewAnswerEnrichSupport answerEnrichSupport,
            StudentInterviewRecordDeleteSupport deleteSupport
    ) {
        this.recordMapper = recordMapper;
        this.answerMapper = answerMapper;
        this.industryMapper = industryMapper;
        this.answerEnrichSupport = answerEnrichSupport;
        this.deleteSupport = deleteSupport;
    }

    @Override
    public Map<String, Object> listByStudent(String studentId, String summaryStatus) {
        String sid = InterviewRequestValidator.requireStudentId(studentId);
        var query = Wrappers.<StudentInterviewRecordEntity>lambdaQuery()
                .eq(StudentInterviewRecordEntity::getStudentId, sid)
                .orderByDesc(StudentInterviewRecordEntity::getCreatedAt);
        if (summaryStatus != null && !summaryStatus.isBlank()) {
            query.eq(StudentInterviewRecordEntity::getSummaryStatus, summaryStatus.trim());
        }
        List<StudentInterviewRecordEntity> rows = recordMapper.selectList(query);
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudentInterviewRecordEntity row : rows) {
            items.add(toListItem(row));
        }
        return Map.of("student_id", sid, "items", items, "count", items.size());
    }

    @Override
    public Map<String, Object> getDetail(String studentId, String recordId) {
        StudentInterviewRecordEntity row = requireOwnedRecord(studentId, recordId);
        Map<String, Object> out = new LinkedHashMap<>(toListItem(row));
        out.put("interview_session_id", row.getInterviewSessionId());
        out.put("chat_session_id", row.getChatSessionId());
        out.put("plan_id", row.getPlanId());
        out.put("plan_version", row.getPlanVersion());
        out.put("report_id", row.getReportId());
        out.put("summary_at", row.getSummaryAt());
        out.put("completed_at", row.getCompletedAt());
        return out;
    }

    @Override
    public Map<String, Object> listAnswers(String studentId, String recordId) {
        StudentInterviewRecordEntity row = requireOwnedRecord(studentId, recordId);
        List<StudentInterviewAnswerEntity> answers = answerMapper.selectList(
                Wrappers.<StudentInterviewAnswerEntity>lambdaQuery()
                        .eq(StudentInterviewAnswerEntity::getRecordId, recordId)
                        .orderByAsc(StudentInterviewAnswerEntity::getSeqNo)
        );
        Map<String, String> questionTextMap = answerEnrichSupport.loadQuestionTextByAnswers(answers);
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudentInterviewAnswerEntity a : answers) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("answer_row_id", a.getAnswerRowId());
            m.put("question_id", a.getQuestionId());
            m.put("iq_row_id", a.getIqRowId());
            m.put("seq_no", a.getSeqNo());
            m.put("answer_status", a.getAnswerStatus());
            m.put("question_text", questionTextMap.getOrDefault(a.getAnswerRowId(), ""));
            m.put("answer_text", a.getAnswerText());
            m.put("score", a.getScore());
            m.put("evaluator_comment", a.getEvaluatorComment());
            m.put("answered_at", a.getAnsweredAt());
            m.put("summarized_at", a.getSummarizedAt());
            items.add(m);
        }
        return Map.of(
                "record_id", recordId,
                "interview_session_id", row.getInterviewSessionId(),
                "items", items,
                "count", items.size()
        );
    }

    @Override
    public Map<String, Object> delete(String studentId, String recordId) {
        StudentInterviewRecordDeleteSupport.DeleteResult result =
                deleteSupport.deleteOwnedRecord(studentId, recordId);
        return Map.of(
                "deleted", true,
                "record_id", result.recordId(),
                "interview_session_id", result.interviewSessionId() == null ? "" : result.interviewSessionId()
        );
    }

    @Override
    public Map<String, Object> lookupByPlanAndChat(String studentId, String planId, String chatSessionId) {
        String sid = InterviewRequestValidator.requireStudentId(studentId);
        if (planId == null || planId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "plan_id 不能为空");
        }
        if (chatSessionId == null || chatSessionId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "chat_session_id 不能为空");
        }
        StudentInterviewRecordEntity row = recordMapper.selectOne(
                Wrappers.<StudentInterviewRecordEntity>lambdaQuery()
                        .eq(StudentInterviewRecordEntity::getStudentId, sid)
                        .eq(StudentInterviewRecordEntity::getPlanId, planId.trim())
                        .eq(StudentInterviewRecordEntity::getChatSessionId, chatSessionId.trim())
                        .orderByDesc(StudentInterviewRecordEntity::getCreatedAt)
                        .last("LIMIT 1")
        );
        if (row == null) {
            return Map.of(
                    "exists", false,
                    "student_id", sid,
                    "plan_id", planId.trim(),
                    "chat_session_id", chatSessionId.trim()
            );
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("exists", true);
        out.put("student_id", sid);
        out.put("plan_id", row.getPlanId());
        out.put("chat_session_id", row.getChatSessionId());
        out.put("record_id", row.getRecordId());
        out.put("interview_session_id", row.getInterviewSessionId());
        out.put("plan_version", row.getPlanVersion());
        out.put("session_status", row.getSessionStatus());
        return out;
    }

    private StudentInterviewRecordEntity requireOwnedRecord(String studentId, String recordId) {
        String sid = InterviewRequestValidator.requireStudentId(studentId);
        if (recordId == null || recordId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "record_id 不能为空");
        }
        StudentInterviewRecordEntity row = recordMapper.selectById(recordId);
        if (row == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "面试记录不存在");
        }
        if (!sid.equals(row.getStudentId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该记录");
        }
        return row;
    }

    private Map<String, Object> toListItem(StudentInterviewRecordEntity row) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("record_id", row.getRecordId());
        m.put("plan_id", row.getPlanId());
        m.put("plan_version", row.getPlanVersion());
        m.put("interview_session_id", row.getInterviewSessionId());
        m.put("chat_session_id", row.getChatSessionId());
        m.put("plan_title", row.getPlanTitle());
        m.put("target_role", row.getTargetRole());
        m.put("industry_category_id", row.getIndustryCategoryId());
        m.put("industry_label", resolveIndustryLabel(row.getIndustryCategoryId()));
        m.put("session_status", row.getSessionStatus());
        m.put("summary_status", row.getSummaryStatus());
        m.put("total_score", row.getTotalScore());
        m.put("question_total", row.getQuestionTotal());
        m.put("question_answered", row.getQuestionAnswered());
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
}
