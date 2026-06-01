package org.example.server_job.interview.support;

/**
 * 行业分类 Redis 键规范（供 ai_job 大纲分类两阶段识别读取）。
 *
 * <p>桶结构：
 * <ul>
 *   <li>{@link #TOP_CATEGORY} — 全部一级类目（enabled_for_classify + active）</li>
 *   <li>一级 {@code category_id} — 该一级下全部二级类目桶</li>
 * </ul>
 */
public final class IndustryCategoryRedisKeys {

    /** 一级行业类目总桶 key */
    public static final String TOP_CATEGORY = "top_category";

    private IndustryCategoryRedisKeys() {
    }

    /**
     * 二级行业桶 key：与一级 category_id 相同（业务 id 均带 ind_ 前缀，避免与其他 Redis 键冲突）。
     */
    public static String level2Bucket(String level1CategoryId) {
        return level1CategoryId;
    }
}
