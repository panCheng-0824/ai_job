package org.example.server_job.interview.mq;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.apache.rocketmq.client.core.RocketMQClientTemplate;
import org.example.server_job.cfgTest.DemoResult;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/**
 * 面试 MQ 联调接口（仅开发/测试，生产请关闭或加鉴权）。
 */
@RestController
@RequestMapping("/demo/interview-mq")
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "interview.mq", name = "enabled", havingValue = "true", matchIfMissing = true)
public class InterviewMqDemoController {

    private final InterviewMqProperties mqProperties;
    private final InterviewAiTaskProducer taskProducer;
    private final RocketMQClientTemplate rocketMQClientTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @GetMapping("/config")
    public Map<String, Object> config() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("enabled", mqProperties.isEnabled());
        data.put("proxyEndpoint", mqProperties.getProxyEndpoint());
        data.put("proxyGrpcEndpoint", mqProperties.getProxyGrpcEndpoint());
        data.put("topics", mqProperties.getTopics());
        data.put("producerGroup", mqProperties.getProducerGroup());
        data.put("consumerGroups", mqProperties.getConsumerGroups());
        return DemoResult.ok(data);
    }

    /**
     * 向 {@code interview_ai_task} 投递测试信封（供 ai_job_b Worker 消费）。
     */
    @PostMapping(value = "/send-task", consumes = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> sendTask(@RequestBody(required = false) Map<String, Object> body) {
        try {
            String json = body == null || body.isEmpty()
                    ? defaultTaskEnvelopeJson()
                    : objectMapper.writeValueAsString(body);
            taskProducer.sendTaskJson(json);
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("topic", mqProperties.getTopics().getAiTask());
            data.put("proxyGrpcEndpoint", mqProperties.getProxyGrpcEndpoint());
            data.put("body", objectMapper.readValue(json, Map.class));
            return DemoResult.ok(data);
        } catch (Exception e) {
            return DemoResult.error(e.getMessage());
        }
    }

    /**
     * 向 {@code interview_ai_result} 投递测试信封（测 server_job 消费与幂等表）。
     */
    @PostMapping(value = "/send-result", consumes = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> sendResult(@RequestBody(required = false) Map<String, Object> body) {
        try {
            String json = body == null || body.isEmpty()
                    ? defaultResultEnvelopeJson()
                    : objectMapper.writeValueAsString(body);
            String topic = mqProperties.getTopics().getAiResult();
            rocketMQClientTemplate.syncSendNormalMessage(topic, json);
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("topic", topic);
            data.put("proxyGrpcEndpoint", mqProperties.getProxyGrpcEndpoint());
            data.put("body", objectMapper.readValue(json, Map.class));
            return DemoResult.ok(data);
        } catch (Exception e) {
            return DemoResult.error(e.getMessage());
        }
    }

    private String defaultTaskEnvelopeJson() throws Exception {
        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("message_id", UUID.randomUUID().toString());
        envelope.put("trace_id", UUID.randomUUID().toString());
        envelope.put("event_type", "interview.reflection.request");
        envelope.put("producer", "server_job");
        envelope.put("occurred_at", Instant.now().toString());
        envelope.put("idempotency_key", "demo:session:reflection:" + System.currentTimeMillis());
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("interview_session_id", "isess_demo_001");
        payload.put("student_id", "stu_demo");
        payload.put("note", "InterviewMqDemoController 内置测试任务");
        envelope.put("payload", payload);
        return objectMapper.writeValueAsString(envelope);
    }

    private String defaultResultEnvelopeJson() throws Exception {
        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("message_id", UUID.randomUUID().toString());
        envelope.put("trace_id", UUID.randomUUID().toString());
        envelope.put("event_type", "interview.reflection.result");
        envelope.put("producer", "ai_job_b");
        envelope.put("occurred_at", Instant.now().toString());
        envelope.put("idempotency_key", "demo:session:reflection:" + System.currentTimeMillis());
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("status", "demo_ok");
        payload.put("message", "InterviewMqDemoController 内置测试结果");
        envelope.put("payload", payload);
        return objectMapper.writeValueAsString(envelope);
    }
}
