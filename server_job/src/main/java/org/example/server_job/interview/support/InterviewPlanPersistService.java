package org.example.server_job.interview.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import org.example.server_job.interview.entity.InterviewPlanBasicsEntity;
import org.example.server_job.interview.entity.InterviewPlanModuleTagEntity;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;
import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.entity.StudentInterviewAnswerEntity;
import org.example.server_job.interview.entity.StudentInterviewRecordEntity;
import org.example.server_job.interview.mapper.InterviewPlanBasicsMapper;
import org.example.server_job.interview.mapper.InterviewPlanModuleTagMapper;
import org.example.server_job.interview.mapper.InterviewPlanQuestionMapper;
import org.example.server_job.interview.mapper.InterviewSessionMapper;
import org.example.server_job.interview.mapper.StudentInterviewAnswerMapper;
import org.example.server_job.interview.mapper.StudentInterviewRecordMapper;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 确认大纲时将 JSON 计划写入 V2 关系表，并初始化会话、学生记录与逐题答题行。
 */
@Component
public class InterviewPlanPersistService {

    private final InterviewPlanBasicsMapper basicsMapper;
    private final InterviewPlanModuleTagMapper tagMapper;
    private final InterviewPlanQuestionMapper questionMapper;
    private final InterviewPlanQuestionJsonWriteSupport questionJsonWriteSupport;
    private final InterviewSessionMapper sessionMapper;
    private final StudentInterviewRecordMapper recordMapper;
    private final StudentInterviewAnswerMapper answerMapper;
    private final InterviewContextRedisSupport contextRedis;

    public InterviewPlanPersistService(
            InterviewPlanBasicsMapper basicsMapper,
            InterviewPlanModuleTagMapper tagMapper,
            InterviewPlanQuestionMapper questionMapper,
            InterviewPlanQuestionJsonWriteSupport questionJsonWriteSupport,
            InterviewSessionMapper sessionMapper,
            StudentInterviewRecordMapper recordMapper,
            StudentInterviewAnswerMapper answerMapper,
            InterviewContextRedisSupport contextRedis
    ) {
        this.basicsMapper = basicsMapper;
        this.tagMapper = tagMapper;
        this.questionMapper = questionMapper;
        this.questionJsonWriteSupport = questionJsonWriteSupport;
        this.sessionMapper = sessionMapper;
        this.recordMapper = recordMapper;
        this.answerMapper = answerMapper;
        this.contextRedis = contextRedis;
    }

    /**
     * 持久化大纲并创建 ready 状态会话及学生侧记录。
     *
     * @return Map 含 interview_session_id、plan_id、plan_version、record_id
     */
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> persistConfirm(
            String studentId,
            String planId,
            int version,
            JsonNode planNode,
            JsonNode planSummaryNode,
            String chatSessionId,
            String snapshotsJson,
            String industryCategoryId
    ) {
        String planRowId = InterviewIds.planRowId(planId, version);
        LocalDateTime now = LocalDateTime.now();

        InterviewPlanBasicsEntity basics = new InterviewPlanBasicsEntity();
        basics.setPlanRowId(planRowId);
        basics.setPlanId(planId);
        basics.setVersion(version);
        String targetRole = planNode.path("target_role").asText("");
        basics.setTargetRole(targetRole);
        basics.setTitle(targetRole.isBlank() ? planId : targetRole);
        basics.setSourceMaterialHash(planNode.path("source_material_hash").asText(""));
        basics.setRubricVersion(planNode.path("rubric_version").asText("v1"));
        basics.setPlannerModel(planNode.path("planner_model").asText(""));
        basics.setIndustryCategoryId(industryCategoryId);
        basics.setIndustryClassifySource("auto");
        basics.setVisibility("private");
        basics.setStatus("published");
        basics.setStudentId(studentId);
        basics.setCreatedAt(now);
        basics.setUpdatedAt(now);

        if (planSummaryNode != null && !planSummaryNode.isMissingNode()) {
            basics.setIntroduction(planSummaryNode.path("introduction").asText(""));
            basics.setSuitableAudience(planSummaryNode.path("suitable_audience").asText(""));
            persistModuleTags(planRowId, planSummaryNode.path("interview_categories"));
        }

        int questionCount = questionJsonWriteSupport.insertQuestionsFromJson(
                planRowId, planId, version, planNode.path("questions"), now
        );
        basics.setQuestionCount(questionCount);
        basicsMapper.insert(basics);

        String sessionId = InterviewIds.newSessionId();
        InterviewSessionEntity session = new InterviewSessionEntity();
        session.setInterviewSessionId(sessionId);
        session.setStudentId(studentId);
        session.setChatSessionId(chatSessionId);
        session.setPlanId(planId);
        session.setPlanVersion(version);
        session.setStatus("ready");
        session.setPhase("self_intro");
        session.setCurrentQuestionIndex(0);
        session.setLockVersion(0);
        session.setTokenBudgetUsed(0);
        session.setScorerVersion("v1");
        session.setSnapshotsJson(snapshotsJson == null ? "{}" : snapshotsJson);
        session.setCreatedAt(now);
        session.setUpdatedAt(now);
        sessionMapper.insert(session);

        String recordId = InterviewIds.newRecordId();
        StudentInterviewRecordEntity record = new StudentInterviewRecordEntity();
        record.setRecordId(recordId);
        record.setStudentId(studentId);
        record.setInterviewSessionId(sessionId);
        record.setChatSessionId(chatSessionId);
        record.setPlanId(planId);
        record.setPlanVersion(version);
        record.setIndustryCategoryId(industryCategoryId);
        record.setTargetRole(targetRole);
        record.setPlanTitle(basics.getTitle());
        record.setSessionStatus("ready");
        record.setSummaryStatus("pending");
        record.setQuestionTotal(questionCount);
        record.setQuestionAnswered(0);
        record.setCreatedAt(now);
        recordMapper.insert(record);

        seedAnswerRows(studentId, sessionId, recordId, planId, version, planRowId, now);

        return Map.of(
                "interview_session_id", sessionId,
                "plan_id", planId,
                "plan_version", version,
                "record_id", recordId,
                "status", "ready"
        );
    }

    /**
     * 大纲已由 MQ/管理端写入题库时，仅创建会话、学生面试记录与答题占位行。
     *
     * @param studentId     学号，须与 {@code interview_plan_basics.student_id} 一致
     * @param planId        大纲业务 ID
     * @param version       版本号；null 或 ≤0 时取该 plan_id 下最新版本
     * @param chatSessionId 门户聊天 session_id，可为空
     */
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> startSessionFromBankPlan(
            String studentId,
            String planId,
            Integer version,
            String chatSessionId
    ) {
        InterviewPlanBasicsEntity basics = loadOwnedBasics(studentId, planId, version);
        int ver = basics.getVersion() == null ? 1 : basics.getVersion();
        String planRowId = basics.getPlanRowId();
        LocalDateTime now = LocalDateTime.now();
        String targetRole = basics.getTargetRole() == null ? "" : basics.getTargetRole();
        int questionCount = basics.getQuestionCount() == null ? 0 : basics.getQuestionCount();
        String industryCategoryId = basics.getIndustryCategoryId();

        String sessionId = InterviewIds.newSessionId();
        InterviewSessionEntity session = new InterviewSessionEntity();
        session.setInterviewSessionId(sessionId);
        session.setStudentId(studentId);
        session.setChatSessionId(chatSessionId == null ? "" : chatSessionId);
        session.setPlanId(planId);
        session.setPlanVersion(ver);
        session.setStatus("ready");
        session.setPhase("self_intro");
        session.setCurrentQuestionIndex(0);
        session.setLockVersion(0);
        session.setTokenBudgetUsed(0);
        session.setScorerVersion("v1");
        session.setSnapshotsJson("{}");
        session.setCreatedAt(now);
        session.setUpdatedAt(now);
        sessionMapper.insert(session);

        String recordId = InterviewIds.newRecordId();
        StudentInterviewRecordEntity record = new StudentInterviewRecordEntity();
        record.setRecordId(recordId);
        record.setStudentId(studentId);
        record.setInterviewSessionId(sessionId);
        record.setChatSessionId(chatSessionId == null ? "" : chatSessionId);
        record.setPlanId(planId);
        record.setPlanVersion(ver);
        record.setIndustryCategoryId(industryCategoryId);
        record.setTargetRole(targetRole);
        record.setPlanTitle(basics.getTitle());
        record.setSessionStatus("ready");
        record.setSummaryStatus("pending");
        record.setQuestionTotal(questionCount);
        record.setQuestionAnswered(0);
        record.setCreatedAt(now);
        recordMapper.insert(record);

        seedAnswerRows(studentId, sessionId, recordId, planId, ver, planRowId, now);

        String ctxKey = contextRedis.seedFromStart(
                studentId,
                recordId,
                sessionId,
                chatSessionId,
                planId,
                ver,
                planRowId,
                questionCount
        );

        return Map.of(
                "interview_session_id", sessionId,
                "plan_id", planId,
                "plan_version", ver,
                "record_id", recordId,
                "status", "ready",
                "ctx_key", ctxKey
        );
    }

    private InterviewPlanBasicsEntity loadOwnedBasics(String studentId, String planId, Integer version) {
        if (planId == null || planId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "plan_id 不能为空");
        }
        String pid = planId.trim();
        InterviewPlanBasicsEntity basics;
        if (version != null && version > 0) {
            basics = basicsMapper.selectById(InterviewIds.planRowId(pid, version));
        } else {
            var rows = basicsMapper.selectList(
                    com.baomidou.mybatisplus.core.toolkit.Wrappers.<InterviewPlanBasicsEntity>lambdaQuery()
                            .eq(InterviewPlanBasicsEntity::getPlanId, pid)
                            .orderByDesc(InterviewPlanBasicsEntity::getVersion)
                            .last("LIMIT 1")
            );
            basics = rows.isEmpty() ? null : rows.get(0);
        }
        if (basics == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "大纲不存在或未同步至题库，请稍后重试");
        }
        String owner = basics.getStudentId();
        if (owner != null && !owner.isBlank() && !studentId.equals(owner)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权使用该大纲");
        }
        return basics;
    }

    private void persistModuleTags(String planRowId, JsonNode categories) {
        if (categories == null || !categories.isArray()) {
            return;
        }
        int sort = 0;
        for (JsonNode cat : categories) {
            String name = cat.asText("").trim();
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

    /** 按大纲题目预生成 pending 答题行，供 turn 更新 */
    private void seedAnswerRows(
            String studentId,
            String sessionId,
            String recordId,
            String planId,
            int version,
            String planRowId,
            LocalDateTime now
    ) {
        var questions = questionMapper.selectList(
                com.baomidou.mybatisplus.core.toolkit.Wrappers.<InterviewPlanQuestionEntity>lambdaQuery()
                        .eq(InterviewPlanQuestionEntity::getPlanRowId, planRowId)
                        .orderByAsc(InterviewPlanQuestionEntity::getSeqNo)
        );
        for (InterviewPlanQuestionEntity q : questions) {
            StudentInterviewAnswerEntity ans = new StudentInterviewAnswerEntity();
            ans.setAnswerRowId(InterviewIds.newAnswerRowId());
            ans.setInterviewSessionId(sessionId);
            ans.setStudentId(studentId);
            ans.setRecordId(recordId);
            ans.setPlanId(planId);
            ans.setPlanVersion(version);
            ans.setIqRowId(q.getIqRowId());
            ans.setQuestionId(q.getQuestionId());
            ans.setSeqNo(q.getSeqNo());
            ans.setAnswerStatus("pending");
            ans.setEvaluatorComment("");
            ans.setCreatedAt(now);
            answerMapper.insert(ans);
        }
    }
}
