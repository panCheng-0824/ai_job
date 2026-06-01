package org.example.server_job.interview.support;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

/**
 * 应用启动时预热行业分类 Redis 桶。
 */
@Component
public class IndustryCategoryCacheWarmRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(IndustryCategoryCacheWarmRunner.class);

    private final IndustryCategoryRedisCache industryRedisCache;

    public IndustryCategoryCacheWarmRunner(IndustryCategoryRedisCache industryRedisCache) {
        this.industryRedisCache = industryRedisCache;
    }

    @Override
    public void run(ApplicationArguments args) {
        try {
            industryRedisCache.rebuildAll();
        } catch (Exception e) {
            log.warn("行业分类 Redis 预热失败（可稍后随 CRUD 或内部 API 触发重建）: {}", e.getMessage());
        }
    }
}
