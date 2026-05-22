package org.example.server_job.client.redis;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.StringRedisTemplate;

@Configuration
public class RedisClientConfiguration {

    @Bean
    public RedisStringClient redisStringClient(StringRedisTemplate stringRedisTemplate) {
        return new SpringDataRedisStringClient(stringRedisTemplate);
    }
}
