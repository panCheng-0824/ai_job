package org.example.server_job.cfgTest.service;

import org.example.server_job.cfgTest.DemoResult;
import org.springframework.data.neo4j.core.Neo4jClient;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class Neo4jDemoService implements MiddlewareDemoService {

    private final Neo4jClient neo4jClient;

    public Neo4jDemoService(Neo4jClient neo4jClient) {
        this.neo4jClient = neo4jClient;
    }

    @Override
    public String middleware() {
        return "neo4j";
    }

    @Override
    public Map<String, Object> runDemo() {
        String nodeName = "neo4j-demo-" + UUID.randomUUID();
        Map<String, Object> row = neo4jClient.query("""
                        MERGE (n:MiddlewareDemo {name: $name})
                        SET n.updatedAt = $updatedAt
                        RETURN n.name AS name, n.updatedAt AS updatedAt
                        """)
                .bind(nodeName).to("name")
                .bind(Instant.now().toString()).to("updatedAt")
                .fetch()
                .one()
                .orElseGet(Map::of);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("node", row);
        return DemoResult.ok(data);
    }
}
