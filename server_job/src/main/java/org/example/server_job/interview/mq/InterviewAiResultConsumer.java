package org.example.server_job.interview.mq;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.client.annotation.RocketMQMessageListener;
import org.apache.rocketmq.client.apis.ClientConfiguration;
import org.apache.rocketmq.client.apis.consumer.ConsumeResult;
import org.apache.rocketmq.client.apis.consumer.PushConsumerBuilder;
import org.apache.rocketmq.client.apis.message.MessageView;
import org.apache.rocketmq.client.core.RocketMQListener;
import org.apache.rocketmq.client.core.RocketMQPushConsumerLifecycleListener;
import org.example.server_job.interview.mq.InterviewQuestionResultPersistService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.time.Duration;

/**
 * 消费 {@link InterviewMqTopics#AI_RESULT}，将 AI 结构化结果落库。
 *
 * <p>使用 RocketMQ 5 gRPC 客户端（{@code rocketmq-v5-client-spring-boot-starter}），
 * 与 ai_job {@code ROCKETMQ_PROXY_GRPC_ENDPOINT} 对齐。
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "interview.mq", name = "enabled", havingValue = "true", matchIfMissing = true)
@ConditionalOnProperty(prefix = "interview.mq", name = "consumer-enabled", havingValue = "true", matchIfMissing = true)
@RocketMQMessageListener(
        topic = "${interview.mq.topics.ai-result}",
        consumerGroup = "${interview.mq.consumer-groups.ai-result}",
        endpoints = "${rocketmq.push-consumer.endpoints}",
        tag = "*"
)
public class InterviewAiResultConsumer implements RocketMQListener, RocketMQPushConsumerLifecycleListener {

    private final InterviewMqConsumeLogService consumeLogService;
    private final InterviewPlanBankPersistService planBankPersistService;
    private final InterviewQuestionResultPersistService questionResultPersistService;
    private final InterviewMqProperties mqProperties;

    /**
     * 2.3.x 注解无法配置 {@code sslEnabled}，在构建 PushConsumer 前覆盖 ClientConfiguration。
     */
    @Override
    public void prepareStart(PushConsumerBuilder pushConsumerBuilder) {
        ClientConfiguration config = ClientConfiguration.newBuilder()
                .setEndpoints(mqProperties.getProxyGrpcEndpoint())
                .setRequestTimeout(Duration.ofSeconds(10))
                .enableSsl(mqProperties.isSslEnabled())
                .build();
        pushConsumerBuilder.setClientConfiguration(config);
        log.info(
                "PushConsumer 已配置 endpoints={} ssl={}",
                mqProperties.getProxyGrpcEndpoint(),
                mqProperties.isSslEnabled()
        );
    }

    @Override
    public ConsumeResult consume(MessageView messageView) {
        String message = StandardCharsets.UTF_8.decode(messageView.getBody()).toString();
        log.info("收到 interview_ai_result 消息 length={},length={}", message.length(),message);
        consumeLogService.recordIfNew(message);
        planBankPersistService.tryPersistFromEnvelopeJson(message);
        questionResultPersistService.tryPersistFromEnvelopeJson(message);
        // TODO: reflection.result / report.result 等其它事件
        return ConsumeResult.SUCCESS;
    }
}








