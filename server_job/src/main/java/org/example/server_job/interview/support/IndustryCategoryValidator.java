package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.interview.dto.InterviewIndustryCategorySaveRequest;
import org.example.server_job.interview.entity.InterviewIndustryCategoryEntity;
import org.example.server_job.interview.entity.InterviewPlanBasicsEntity;
import org.example.server_job.interview.mapper.InterviewIndustryCategoryMapper;
import org.example.server_job.interview.mapper.InterviewPlanBasicsMapper;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

/**
 * 行业分类写入前的业务校验。
 */
@Component
public class IndustryCategoryValidator {

    private final InterviewIndustryCategoryMapper categoryMapper;
    private final InterviewPlanBasicsMapper planBasicsMapper;

    public IndustryCategoryValidator(
            InterviewIndustryCategoryMapper categoryMapper,
            InterviewPlanBasicsMapper planBasicsMapper
    ) {
        this.categoryMapper = categoryMapper;
        this.planBasicsMapper = planBasicsMapper;
    }

    public InterviewIndustryCategoryEntity requireExists(String categoryId) {
        if (categoryId == null || categoryId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "category_id 不能为空");
        }
        InterviewIndustryCategoryEntity row = categoryMapper.selectById(categoryId.trim());
        if (row == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "行业分类不存在");
        }
        return row;
    }

    public void validateSave(InterviewIndustryCategorySaveRequest req, boolean isUpdate) {
        if (req == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请求体不能为空");
        }
        int level = req.level() == null ? 0 : req.level();
        if (level != 1 && level != 2) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "level 必须为 1 或 2");
        }
        if (req.categoryCode() == null || req.categoryCode().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "category_code 不能为空");
        }
        if (req.categoryName() == null || req.categoryName().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "category_name 不能为空");
        }
        if (level == 1 && req.parentId() != null && !req.parentId().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "一级分类不能有 parent_id");
        }
        if (level == 2) {
            if (req.parentId() == null || req.parentId().isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "二级分类必须指定 parent_id");
            }
            InterviewIndustryCategoryEntity parent = categoryMapper.selectById(req.parentId().trim());
            if (parent == null || parent.getLevel() == null || parent.getLevel() != 1) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "parent_id 必须指向有效的一级分类");
            }
        }
        if (!isUpdate && req.categoryId() != null && !req.categoryId().isBlank()) {
            if (categoryMapper.selectById(req.categoryId().trim()) != null) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "category_id 已存在");
            }
        }
    }

    public void ensureCanDelete(InterviewIndustryCategoryEntity row) {
        long childCount = categoryMapper.selectCount(
                Wrappers.<InterviewIndustryCategoryEntity>lambdaQuery()
                        .eq(InterviewIndustryCategoryEntity::getParentId, row.getCategoryId())
        );
        if (childCount > 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "请先删除其下二级分类");
        }
        if (row.getLevel() != null && row.getLevel() == 2) {
            long planRef = planBasicsMapper.selectCount(
                    Wrappers.<InterviewPlanBasicsEntity>lambdaQuery()
                            .eq(InterviewPlanBasicsEntity::getIndustryCategoryId, row.getCategoryId())
            );
            if (planRef > 0) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "已有面试大纲引用该行业，无法删除");
            }
        }
    }
}
