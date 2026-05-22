package org.example.server_job.ai.service.impl;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.client.AiJobGatewayService;
import org.example.server_job.ai.service.AssistApiService;
import org.example.server_job.ai.service.support.BaseAiApiService;
import org.example.server_job.ai.support.AiResponseMapper;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class AssistApiServiceImpl extends BaseAiApiService implements AssistApiService {

    private static final Logger log = LogManager.getLogger(AssistApiServiceImpl.class);

    private final AiJobGatewayService gatewayService;
    private final AiResponseMapper responseMapper;

    public AssistApiServiceImpl(AiJobGatewayService gatewayService, AiResponseMapper responseMapper) {
        this.gatewayService = gatewayService;
        this.responseMapper = responseMapper;
    }

    @Override
    public ResponseEntity<byte[]> listUserModels() {
        log.info("调用 ai_job 获取用户模型列表开始");
        return guard(() -> responseMapper.toResponseEntity(gatewayService.get("/user-models", Map.of())));
    }

    @Override
    public ResponseEntity<byte[]> search(String keyword, String scope, Integer limit) {
        log.info("调用 ai_job 通用搜索开始, keyword={}, scope={}, limit={}", keyword, scope, limit);
        Map<String, String> queryParams = new LinkedHashMap<>();
        queryParams.put("keyword", keyword);
        queryParams.put("scope", scope);
        queryParams.put("limit", limit == null ? null : String.valueOf(limit));
        return guard(() -> responseMapper.toResponseEntity(gatewayService.get("/search", queryParams)));
    }

    @Override
    public ResponseEntity<byte[]> onlineSearch(String query, String engine, Integer topk, Boolean deepSearch) {
        log.info("调用 ai_job 联网搜索开始, query={}, engine={}, topk={}, deepSearch={}",
                query, engine, topk, deepSearch);
        Map<String, String> queryParams = new LinkedHashMap<>();
        queryParams.put("query", query);
        queryParams.put("engine", engine);
        queryParams.put("topk", topk == null ? null : String.valueOf(topk));
        queryParams.put("deep_search", deepSearch == null ? null : String.valueOf(deepSearch));
        return guard(() -> responseMapper.toResponseEntity(gatewayService.get("/online-search", queryParams)));
    }

    @Override
    public ResponseEntity<byte[]> jobInfoQuery(String body) {
        log.info("调用 ai_job 岗位信息查询开始, bodyLength={}", body == null ? 0 : body.length());
        return guard(() -> responseMapper.toResponseEntity(gatewayService.postJson("/skills/job-info-query", body)));
    }
}
