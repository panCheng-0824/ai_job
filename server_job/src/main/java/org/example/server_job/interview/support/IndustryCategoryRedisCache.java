package org.example.server_job.interview.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.server_job.client.redis.RedisStringClient;
import org.example.server_job.interview.entity.InterviewIndustryCategoryEntity;
import org.example.server_job.interview.mapper.InterviewIndustryCategoryMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 行业分类 Redis 缓存：top_category 一级桶 + 各一级 id 二级桶。
 * CRUD 后全量重建，供 ai_job 两阶段大纲行业识别读取。
 */
@Component
public class IndustryCategoryRedisCache {

    private static final Logger log = LoggerFactory.getLogger(IndustryCategoryRedisCache.class);

    private final InterviewIndustryCategoryMapper categoryMapper;
    private final IndustryCategorySupport support;
    private final RedisStringClient redis;
    private final ObjectMapper objectMapper;

    public IndustryCategoryRedisCache(
            InterviewIndustryCategoryMapper categoryMapper,
            IndustryCategorySupport support,
            RedisStringClient redis,
            ObjectMapper objectMapper
    ) {
        this.categoryMapper = categoryMapper;
        this.support = support;
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

    /** 从 DB 全量重建 Redis 行业桶 */
    public void rebuildAll() {
        List<InterviewIndustryCategoryEntity> level1Rows = categoryMapper.selectList(
                Wrappers.<InterviewIndustryCategoryEntity>lambdaQuery()
                        .eq(InterviewIndustryCategoryEntity::getLevel, 1)
                        .eq(InterviewIndustryCategoryEntity::getStatus, "active")
                        .eq(InterviewIndustryCategoryEntity::getEnabledForClassify, 1)
                        .orderByAsc(InterviewIndustryCategoryEntity::getSortNo)
        );

        List<Map<String, Object>> topItems = new ArrayList<>();
        for (InterviewIndustryCategoryEntity l1 : level1Rows) {
            topItems.add(toClassifyItem(l1));
            rebuildLevel2Bucket(l1.getCategoryId());
        }

        writeBucket(IndustryCategoryRedisKeys.TOP_CATEGORY, Map.of(
                "bucket", "top_category",
                "level", 1,
                "items", topItems,
                "count", topItems.size(),
                "updated_at", LocalDateTime.now().toString()
        ));
        log.info("行业分类 Redis 缓存已重建：一级 {} 个", topItems.size());
    }

    /** 删除一级类目时清理其二级桶 */
    public void deleteLevel2Bucket(String level1CategoryId) {
        if (level1CategoryId != null && !level1CategoryId.isBlank()) {
            redis.delete(IndustryCategoryRedisKeys.level2Bucket(level1CategoryId.trim()));
        }
    }

    public Optional<Map<String, Object>> readTopBucket() {
        return readBucket(IndustryCategoryRedisKeys.TOP_CATEGORY);
    }

    public Optional<Map<String, Object>> readLevel2Bucket(String level1CategoryId) {
        if (level1CategoryId == null || level1CategoryId.isBlank()) {
            return Optional.empty();
        }
        return readBucket(IndustryCategoryRedisKeys.level2Bucket(level1CategoryId.trim()));
    }

    private void rebuildLevel2Bucket(String level1CategoryId) {
        List<InterviewIndustryCategoryEntity> l2Rows = categoryMapper.selectList(
                Wrappers.<InterviewIndustryCategoryEntity>lambdaQuery()
                        .eq(InterviewIndustryCategoryEntity::getLevel, 2)
                        .eq(InterviewIndustryCategoryEntity::getParentId, level1CategoryId)
                        .eq(InterviewIndustryCategoryEntity::getStatus, "active")
                        .eq(InterviewIndustryCategoryEntity::getEnabledForClassify, 1)
                        .orderByAsc(InterviewIndustryCategoryEntity::getSortNo)
        );
        List<Map<String, Object>> items = new ArrayList<>();
        for (InterviewIndustryCategoryEntity row : l2Rows) {
            items.add(toClassifyItem(row));
        }
        writeBucket(IndustryCategoryRedisKeys.level2Bucket(level1CategoryId), Map.of(
                "bucket", "level2",
                "parent_id", level1CategoryId,
                "level", 2,
                "items", items,
                "count", items.size(),
                "updated_at", LocalDateTime.now().toString()
        ));
    }

    /** 精简字段，降低 LLM Prompt 体积 */
    private Map<String, Object> toClassifyItem(InterviewIndustryCategoryEntity row) {
        Map<String, Object> slim = new LinkedHashMap<>();
        slim.put("category_id", row.getCategoryId());
        slim.put("category_code", row.getCategoryCode());
        slim.put("category_name", row.getCategoryName());
        slim.put("description", row.getDescription());
        slim.put("intent_keywords", row.getIntentKeywords());
        slim.put("level", row.getLevel());
        if (row.getParentId() != null) {
            slim.put("parent_id", row.getParentId());
        }
        return slim;
    }

    private void writeBucket(String key, Map<String, Object> payload) {
        try {
            redis.set(key, objectMapper.writeValueAsString(payload));
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("行业分类 Redis 序列化失败: " + key, e);
        }
    }

    @SuppressWarnings("unchecked")
    private Optional<Map<String, Object>> readBucket(String key) {
        String raw = redis.get(key);
        if (raw == null || raw.isBlank()) {
            return Optional.empty();
        }
        try {
            return Optional.of(objectMapper.readValue(raw, Map.class));
        } catch (JsonProcessingException e) {
            log.warn("行业分类 Redis 反序列化失败 key={}: {}", key, e.getMessage());
            return Optional.empty();
        }
    }
}
