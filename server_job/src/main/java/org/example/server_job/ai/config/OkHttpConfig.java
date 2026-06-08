package org.example.server_job.ai.config;

import okhttp3.OkHttpClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

@Configuration
public class OkHttpConfig {

    /**
     * 调用 ai_job 的 HTTP 客户端。
     * RAG 同步（LightRAG insert）在 ai_job 侧可能含 LLM 清洗 + 最长 600s 文档处理轮询，
     * read-timeout 需明显大于原 120s，否则会出现 Read timed out 但 ai_job 仍在后台处理。
     */
    @Bean
    public OkHttpClient okHttpClient(
            @Value("${ai-job.http.connect-timeout:8s}") Duration connectTimeout,
            @Value("${ai-job.http.read-timeout:15m}") Duration readTimeout,
            @Value("${ai-job.http.write-timeout:2m}") Duration writeTimeout
    ) {
        return new OkHttpClient.Builder()
                .connectTimeout(connectTimeout)
                .readTimeout(readTimeout)
                .writeTimeout(writeTimeout)
                .build();
    }
}
