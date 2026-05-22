package org.example.server_job.client.redis;

import java.time.Duration;

/**
 * 基于 Redis 的字符串读写封装，业务层只依赖本接口，由 Spring 注入已配置的实现。
 */
public interface RedisStringClient {

    String get(String key);

    void set(String key, String value);

    void set(String key, String value, Duration ttl);

    boolean delete(String key);
}
