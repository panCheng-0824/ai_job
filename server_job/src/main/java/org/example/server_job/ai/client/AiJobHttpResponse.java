package org.example.server_job.ai.client;

import java.util.List;
import java.util.Map;

public record AiJobHttpResponse(int statusCode, Map<String, List<String>> headers, byte[] body) {
}
