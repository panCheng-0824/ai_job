package org.example.server_job.interview.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.example.server_job.interview.dto.InterviewIndustryCategorySaveRequest;
import org.example.server_job.interview.entity.InterviewIndustryCategoryEntity;
import org.example.server_job.interview.mapper.InterviewIndustryCategoryMapper;
import org.example.server_job.interview.service.InterviewIndustryCategoryService;
import org.example.server_job.interview.support.IndustryCategoryRedisCache;
import org.example.server_job.interview.support.IndustryCategorySupport;
import org.example.server_job.interview.support.IndustryCategoryValidator;
import org.example.server_job.interview.support.InterviewIndustryCategoryTreeBuilder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 行业分类 CRUD 与字典查询实现。
 */
@Service
public class InterviewIndustryCategoryServiceImpl implements InterviewIndustryCategoryService {

    private final InterviewIndustryCategoryMapper categoryMapper;
    private final InterviewIndustryCategoryTreeBuilder treeBuilder;
    private final IndustryCategorySupport support;
    private final IndustryCategoryValidator validator;
    private final IndustryCategoryRedisCache industryRedisCache;

    public InterviewIndustryCategoryServiceImpl(
            InterviewIndustryCategoryMapper categoryMapper,
            InterviewIndustryCategoryTreeBuilder treeBuilder,
            IndustryCategorySupport support,
            IndustryCategoryValidator validator,
            IndustryCategoryRedisCache industryRedisCache
    ) {
        this.categoryMapper = categoryMapper;
        this.treeBuilder = treeBuilder;
        this.support = support;
        this.validator = validator;
        this.industryRedisCache = industryRedisCache;
    }

    @Override
    public Map<String, Object> listCategories(String purpose, boolean tree, boolean includeAll) {
        var query = Wrappers.<InterviewIndustryCategoryEntity>lambdaQuery()
                .orderByAsc(InterviewIndustryCategoryEntity::getLevel)
                .orderByAsc(InterviewIndustryCategoryEntity::getSortNo);
        if (!includeAll) {
            query.eq(InterviewIndustryCategoryEntity::getStatus, "active");
        }
        if ("intent".equalsIgnoreCase(purpose)) {
            query.eq(InterviewIndustryCategoryEntity::getEnabledForIntent, 1);
        } else if ("classify".equalsIgnoreCase(purpose)) {
            query.eq(InterviewIndustryCategoryEntity::getEnabledForClassify, 1);
        }
        List<Map<String, Object>> items = mapRows(categoryMapper.selectList(query));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("items", tree ? treeBuilder.buildTree(items) : items);
        out.put("count", items.size());
        return out;
    }

    @Override
    public Map<String, Object> getDetail(String categoryId) {
        InterviewIndustryCategoryEntity row = validator.requireExists(categoryId);
        Map<String, Object> out = new LinkedHashMap<>(support.toItem(row));
        if (row.getLevel() != null && row.getLevel() == 2 && row.getParentId() != null) {
            InterviewIndustryCategoryEntity parent = categoryMapper.selectById(row.getParentId());
            if (parent != null) {
                out.put("parent_name", parent.getCategoryName());
            }
        }
        if (row.getLevel() != null && row.getLevel() == 1) {
            long childCount = categoryMapper.selectCount(
                    Wrappers.<InterviewIndustryCategoryEntity>lambdaQuery()
                            .eq(InterviewIndustryCategoryEntity::getParentId, row.getCategoryId())
            );
            out.put("child_count", childCount);
        }
        return out;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> create(InterviewIndustryCategorySaveRequest request) {
        validator.validateSave(request, false);
        LocalDateTime now = LocalDateTime.now();
        InterviewIndustryCategoryEntity row = fromRequest(request, null);
        if (row.getCategoryId() == null || row.getCategoryId().isBlank()) {
            row.setCategoryId(support.buildCategoryId(row.getCategoryCode()));
        }
        if (categoryMapper.selectById(row.getCategoryId()) != null) {
            row.setCategoryId(row.getCategoryId() + "_" + System.currentTimeMillis() % 10000);
        }
        row.setCreatedAt(now);
        row.setUpdatedAt(now);
        categoryMapper.insert(row);
        refreshIndustryRedis(row);
        return Map.of("category_id", row.getCategoryId(), "item", support.toItem(row));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> update(String categoryId, InterviewIndustryCategorySaveRequest request) {
        InterviewIndustryCategoryEntity existing = validator.requireExists(categoryId);
        validator.validateSave(request, true);
        InterviewIndustryCategoryEntity row = fromRequest(request, existing);
        row.setCategoryId(existing.getCategoryId());
        row.setCreatedAt(existing.getCreatedAt());
        row.setUpdatedAt(LocalDateTime.now());
        categoryMapper.updateById(row);
        refreshIndustryRedis(row);
        return Map.of("category_id", row.getCategoryId(), "item", support.toItem(row));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> delete(String categoryId) {
        InterviewIndustryCategoryEntity row = validator.requireExists(categoryId);
        validator.ensureCanDelete(row);
        if (row.getLevel() != null && row.getLevel() == 1) {
            industryRedisCache.deleteLevel2Bucket(row.getCategoryId());
        }
        categoryMapper.deleteById(row.getCategoryId());
        refreshIndustryRedis(null);
        return Map.of("deleted", true, "category_id", row.getCategoryId());
    }

    /** 行业 CRUD 后重建 Redis 分类桶 */
    private void refreshIndustryRedis(InterviewIndustryCategoryEntity row) {
        try {
            industryRedisCache.rebuildAll();
        } catch (Exception e) {
            // 不阻断主流程；ai_job 可回退 HTTP 拉取 DB
            org.slf4j.LoggerFactory.getLogger(getClass())
                    .warn("行业分类 Redis 重建失败 category={}: {}", row != null ? row.getCategoryId() : "-", e.getMessage());
        }
    }

    private List<Map<String, Object>> mapRows(List<InterviewIndustryCategoryEntity> rows) {
        List<Map<String, Object>> items = new ArrayList<>();
        for (InterviewIndustryCategoryEntity row : rows) {
            items.add(support.toItem(row));
        }
        return items;
    }

    private InterviewIndustryCategoryEntity fromRequest(
            InterviewIndustryCategorySaveRequest req,
            InterviewIndustryCategoryEntity existing
    ) {
        InterviewIndustryCategoryEntity row = new InterviewIndustryCategoryEntity();
        row.setCategoryId(trimOrNull(req.categoryId()));
        row.setLevel(req.level());
        row.setCategoryCode(req.categoryCode().trim());
        row.setCategoryName(req.categoryName().trim());
        row.setDescription(nullToEmpty(req.description()));
        row.setIntentKeywords(nullToEmpty(req.intentKeywords()));
        row.setEnabledForIntent(boolToInt(req.enabledForIntent(), true));
        row.setEnabledForClassify(boolToInt(req.enabledForClassify(), true));
        row.setSortNo(req.sortNo() != null ? req.sortNo() : 0);
        row.setStatus(normalizeStatus(req.status(), existing));

        if (req.level() != null && req.level() == 1) {
            row.setParentId(null);
        } else {
            row.setParentId(trimOrNull(req.parentId()));
        }
        return row;
    }

    private static String normalizeStatus(String status, InterviewIndustryCategoryEntity existing) {
        if (status != null && !status.isBlank()) {
            return "disabled".equalsIgnoreCase(status.trim()) ? "disabled" : "active";
        }
        return existing != null && existing.getStatus() != null ? existing.getStatus() : "active";
    }

    private static int boolToInt(Boolean v, boolean defaultVal) {
        if (v == null) {
            return defaultVal ? 1 : 0;
        }
        return Boolean.TRUE.equals(v) ? 1 : 0;
    }

    private static String nullToEmpty(String v) {
        return v == null ? "" : v.trim();
    }

    private static String trimOrNull(String v) {
        if (v == null || v.isBlank()) {
            return null;
        }
        return v.trim();
    }
}
