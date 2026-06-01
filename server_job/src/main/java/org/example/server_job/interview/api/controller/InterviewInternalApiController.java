package org.example.server_job.interview.api.controller;

import org.example.server_job.interview.service.InterviewContextBundleService;
import org.example.server_job.interview.support.IndustryCategoryRedisCache;
import org.example.server_job.interview.support.InterviewContextRedisSupport;
import org.example.server_job.interview.support.InterviewServiceTokenVerifier;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 内部 API — 供 ai_job 拉取 context-bundle（无 PII 大 payload 时回调）。
 */
@RestController
@RequestMapping("/internal/interview")
public class InterviewInternalApiController {

    private final InterviewContextBundleService contextBundleService;
    private final IndustryCategoryRedisCache industryRedisCache;
    private final InterviewContextRedisSupport contextRedis;
    private final InterviewServiceTokenVerifier tokenVerifier;

    public InterviewInternalApiController(
            InterviewContextBundleService contextBundleService,
            IndustryCategoryRedisCache industryRedisCache,
            InterviewContextRedisSupport contextRedis,
            InterviewServiceTokenVerifier tokenVerifier
    ) {
        this.contextBundleService = contextBundleService;
        this.industryRedisCache = industryRedisCache;
        this.contextRedis = contextRedis;
        this.tokenVerifier = tokenVerifier;
    }

    @GetMapping("/sessions/{id}/context-bundle")
    public ResponseEntity<Map<String, Object>> contextBundle(
            @PathVariable("id") String interviewSessionId,
            @RequestHeader(value = "X-Service-Token", required = false) String serviceToken
    ) {
        tokenVerifier.verify(serviceToken);
        return ResponseEntity.ok(contextBundleService.build(interviewSessionId));
    }

    /**
     * 读取整场面试 Redis ctx（ai_job 遮层模式入口）。
     */
    @GetMapping("/ctx/{studentId}/{recordId}")
    public ResponseEntity<Map<String, Object>> loadInterviewCtx(
            @PathVariable("studentId") String studentId,
            @PathVariable("recordId") String recordId,
            @RequestHeader(value = "X-Service-Token", required = false) String serviceToken
    ) {
        tokenVerifier.verify(serviceToken);
        return contextRedis.read(studentId, recordId)
                .map(ctx -> {
                    Map<String, Object> out = new LinkedHashMap<>(ctx);
                    out.put("ctx_key", org.example.server_job.interview.support.InterviewRedisKeys.ctx(studentId, recordId));
                    return ResponseEntity.ok(out);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /** 标记面试已进入遮层答题（可选，web 进入时调用） */
    @PostMapping("/ctx/{studentId}/{recordId}/enter")
    public ResponseEntity<Map<String, Object>> enterInterviewCtx(
            @PathVariable("studentId") String studentId,
            @PathVariable("recordId") String recordId,
            @RequestHeader(value = "X-Service-Token", required = false) String serviceToken
    ) {
        tokenVerifier.verify(serviceToken);
        contextRedis.markInProgress(studentId, recordId);
        return contextRedis.read(studentId, recordId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * 一级行业 Redis 桶（key=top_category），供 ai_job 大纲分类第一阶段。
     */
    @GetMapping("/industry/cache/top")
    public ResponseEntity<Map<String, Object>> industryTopCache(
            @RequestHeader(value = "X-Service-Token", required = false) String serviceToken
    ) {
        tokenVerifier.verify(serviceToken);
        return ResponseEntity.ok(loadTopBucket());
    }

    /**
     * 某一级下的二级行业 Redis 桶（key=一级 category_id）。
     */
    @GetMapping("/industry/cache/l2/{parentId}")
    public ResponseEntity<Map<String, Object>> industryL2Cache(
            @PathVariable("parentId") String parentId,
            @RequestHeader(value = "X-Service-Token", required = false) String serviceToken
    ) {
        tokenVerifier.verify(serviceToken);
        return ResponseEntity.ok(loadLevel2Bucket(parentId));
    }

    /** 手动触发 Redis 重建（运维/联调） */
    @PostMapping("/industry/cache/rebuild")
    public ResponseEntity<Map<String, Object>> rebuildIndustryCache(
            @RequestHeader(value = "X-Service-Token", required = false) String serviceToken
    ) {
        tokenVerifier.verify(serviceToken);
        industryRedisCache.rebuildAll();
        return ResponseEntity.ok(Map.of("rebuilt", true));
    }

    private Map<String, Object> loadTopBucket() {
        return industryRedisCache.readTopBucket().orElseGet(() -> {
            industryRedisCache.rebuildAll();
            return industryRedisCache.readTopBucket().orElse(emptyBucket("top_category", 1));
        });
    }

    private Map<String, Object> loadLevel2Bucket(String parentId) {
        return industryRedisCache.readLevel2Bucket(parentId).orElseGet(() -> {
            industryRedisCache.rebuildAll();
            return industryRedisCache.readLevel2Bucket(parentId).orElse(emptyBucket("level2", 2, parentId));
        });
    }

    private static Map<String, Object> emptyBucket(String bucket, int level) {
        return emptyBucket(bucket, level, null);
    }

    private static Map<String, Object> emptyBucket(String bucket, int level, String parentId) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("bucket", bucket);
        out.put("level", level);
        if (parentId != null) {
            out.put("parent_id", parentId);
        }
        out.put("items", List.of());
        out.put("count", 0);
        return out;
    }
}
