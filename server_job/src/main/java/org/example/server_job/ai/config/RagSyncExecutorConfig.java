package org.example.server_job.ai.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

/**
 * 岗位同步 RAG 线程池：批量任务提交与单岗位内 LightRAG/GrepRAG 并行调用共用。
 * 默认核心线程 3，队列容量 {@link Integer#MAX_VALUE}（等价于不限制排队长度）。
 */
@Configuration
public class RagSyncExecutorConfig {

    @Bean(name = "ragSyncExecutor")
    public Executor ragSyncExecutor(
            @Value("${ai-job.rag.sync-thread-pool-core-size:3}") int corePoolSize
    ) {
        int core = Math.max(1, corePoolSize);
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(core);
        executor.setMaxPoolSize(core);
        executor.setQueueCapacity(Integer.MAX_VALUE);
        executor.setThreadNamePrefix("rag-sync-");
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(120);
        executor.initialize();
        return executor;
    }
}
