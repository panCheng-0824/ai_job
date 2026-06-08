package org.example.server_job.biz.support;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

/**
 * 应用启动时预热系统字典 Redis 桶。
 */
@Component
public class SysCodeCacheWarmRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(SysCodeCacheWarmRunner.class);

    private final SysCodeRedisCache sysCodeRedisCache;

    public SysCodeCacheWarmRunner(SysCodeRedisCache sysCodeRedisCache) {
        this.sysCodeRedisCache = sysCodeRedisCache;
    }

    @Override
    public void run(ApplicationArguments args) {
        try {
            sysCodeRedisCache.rebuildAll();
        } catch (Exception e) {
            log.warn("系统字典 Redis 预热失败（可稍后随 CRUD 触发重建）: {}", e.getMessage());
        }
    }
}
