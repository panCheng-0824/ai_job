package org.example.server_job.ai.service;

import org.springframework.http.ResponseEntity;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

/**
 * 智能网页采集（ai_search）网关：同步 JSON 与 NDJSON 流式中转。
 */
public interface AiSearchApiService {

    ResponseEntity<byte[]> crawl(String jsonBody);

    ResponseEntity<StreamingResponseBody> crawlStream(String jsonBody);
}
