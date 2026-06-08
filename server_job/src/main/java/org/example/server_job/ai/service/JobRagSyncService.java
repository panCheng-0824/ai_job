package org.example.server_job.ai.service;

import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Map;

public interface JobRagSyncService {
    Map<String, Object> syncJobToRag(String jobId);

    /**
     * 下架单个岗位的知识库数据：删除 ai_job 侧 LightRAG + GrepRAG，回写 synRag=0。
     */
    Map<String, Object> unsyncJobFromRag(String jobId);

    Map<String, Object> syncJobToRagList();

    /**
     * 岗位 RAG 统计：总数、已同步（synRag=1）、未同步。
     *
     * @param keyword     可选；非空时仅统计岗位名/企业名/地址/地区命中该关键词的岗位
     * @param companyType 可选；字典 job_dwxz 的 DM
     * @param industry    可选；字典 job_hylb 的 DM
     */
    Map<String, Object> ragSyncStats(String keyword, String companyType, String industry);

    /**
     * 将未同步岗位提交线程池并行处理，通过 SSE 推送 stats / progress / done。
     *
     * @param keyword          可选；非空时仅处理命中关键词且仍待同步的岗位
     * @param companyType      可选；单位性质筛选
     * @param industry         可选；行业筛选
     * @param accelerate       为 true 时按线程池配置并行同步；为 false 时串行（一次仅 1 条）
     * @param purgeBeforeSync  为 true 时在占槽并开始同步前，调用 ai_job 清理 LightRAG 积压
     */
    void streamSyncPendingJobs(
            SseEmitter emitter,
            String keyword,
            String companyType,
            String industry,
            boolean accelerate,
            boolean purgeBeforeSync
    );

    /**
     * 预览岗位写入 RAG 的正文（与 {@link #syncJobToRag} 组装逻辑一致，不调用 ai_job）。
     */
    Map<String, Object> previewJobRag(String jobId);

    /**
     * 单独清理 ai_job LightRAG 积压（pending / processing / failed），不触发岗位同步。
     */
    Map<String, Object> purgeLightRagBacklog();

    /**
     * LightRAG 积压文档数量（pending / processing / failed / processed）。
     */
    Map<String, Object> lightRagBacklogStats();
}
