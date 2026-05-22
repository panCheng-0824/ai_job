package org.example.server_job.cfgTest.service;

import org.example.server_job.cfgTest.DemoResult;
import org.example.server_job.client.redis.RedisStringClient;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class RedisDemoService implements MiddlewareDemoService {

    private final RedisStringClient redis;

    public RedisDemoService(RedisStringClient redis) {
        this.redis = redis;
    }

    @Override
    public String middleware() {
        return "redis";
    }

    @Override
    public Map<String, Object> runDemo() {
        String key = "middleware:demo:redis:key";
        String value = "redis-demo-" + UUID.randomUUID();
        redis.set(key, value);
        String cached = redis.get(key);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("key", key);
        data.put("writtenValue", value);
        data.put("readValue", cached);
        return DemoResult.ok(data);
    }
}
