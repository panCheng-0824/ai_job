package org.example.server_job.interview.mq;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 面试 MQ 配置：Proxy 端点、Topic、消费组。
 */
@Data
@ConfigurationProperties(prefix = "interview.mq")
public class InterviewMqProperties {

    /** 是否启用 MQ 监听与投递 */
    private boolean enabled = true;

    /** 是否注册 {@code interview_ai_result} PushConsumer（Broker 未就绪时可先关） */
    private boolean consumerEnabled = true;

    /** Proxy HTTP/remoting（健康检查），如 localhost:18080 */
    private String proxyEndpoint = "localhost:18080";

    /** Proxy gRPC（生产/消费客户端），如 localhost:18081 */
    private String proxyGrpcEndpoint = "localhost:18081";

    /** gRPC 是否启用 TLS（本地 Proxy 一般为 false） */
    private boolean sslEnabled = false;

    private Topics topics = new Topics();
    private String producerGroup = "server_job_producer";
    private ConsumerGroups consumerGroups = new ConsumerGroups();

    @Data
    public static class Topics {
        private String aiTask = InterviewMqTopics.AI_TASK;
        private String aiResult = InterviewMqTopics.AI_RESULT;
        private String timerEvent = InterviewMqTopics.TIMER_EVENT;
        private String dlq = InterviewMqTopics.DLQ;
    }

    @Data
    public static class ConsumerGroups {
        /** 消费 ai_job_b 产出的 interview_ai_result */
        private String aiResult = "server_job_interview_result_consumer";
        /** 可选：server_job 自消费任务（调试） */
        private String aiTask = "server_job_interview_task_consumer";
    }
}
