package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import org.example.server_job.interview.entity.InterviewPlanBasicsEntity;
import org.example.server_job.interview.entity.InterviewPlanModuleTagEntity;
import org.example.server_job.interview.mapper.InterviewPlanBasicsMapper;
import org.example.server_job.interview.mapper.InterviewPlanModuleTagMapper;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * MQ {@code interview.plan.result} 落库 V2 大纲关系表（不含会话/学生记录）。
 *
 * <p>写入范围：基础信息、模块标签、题目主表及维度/追问/评分子表。
 */
@Component
public class InterviewPlanBankWriteSupport {

    private final InterviewPlanBasicsMapper basicsMapper;
    private final InterviewPlanModuleTagMapper tagMapper;
    private final InterviewPlanQuestionJsonWriteSupport questionJsonWriteSupport;

    public InterviewPlanBankWriteSupport(
            InterviewPlanBasicsMapper basicsMapper,
            InterviewPlanModuleTagMapper tagMapper,
            InterviewPlanQuestionJsonWriteSupport questionJsonWriteSupport
    ) {
        this.basicsMapper = basicsMapper;
        this.tagMapper = tagMapper;
        this.questionJsonWriteSupport = questionJsonWriteSupport;
    }

    /**
     * 幂等写入 V2 大纲；已存在同 plan_row_id 时跳过。
     *
     * @return true 表示已存在或新写入成功；false 表示 payload 不完整未处理
     */
    public boolean insertFromMqPayload(JsonNode payload) {
        JsonNode planNode = payload.path("plan");
        if (planNode.isMissingNode() || !planNode.isObject()) {
            return false;
        }
        String planId = planNode.path("plan_id").asText("");
        if (planId.isBlank()) {
            return false;
        }
        int version = planNode.path("version").asInt(1);
        String planRowId = InterviewIds.planRowId(planId, version);

        long exists = basicsMapper.selectCount(
                new LambdaQueryWrapper<InterviewPlanBasicsEntity>()
                        .eq(InterviewPlanBasicsEntity::getPlanRowId, planRowId)
        );
        if (exists > 0) {
            return true;
        }

        LocalDateTime now = LocalDateTime.now();
        JsonNode summaryNode = payload.path("plan_summary");
        JsonNode classifyNode = payload.path("industry_classification");

        String targetRole = planNode.path("target_role").asText(text(payload, "target_role"));
        String industryCategoryId = resolveIndustryCategoryId(payload, planNode);

        InterviewPlanBasicsEntity basics = new InterviewPlanBasicsEntity();
        basics.setPlanRowId(planRowId);
        basics.setPlanId(planId);
        basics.setVersion(version);
        basics.setTitle(targetRole.isBlank() ? planId : targetRole);
        basics.setTargetRole(targetRole);
        basics.setSourceMaterialHash(planNode.path("source_material_hash").asText(
                text(payload, "material_hash")
        ));
        basics.setRubricVersion(planNode.path("rubric_version").asText("v1"));
        basics.setPlannerModel(planNode.path("planner_model").asText(""));
        basics.setIndustryCategoryId(blankToNull(industryCategoryId));
        applyIndustryClassification(basics, classifyNode, now);
        basics.setVisibility("private");
        basics.setStatus("draft");
        basics.setStudentId(blankToNull(text(payload, "student_id")));
        basics.setCacheHitId(resolveCacheHitId(payload));
        basics.setCreatedAt(now);
        basics.setUpdatedAt(now);

        if (summaryNode.isObject()) {
            basics.setIntroduction(summaryNode.path("introduction").asText(""));
            basics.setSuitableAudience(summaryNode.path("suitable_audience").asText(""));
            persistModuleTags(planRowId, summaryNode.path("interview_categories"));
        }

        // 题目主表 + dimensions / preset_followups / eval_criteria 子表
        int questionCount = questionJsonWriteSupport.insertQuestionsFromJson(
                planRowId, planId, version, planNode.path("questions"), now
        );
        basics.setQuestionCount(questionCount);
        basicsMapper.insert(basics);
        return true;
    }

    /** 优先 payload 顶层，其次 plan.industry_category_id */
    private static String resolveIndustryCategoryId(JsonNode payload, JsonNode planNode) {
        String fromPayload = text(payload, "industry_category_id");
        if (!fromPayload.isBlank()) {
            return fromPayload.trim();
        }
        return planNode.path("industry_category_id").asText("").trim();
    }

    private static void applyIndustryClassification(
            InterviewPlanBasicsEntity basics,
            JsonNode classifyNode,
            LocalDateTime now
    ) {
        if (basics.getIndustryCategoryId() == null || basics.getIndustryCategoryId().isBlank()) {
            return;
        }
        if (classifyNode != null && classifyNode.isObject()) {
            double confidence = classifyNode.path("confidence").asDouble(0.0);
            basics.setIndustryClassifyConfidence(BigDecimal.valueOf(confidence));
            basics.setIndustryClassifyReason(classifyNode.path("reason").asText(""));
            String source = classifyNode.path("source").asText("");
            basics.setIndustryClassifySource(source.isBlank() ? "redis_two_stage_llm" : source);
        } else {
            basics.setIndustryClassifySource("auto");
        }
        basics.setIndustryClassifiedAt(now);
    }

    private static String resolveCacheHitId(JsonNode payload) {
        JsonNode cacheMeta = payload.path("cache_meta");
        if (cacheMeta.isObject() && cacheMeta.hasNonNull("cache_hit_id")) {
            String id = cacheMeta.path("cache_hit_id").asText("");
            return id.isBlank() ? null : id;
        }
        return null;
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

    private static String text(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return v == null || v.isNull() ? "" : v.asText("");
    }

    private static String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}
