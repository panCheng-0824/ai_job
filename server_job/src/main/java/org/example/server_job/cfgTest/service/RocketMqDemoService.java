package org.example.server_job.cfgTest.service;

import org.example.server_job.cfgTest.DemoResult;
import org.example.server_job.interview.mq.InterviewMqProperties;
import org.springframework.stereotype.Service;

import java.net.InetSocketAddress;
import java.net.Socket;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * RocketMQ 联调：检测 Proxy gRPC 端口可达性（与业务发送/消费一致）。
 */
@Service
public class RocketMqDemoService implements MiddlewareDemoService {

    private final InterviewMqProperties interviewMqProperties;

    public RocketMqDemoService(InterviewMqProperties interviewMqProperties) {
        this.interviewMqProperties = interviewMqProperties;
    }

    @Override
    public String middleware() {
        return "rocketmq";
    }

    @Override
    public Map<String, Object> runDemo() {
        String endpoint = interviewMqProperties.getProxyGrpcEndpoint();
        if (endpoint == null || endpoint.isBlank()) {
            endpoint = interviewMqProperties.getProxyEndpoint();
        }
        String[] addr = endpoint.split(":");
        if (addr.length != 2) {
            throw new IllegalArgumentException("RocketMQ gRPC 地址格式应为 host:port，当前=" + endpoint);
        }
        Map<String, Object> data = socketConnectDemo("rocketmq-proxy-grpc", addr[0], Integer.parseInt(addr[1]));
        data.put("proxy_grpc_endpoint", endpoint);
        data.put("proxy_http_endpoint", interviewMqProperties.getProxyEndpoint());
        data.put("topic_ai_task", interviewMqProperties.getTopics().getAiTask());
        data.put("topic_ai_result", interviewMqProperties.getTopics().getAiResult());
        return DemoResult.ok(data);
    }

    private Map<String, Object> socketConnectDemo(String middleware, String host, int port) {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(host, port), 3000);
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("middleware", middleware);
            data.put("host", host);
            data.put("port", port);
            data.put("connected", socket.isConnected());
            return data;
        } catch (Exception e) {
            throw new RuntimeException("connect failed: " + middleware + " " + host + ":" + port, e);
        }
    }
}
