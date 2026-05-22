package org.example.server_job.ai.controller;

import org.example.server_job.ai.service.DataApiService;
import org.example.server_job.ai.service.JobRagSyncService;
import org.example.server_job.ai.rag.RagSyncBatchCoordinator;
import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * 门户/管理端使用的只读与轻量写接口聚合层。
 * <p>
 * 路径统一前缀 {@code /api}，由 {@code web_job} 等前端通过反向代理访问。
 * 学生画像、企业、岗位列表等委托 {@link DataApiService}；岗位与 RAG 知识库同步委托 {@link JobRagSyncService}；
 * 批量同步的「暂停 / 继续 / 取消」与流式连接生命周期配合，由 {@link RagSyncBatchCoordinator} 维护全局单批次状态。
 * </p>
 */
@RestController
@RequestMapping("/api")
public class DataController {

    /** 学生、企业、岗位分页等通用数据查询。 */
    private final DataApiService dataApiService;

    /** 单岗位同步、批量同步、RAG 统计及 SSE 流式同步实现。 */
    private final JobRagSyncService jobRagSyncService;

    /**
     * 当前是否允许新开一批流式同步、以及暂停/取消信号的分发器。
     * 与 {@link JobRagSyncServiceImpl#streamSyncPendingJobs} 内部注册的 SseEmitter 回调配合：
     * 客户端断开 SSE 时会触发取消，效果与调用 {@link #ragSyncCancel()} 一致。
     */
    private final RagSyncBatchCoordinator ragSyncBatchCoordinator;

    public DataController(
            DataApiService dataApiService,
            JobRagSyncService jobRagSyncService,
            RagSyncBatchCoordinator ragSyncBatchCoordinator
    ) {
        this.dataApiService = dataApiService;
        this.jobRagSyncService = jobRagSyncService;
        this.ragSyncBatchCoordinator = ragSyncBatchCoordinator;
    }

    /** 按学号（或业务主键）拉取学生画像树（中文键），供学生端展示。 */
    @GetMapping("/students/{studentId}")
    public Map<String, Object> getStudent(@PathVariable String studentId) {
        return dataApiService.getStudent(studentId);
    }

    /** 企业列表全量（体量可控时使用）。 */
    @GetMapping("/companies")
    public List<BizCompanyInfo> listCompanies() {
        return dataApiService.listCompanies();
    }

    /**
     * 企业分页：返回 total、hasMore、items（含关联岗位数 jobCount），供前端无限滚动。
     *
     * @param page     页码，从 1 开始
     * @param pageSize 每页条数，由服务层做上限裁剪
     * @param keyword  可选；非空时按关键词在库内模糊查询（与前端「回车搜索」对应）
     */
    @GetMapping("/companies/paged")
    public Map<String, Object> listCompaniesPaged(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer pageSize,
            @RequestParam(required = false) String keyword
    ) {
        return dataApiService.listCompaniesPaged(page, pageSize, keyword);
    }

    /** 按统一社会信用代码查询单家企业。 */
    @GetMapping("/companies/{creditCode}")
    public BizCompanyInfo getCompany(@PathVariable String creditCode) {
        return dataApiService.getCompany(creditCode);
    }

    /** 岗位全量列表（不分页；列表页主路径建议使用 {@link #listJobsPaged}）。 */
    @GetMapping("/jobs")
    public List<BizJobsInfo> listJobs() {
        return dataApiService.listJobs();
    }

    /**
     * 岗位分页：返回 total、hasMore、items 等，供前端无限滚动加载。
     *
     * @param page     页码，从 1 开始
     * @param pageSize 每页条数，由服务层做上限裁剪
     * @param keyword    可选；非空时按关键词在库内模糊查询（与前端「回车搜索」对应）
     * @param syncedOnly 默认 true：仅查已同步知识库（synRag=1）的岗位
     */
    @GetMapping("/jobs/paged")
    public Map<String, Object> listJobsPaged(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer pageSize,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "true") Boolean syncedOnly
    ) {
        return dataApiService.listJobsPaged(page, pageSize, keyword, syncedOnly);
    }

    /** 按岗位主键查询单条岗位实体（含正文等字段）。 */
    @GetMapping("/jobs/{jobId}")
    public BizJobsInfo getJob(@PathVariable String jobId) {
        return dataApiService.getJob(jobId);
    }

    /**
     * 将<strong>单个</strong>岗位同步到 ai_job 侧 LightRAG + GrepRAG，并回写本库 {@code synRag}、{@code ragMdPath}。
     * <p>同步完成后返回 JSON，供岗位详情页「同步知识库」按钮使用；与批量 SSE 接口相互独立。</p>
     */
    @PostMapping("/jobs/{jobId}/sync-rag")
    public Map<String, Object> syncJobToRag(@PathVariable String jobId) {
        return jobRagSyncService.syncJobToRag(jobId);
    }

    /**
     * 岗位 RAG 同步统计：总数、已同步（{@code synRag = "1"}）、未同步。
     * <p>可选 {@code keyword} 与岗位分页一致，仅统计命中关键词的岗位；空为全库。</p>
     */
    @GetMapping("/jobs/rag-sync/stats")
    public Map<String, Object> ragSyncStats(@RequestParam(required = false) String keyword) {
        return jobRagSyncService.ragSyncStats(keyword);
    }

    /**
     * 批量同步<strong>当前所有未同步</strong>岗位到 RAG，响应体为 <strong>SSE</strong>（{@code text/event-stream}）。
     * <p>
     * 设计要点：
     * <ul>
     *   <li>立即返回 {@link SseEmitter}，具体同步在 {@link CompletableFuture#runAsync} 异步线程中执行，避免阻塞 Tomcat 工作线程整段批量时间。</li>
     *   <li>事件名约定：{@code stats}（初始统计）、{@code progress}（每条完成）、{@code done}（汇总）、{@code error}（例如已有同步在进行）。</li>
     *   <li>浏览器关闭或取消请求导致连接完成时，由服务层注册的回调触发「取消」，未开始的岗位会被跳过。</li>
     * </ul>
     * </p>
     */
    @PostMapping(value = "/jobs/sync-rag/pending", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter syncJobsPendingRagStream(@RequestBody(required = false) Map<String, Object> body) {
        String keyword = "";
        if (body != null && body.get("keyword") != null) {
            keyword = String.valueOf(body.get("keyword"));
        }
        final String keywordFinal = keyword;
        // 0L：不设置超时时间，避免长批量被服务端主动掐断（仍受代理/网关超时影响）
        SseEmitter emitter = new SseEmitter(0L);
        CompletableFuture.runAsync(() -> {
            try {
                jobRagSyncService.streamSyncPendingJobs(emitter, keywordFinal);
            } catch (Exception ex) {
                try {
                    emitter.completeWithError(ex);
                } catch (Exception ignored) {
                    // 客户端已断开时 completeWithError 可能再抛异常，忽略即可
                }
            }
        });
        return emitter;
    }

    /**
     * 暂停<strong>当前这一批</strong>流式同步：尚未开始执行的岗位任务会在闸门前阻塞；
     * 已在执行中的单条同步（HTTP 进行中）会继续跑完。
     */
    @PostMapping("/jobs/sync-rag/pause")
    public Map<String, Object> ragSyncPause() {
        ragSyncBatchCoordinator.pauseCurrent();
        return Map.of("ok", true);
    }

    /** 恢复当前批次：唤醒在暂停闸门前等待的工作线程。 */
    @PostMapping("/jobs/sync-rag/resume")
    public Map<String, Object> ragSyncResume() {
        ragSyncBatchCoordinator.resumeCurrent();
        return Map.of("ok", true);
    }

    /**
     * 显式取消当前批次（与关闭 SSE 页面、前端 Abort 断开连接效果一致）：
     * 未开始的岗位记为跳过；进行中的单条仍可能完成。
     */
    @PostMapping("/jobs/sync-rag/cancel")
    public Map<String, Object> ragSyncCancel() {
        ragSyncBatchCoordinator.cancelCurrent();
        return Map.of("ok", true);
    }

    /**
     * 统一搜索入口：学生 / 企业 / 岗位等 scope，由 {@link DataApiService} 路由到具体存储。
     */
    @GetMapping("/data/search")
    public Map<String, Object> search(
            @RequestParam String keyword,
            @RequestParam(defaultValue = "all") String scope,
            @RequestParam(defaultValue = "20") Integer limit
    ) {
        return dataApiService.search(keyword, scope, limit);
    }
}
