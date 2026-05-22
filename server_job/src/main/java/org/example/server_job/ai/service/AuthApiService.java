package org.example.server_job.ai.service;

import java.util.Map;

public interface AuthApiService {
    Map<String, Object> login(String body);
}
