package org.example.server_job.cfgTest.service;

import org.bson.Document;
import org.example.server_job.cfgTest.DemoResult;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class MongoDbDemoService implements MiddlewareDemoService {

    private final MongoTemplate mongoTemplate;

    public MongoDbDemoService(MongoTemplate mongoTemplate) {
        this.mongoTemplate = mongoTemplate;
    }

    @Override
    public String middleware() {
        return "mongodb";
    }

    @Override
    public Map<String, Object> runDemo() {
        String collection = "middleware_demo_mongo";
        String docId = UUID.randomUUID().toString();
        Document doc = new Document("_id", docId)
                .append("message", "mongodb-demo")
                .append("createdAt", Instant.now().toString());
        mongoTemplate.getCollection(collection).insertOne(doc);
        long count = mongoTemplate.getCollection(collection).countDocuments();

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("collection", collection);
        data.put("insertedId", docId);
        data.put("totalDocs", count);
        return DemoResult.ok(data);
    }
}
