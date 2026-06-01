package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.interview.dto.InterviewPlanQuestionSaveItem;
import org.example.server_job.interview.dto.InterviewPlanSaveRequest;
import org.example.server_job.interview.entity.InterviewIndustryCategoryEntity;
import org.example.server_job.interview.entity.InterviewPlanBasicsEntity;
import org.example.server_job.interview.entity.InterviewSessionEntity;
import org.example.server_job.interview.mapper.InterviewIndustryCategoryMapper;
import org.example.server_job.interview.mapper.InterviewPlanBasicsMapper;
import org.example.server_job.interview.mapper.InterviewSessionMapper;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

/**
 * 大纲写入前的业务校验：仅允许绑定二级行业。
 */
@Component
public class InterviewPlanWriteValidator {

    private final InterviewIndustryCategoryMapper industryMapper;
    private final InterviewPlanBasicsMapper basicsMapper;
    private final InterviewSessionMapper sessionMapper;

    public InterviewPlanWriteValidator(
            InterviewIndustryCategoryMapper industryMapper,
            InterviewPlanBasicsMapper basicsMapper,
            InterviewSessionMapper sessionMapper
    ) {
        this.industryMapper = industryMapper;
        this.basicsMapper = basicsMapper;
        this.sessionMapper = sessionMapper;
    }

    public InterviewIndustryCategoryEntity requireLevel2Industry(String categoryId) {
        if (categoryId == null || categoryId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "industry_category_id 不能为空");
        }
        InterviewIndustryCategoryEntity cat = industryMapper.selectById(categoryId.trim());
        if (cat == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "行业分类不存在");
        }
        if (cat.getLevel() == null || cat.getLevel() != 2) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "题目大纲只能绑定二级行业分类");
        }
        if (!"active".equalsIgnoreCase(String.valueOf(cat.getStatus()))) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "行业分类已停用，无法绑定大纲");
        }
        return cat;
    }

    public void validateSave(InterviewPlanSaveRequest req, boolean isCreate) {
        if (req == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请求体不能为空");
        }
        requireLevel2Industry(req.industryCategoryId());
        if (req.title() == null || req.title().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "title 不能为空");
        }
        if (req.questions() == null || req.questions().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "至少需要一道题目");
        }
        int seq = 0;
        for (InterviewPlanQuestionSaveItem q : req.questions()) {
            if (q == null || q.text() == null || q.text().isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "题目内容不能为空");
            }
            seq++;
        }
        if (isCreate && req.planId() != null && !req.planId().isBlank()) {
            long exists = basicsMapper.selectCount(
                    Wrappers.<InterviewPlanBasicsEntity>lambdaQuery()
                            .eq(InterviewPlanBasicsEntity::getPlanId, req.planId().trim())
            );
            if (exists > 0) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "plan_id 已存在");
            }
        }
    }

    public InterviewPlanBasicsEntity requireOwnedPlan(String studentId, String planId) {
        if (planId == null || planId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "plan_id 不能为空");
        }
        var rows = basicsMapper.selectList(
                Wrappers.<InterviewPlanBasicsEntity>lambdaQuery()
                        .eq(InterviewPlanBasicsEntity::getPlanId, planId.trim())
                        .orderByDesc(InterviewPlanBasicsEntity::getVersion)
                        .last("LIMIT 1")
        );
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "大纲不存在");
        }
        InterviewPlanBasicsEntity row = rows.get(0);
        if (!studentId.equals(row.getStudentId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权操作该大纲");
        }
        return row;
    }

    public void ensureCanDelete(String planId) {
        long sessionRef = sessionMapper.selectCount(
                Wrappers.<InterviewSessionEntity>lambdaQuery()
                        .eq(InterviewSessionEntity::getPlanId, planId)
        );
        if (sessionRef > 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "已有面试会话引用该大纲，无法删除");
        }
    }
}
