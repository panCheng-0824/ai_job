package org.example.server_job.cfgTest.service;

import org.example.server_job.cfgTest.DemoResult;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class ElasticsearchDemoService implements MiddlewareDemoService {

    @Value("${spring.data.elasticsearch.uris}")
    private String elasticsearchUris;

    @Value("${spring.data.elasticsearch.username:}")
    private String elasticsearchUsername;

    @Value("${spring.data.elasticsearch.password:}")
    private String elasticsearchPassword;

    @Override
    public String middleware() {
        return "elasticsearch";
    }

    @Override
    public Map<String, Object> runDemo() {
        RestClient client = RestClient.builder()
                .baseUrl(elasticsearchUris)
                .defaultHeaders(headers -> headers.setBasicAuth(elasticsearchUsername, elasticsearchPassword))
                .build();

        String indexName = "middleware-demo-es";
        try {
            client.put().uri("/" + indexName).retrieve().toBodilessEntity();
        } catch (Exception ignored) {
            // Index may already exist.
        }

        String id = UUID.randomUUID().toString();
        Map<String, Object> body = Map.of(
                "id", id,
                "message", "elasticsearch-demo",
                "createdAt", Instant.now().toString()
        );
        client.post().uri("/" + indexName + "/_doc/" + id).body(body).retrieve().toBodilessEntity();

        Map<String, Object> countResp = client.get().uri("/" + indexName + "/_count").retrieve().body(Map.class);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("index", indexName);
        data.put("insertedId", id);
        data.put("countResponse", countResp);
        return DemoResult.ok(data);
    }
}
