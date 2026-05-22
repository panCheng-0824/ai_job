package org.example.server_job.client.redis;

import org.springframework.data.redis.core.StringRedisTemplate;

import java.time.Duration;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

/**
 * 使用 Spring Data 的 {@link StringRedisTemplate} 实现 {@link RedisStringClient}。
 */
public class SpringDataRedisStringClient implements RedisStringClient {

    private final StringRedisTemplate template;

    public SpringDataRedisStringClient(StringRedisTemplate template) {
        this.template = Objects.requireNonNull(template, "template");
    }

    @Override
    public String get(String key) {
        return template.opsForValue().get(key);
    }

    @Override
    public void set(String key, String value) {
        template.opsForValue().set(key, value);
    }

    @Override
    public void set(String key, String value, Duration ttl) {
        if (ttl == null || ttl.isNegative() || ttl.isZero()) {
            set(key, value);
            return;
        }
        template.opsForValue().set(key, value, ttl.toMillis(), TimeUnit.MILLISECONDS);
    }

    @Override
    public boolean delete(String key) {
        Boolean removed = template.delete(key);
        return Boolean.TRUE.equals(removed);
    }
}
