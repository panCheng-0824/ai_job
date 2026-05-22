package org.example.server_job.cfgTest.service;

import org.example.server_job.cfgTest.DemoResult;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class MySqlDemoService implements MiddlewareDemoService {

    private final JdbcTemplate jdbcTemplate;

    public MySqlDemoService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    public String middleware() {
        return "mysql";
    }

    @Override
    public Map<String, Object> runDemo() {
        jdbcTemplate.execute("""
                CREATE TABLE IF NOT EXISTS middleware_demo_mysql (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    message VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """);
        String message = "mysql-demo-" + UUID.randomUUID();
        jdbcTemplate.update("INSERT INTO middleware_demo_mysql(message) VALUES (?)", message);
        Integer count = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM middleware_demo_mysql", Integer.class);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("insertedMessage", message);
        data.put("totalRows", count);
        return DemoResult.ok(data);
    }
}
