package org.example.server_job.cfgTest.service;

import org.example.server_job.cfgTest.DemoResult;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.InetSocketAddress;
import java.net.Socket;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class MilvusDemoService implements MiddlewareDemoService {

    @Value("${milvus.host}")
    private String milvusHost;

    @Value("${milvus.port}")
    private int milvusPort;

    @Override
    public String middleware() {
        return "milvus";
    }

    @Override
    public Map<String, Object> runDemo() {
        return socketConnectDemo("milvus", milvusHost, milvusPort);
    }

    private Map<String, Object> socketConnectDemo(String middleware, String host, int port) {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(host, port), 3000);
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("middleware", middleware);
            data.put("host", host);
            data.put("port", port);
            data.put("connected", socket.isConnected());
            return DemoResult.ok(data);
        } catch (Exception e) {
            throw new RuntimeException("connect failed: " + middleware + " " + host + ":" + port, e);
        }
    }
}
