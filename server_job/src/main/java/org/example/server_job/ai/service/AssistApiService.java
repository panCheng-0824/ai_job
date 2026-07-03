package org.example.server_job.ai.service;

import org.springframework.http.ResponseEntity;

public interface AssistApiService {
    ResponseEntity<byte[]> listUserModels();

    ResponseEntity<byte[]> search(String keyword, String scope, Integer limit);

    ResponseEntity<byte[]> onlineSearch(String query, String engine, Integer topk, Boolean deepSearch);

    ResponseEntity<byte[]> jobInfoQuery(String body);

    ResponseEntity<byte[]> clearJobInfoSemCache();
}
