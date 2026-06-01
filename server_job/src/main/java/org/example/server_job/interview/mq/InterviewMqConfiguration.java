package org.example.server_job.interview.mq;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * 注册面试 MQ 配置属性。
 */
@Configuration
@EnableConfigurationProperties(InterviewMqProperties.class)
public class InterviewMqConfiguration {
}
