package org.example.server_job.interview.mq;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.client.core.RocketMQClientTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * 向 {@link InterviewMqTopics#AI_TASK} 投递异步 AI 任务（Reflection、异步规划等）。
 *
 * <p>经 Proxy gRPC 发送，配置见 {@code rocketmq.producer.endpoints}。
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "interview.mq", name = "enabled", havingValue = "true", matchIfMissing = true)
public class InterviewAiTaskProducer {

    private final RocketMQClientTemplate rocketMQClientTemplate;
    private final InterviewMqProperties mqProperties;

    /**
     * 发送 JSON 信封（与 ai_job MqEnvelope 字段对齐）。
     */
    public void sendTaskJson(String jsonBody) {
        String topic = mqProperties.getTopics().getAiTask();
        rocketMQClientTemplate.syncSendNormalMessage(topic, jsonBody);
        log.info(
                "MQ 已投递 topic={} grpc={}",
                topic,
                mqProperties.getProxyGrpcEndpoint()
        );
    }
}
