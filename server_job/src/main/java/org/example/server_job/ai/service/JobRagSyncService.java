package org.example.server_job.ai.service;

import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Map;

public interface JobRagSyncService {
    Map<String, Object> syncJobToRag(String jobId);

    Map<String, Object> syncJobToRagList();

    /**
     * 岗位 RAG 统计：总数、已同步（synRag=1）、未同步。
     *
     * @param keyword 可选；非空时仅统计岗位名/企业名/地址/地区命中该关键词的岗位（与列表分页筛选一致）；空为全库。
     */
    Map<String, Object> ragSyncStats(String keyword);

    /**
     * 将未同步岗位提交线程池并行处理，通过 SSE 推送 stats / progress / done。
     *
     * @param keyword 可选；非空时仅处理命中关键词且仍待同步的岗位；空为全库未同步。
     */
    void streamSyncPendingJobs(SseEmitter emitter, String keyword);
}
