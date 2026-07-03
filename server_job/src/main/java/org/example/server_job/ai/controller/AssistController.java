package org.example.server_job.ai.controller;

import org.example.server_job.ai.service.AssistApiService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class AssistController {

    private final AssistApiService assistApiService;

    public AssistController(AssistApiService assistApiService) {
        this.assistApiService = assistApiService;
    }

    @GetMapping("/user-models")
    public ResponseEntity<byte[]> userModels() {
        return assistApiService.listUserModels();
    }

    @GetMapping("/search")
    public ResponseEntity<byte[]> search(
            @RequestParam String keyword,
            @RequestParam(defaultValue = "all") String scope,
            @RequestParam(defaultValue = "20") Integer limit
    ) {
        return assistApiService.search(keyword, scope, limit);
    }

    @GetMapping("/online-search")
    public ResponseEntity<byte[]> onlineSearch(
            @RequestParam String query,
            @RequestParam(defaultValue = "baidu") String engine,
            @RequestParam(defaultValue = "5") Integer topk,
            @RequestParam(name = "deep_search", defaultValue = "false") Boolean deepSearch
    ) {
        return assistApiService.onlineSearch(query, engine, topk, deepSearch);
    }

    @PostMapping("/skills/job-info-query")
    public ResponseEntity<byte[]> jobInfoQuery(@RequestBody String body) {
        return assistApiService.jobInfoQuery(body);
    }

    @PostMapping("/skills/job-info-sem-cache/clear")
    public ResponseEntity<byte[]> clearJobInfoSemCache() {
        return assistApiService.clearJobInfoSemCache();
    }
}
