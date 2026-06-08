package org.example.server_job.ai.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.example.server_job.ai.client.AiJobGatewayService;
import org.example.server_job.ai.client.AiJobHttpResponse;
import org.example.server_job.ai.rag.RagSyncBatchCoordinator;
import org.example.server_job.ai.rag.RagSyncRunState;
import org.example.server_job.ai.service.JobRagSyncService;
import org.example.server_job.biz.entity.BizCompanyInfo;
import org.example.server_job.biz.entity.BizJobsInfo;
import org.example.server_job.biz.entity.BizJobsRagSync;
import org.example.server_job.biz.service.BizCompanyInfoService;
import org.example.server_job.biz.service.BizJobsInfoService;
import org.example.server_job.biz.service.BizJobsRagSyncService;
import org.example.server_job.biz.support.BizDetailPreviewBuilder;
import org.example.server_job.biz.support.BizJobListScopeSupport;
import org.example.server_job.biz.support.JobRagTextBuilder;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executor;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 岗位与 ai_job（LightRAG + GrepRAG）同步的核心实现。
 * <p>
 * 职责划分：
 * <ul>
 *   <li><strong>单条同步</strong>{@link #syncJobToRag(String)}：供 REST 按 jobId 调用，同步完成后返回 JSON。</li>
 *   <li><strong>批量同步（非流式）</strong>{@link #syncJobToRagList()}：线程池并发拉全量待同步列表，全部结束后一次性返回汇总（脚本或其它调用方可复用）。</li>
 *   <li><strong>批量同步（SSE）</strong>{@link #streamSyncPendingJobs(SseEmitter, String)}：与 {@link RagSyncBatchCoordinator} 配合，支持暂停/取消/关连接取消，并向前端推送 stats / progress / done。</li>
 *   <li><strong>统计</strong>{@link #ragSyncStats(String)}：读库计数，支持按关键词限定范围（与 {@link DataApiService#listJobsPaged} 一致）。</li>
 * </ul>
 * 单条写入路径上，LightRAG 与 GrepRAG 的两个 HTTP 在 {@link ForkJoinPool#commonPool()} 上并行（避免与批量任务共用 {@link #ragSyncExecutor} 造成线程池死锁）；
 * 批量/流式层仅在「每条岗位」级别使用 {@link #ragSyncExecutor}。
 * </p>
 */
@Service
public class JobRagSyncServiceImpl implements JobRagSyncService {

    private static final Logger log = LogManager.getLogger(JobRagSyncServiceImpl.class);

    /** 本库岗位表：读取待同步列表、单条查询。 */
    private final BizJobsInfoService bizJobsInfoService;

    /** 企业主数据：RAG 正文拼装时补充公司信息。 */
    private final BizCompanyInfoService bizCompanyInfoService;

    /** RAG 同步状态独立表：回写 syn_rag / rag_md_path。 */
    private final BizJobsRagSyncService bizJobsRagSyncService;

    /** 岗位 + 企业 + 字典 → Markdown 正文。 */
    private final JobRagTextBuilder jobRagTextBuilder;

    /** 详情页 JSON 预览（字典翻译后结构化展示）。 */
    private final BizDetailPreviewBuilder detailPreviewBuilder;

    /** 岗位列表 / RAG 同步共用查询范围。 */
    private final BizJobListScopeSupport bizJobListScopeSupport;

    /** 访问 ai_job 网关的 OkHttp 封装，用于 POST JSON 到 LightRAG、GrepRAG 等路径。 */
    private final AiJobGatewayService aiJobGatewayService;

    /** 将请求体、响应体与 Map 互转。 */
    private final ObjectMapper objectMapper;

    /**
     * 专用于 RAG 批量场景的线程池（配置见 {@code RagSyncExecutorConfig}）：
     * 仅用于「每条岗位」级别的 {@link CompletableFuture#supplyAsync}（含流式与非流式批量），
     * <strong>不要</strong>在池任务内部再向本池提交子任务并阻塞等待，否则易死锁；单岗位内双 HTTP 并行见 {@link #syncRagForJob} 使用 {@link ForkJoinPool#commonPool()}。
     */
    private final Executor ragSyncExecutor;

    /**
     * 保证全服务同一时刻只有一批流式批量同步在跑；并承载暂停 / 取消语义。
     * 与 {@link org.example.server_job.ai.controller.DataController} 中的 pause/resume/cancel 接口及 SseEmitter 生命周期回调相连。
     */
    private final RagSyncBatchCoordinator ragSyncBatchCoordinator;

    /** ai_job 侧 LightRAG 写入接口路径，默认 {@code /rag/lightrag/insert}，可由配置覆盖。 */
    @Value("${ai-job.rag.insert-path:/rag/lightrag/insert}")
    private String ragInsertPath;

    /** ai_job 侧 LightRAG 清理 pending/processing/failed 积压路径。 */
    @Value("${ai-job.rag.purge-non-processed-path:/rag/lightrag/purge-non-processed}")
    private String lightRagPurgeNonProcessedPath;

    /** ai_job 侧 LightRAG 积压统计路径。 */
    @Value("${ai-job.rag.backlog-stats-path:/rag/lightrag/backlog-stats}")
    private String lightRagBacklogStatsPath;

    /** ai_job 侧 GrepRAG 文本落 Markdown 路径，默认 {@code /rag/greprag/text-to-md}。 */
    @Value("${ai-job.rag.greprag-text-to-md-path:/rag/greprag/text-to-md}")
    private String grepRagTextToMdPath;

    /** ai_job 侧 LightRAG 按 doc_id 删除路径，默认 {@code /rag/lightrag/docs/{docId}}。 */
    @Value("${ai-job.rag.delete-doc-path:/rag/lightrag/docs}")
    private String lightRagDeleteDocPath;

    /** ai_job 侧 GrepRAG 删除 Markdown 路径，默认 {@code /rag/greprag/md-file}。 */
    @Value("${ai-job.rag.greprag-delete-md-path:/rag/greprag/md-file}")
    private String grepRagDeleteMdPath;

    /** 写入请求体中的 source 字段，标识数据来自本服务。 */
    @Value("${ai-job.rag.source:server_job}")
    private String ragSource;

    /** 批量同步开启「加速」时的最大并行条数（与 {@link RagSyncExecutorConfig} 线程池大小一致）。 */
    @Value("${ai-job.rag.sync-thread-pool-core-size:3}")
    private int ragSyncParallelism;

    public JobRagSyncServiceImpl(
            BizJobsInfoService bizJobsInfoService,
            BizCompanyInfoService bizCompanyInfoService,
            BizJobsRagSyncService bizJobsRagSyncService,
            JobRagTextBuilder jobRagTextBuilder,
            BizDetailPreviewBuilder detailPreviewBuilder,
            BizJobListScopeSupport bizJobListScopeSupport,
            AiJobGatewayService aiJobGatewayService,
            ObjectMapper objectMapper,
            @Qualifier("ragSyncExecutor") Executor ragSyncExecutor,
            RagSyncBatchCoordinator ragSyncBatchCoordinator
    ) {
        this.bizJobsInfoService = bizJobsInfoService;
        this.bizCompanyInfoService = bizCompanyInfoService;
        this.bizJobsRagSyncService = bizJobsRagSyncService;
        this.jobRagTextBuilder = jobRagTextBuilder;
        this.detailPreviewBuilder = detailPreviewBuilder;
        this.bizJobListScopeSupport = bizJobListScopeSupport;
        this.aiJobGatewayService = aiJobGatewayService;
        this.objectMapper = objectMapper;
        this.ragSyncExecutor = ragSyncExecutor;
        this.ragSyncBatchCoordinator = ragSyncBatchCoordinator;
    }

    /**
     * 按路径参数同步<strong>一个</strong>岗位：校验 jobId → 查库 → 组正文与请求体 → 并行调 LightRAG + GrepRAG → 校验 HTTP 状态 → 更新 synRag。
     *
     * @param jobId 岗位主键（会先经 {@link #normalizeJobId(String)} 去空白）
     * @return 含 graphRag/grepRag 上游 JSON 摘要及 ragMdPath 等，供前端展示结果
     * @throws ResponseStatusException 404 岗位不存在；502 上游失败或调用异常
     */
    @Override
    public Map<String, Object> syncJobToRag(String jobId) {
        String normalizedJobId = normalizeJobId(jobId);
        BizJobsInfo job = bizJobsInfoService.getById(normalizedJobId);
        if (job == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "岗位不存在");
        }
        return syncRagForJob(job);
    }

    @Override
    public Map<String, Object> unsyncJobFromRag(String jobId) {
        String normalizedJobId = normalizeJobId(jobId);
        BizJobsInfo job = bizJobsInfoService.getById(normalizedJobId);
        if (job == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "岗位不存在");
        }
        if (!bizJobsRagSyncService.isSynced(normalizedJobId)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "该岗位尚未同步到知识库");
        }
        BizJobsRagSync rag = bizJobsRagSyncService.findByJobId(normalizedJobId);
        String ragMdPath = rag != null ? rag.getRagMdPath() : null;
        String lightDocId = toLightRagDocId(normalizedJobId);

        log.info("岗位知识库下架开始, jobId={}, lightDocId={}, ragMdPath={}", normalizedJobId, lightDocId, ragMdPath);

        CompletableFuture<AiJobHttpResponse> lightFuture = CompletableFuture.supplyAsync(
                () -> deleteLightRagDoc(lightDocId, normalizedJobId),
                ForkJoinPool.commonPool()
        );
        CompletableFuture<AiJobHttpResponse> grepFuture = CompletableFuture.supplyAsync(
                () -> deleteGrepRagMarkdown(ragMdPath, normalizedJobId),
                ForkJoinPool.commonPool()
        );

        try {
            CompletableFuture.allOf(lightFuture, grepFuture).join();
        } catch (CompletionException ex) {
            unwrapRagSyncCompletionException(ex);
        }

        AiJobHttpResponse lightResp = lightFuture.join();
        AiJobHttpResponse grepResp = grepFuture.join();
        Map<String, Object> lightBody = parseUpstreamBody(lightResp);
        Map<String, Object> grepBody = parseUpstreamBody(grepResp);

        boolean lightOk = lightResp.statusCode() >= 200 && lightResp.statusCode() < 300;
        boolean grepOk = grepResp.statusCode() >= 200 && grepResp.statusCode() < 300
                || grepResp.statusCode() == 404;
        if (!lightOk) {
            String detail = Objects.toString(lightBody.getOrDefault("detail", "LightRAG 删除失败"), "LightRAG 删除失败");
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, detail);
        }
        if (!grepOk) {
            String detail = Objects.toString(grepBody.getOrDefault("detail", "GrepRAG 删除 Markdown 失败"), "GrepRAG 删除 Markdown 失败");
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, detail);
        }

        bizJobsRagSyncService.markUnsynced(normalizedJobId);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("success", true);
        result.put("message", "知识库下架成功");
        result.put("jobId", normalizedJobId);
        result.put("synRag", "0");
        result.put("graphRag", lightBody);
        result.put("grepRag", grepBody);
        log.info("岗位知识库下架完成, jobId={}", normalizedJobId);
        return result;
    }

    @Override
    public Map<String, Object> previewJobRag(String jobId) {
        String normalizedJobId = normalizeJobId(jobId);
        BizJobsInfo job = bizJobsInfoService.getById(normalizedJobId);
        if (job == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "岗位不存在");
        }
        BizCompanyInfo company = loadCompanyForJob(job);
        BizJobsRagSync rag = bizJobsRagSyncService.findByJobId(job.getJobid());
        String text = jobRagTextBuilder.build(job, company);
        String filename = jobRagTextBuilder.buildMarkdownFilename(job, company);
        Map<String, Object> display = detailPreviewBuilder.buildJobPreview(
                job, company, rag, text, filename, ragSource);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("展示数据", display);
        result.put("jobId", job.getJobid());
        result.put("source", ragSource);
        result.put("filename", filename);
        result.put("job_ids", List.of(job.getJobid()));
        result.put("markdown", text);
        result.put("textLength", text.length());
        return result;
    }

    /**
     * 非流式批量同步：筛选 {@code synRag != "1"} 的岗位，逐条提交到 {@link #ragSyncExecutor}，全部结束后汇总。
     * <p>
     * 与 {@link #streamSyncPendingJobs} 相比：无 SSE、无暂停/取消协调；适合脚本或内部任务。单条失败不会中断其它 CompletableFuture。
     * </p>
     */
    @Override
    public Map<String, Object> syncJobToRagList() {
        List<BizJobsInfo> pending = bizJobsInfoService.list().stream()
                .filter(Objects::nonNull)
                .filter(j -> j.getJobid() != null && !j.getJobid().isBlank())
                .filter(this::needsRagSync)
                .toList();

        if (pending.isEmpty()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("success", true);
            empty.put("message", "没有待同步的岗位");
            empty.put("pendingCount", 0);
            empty.put("succeeded", 0);
            empty.put("failed", 0);
            empty.put("items", List.of());
            return empty;
        }

        List<CompletableFuture<Map<String, Object>>> futures = pending.stream()
                .map(job -> CompletableFuture.supplyAsync(() -> syncOneJobInBatch(job), ragSyncExecutor))
                .toList();

        @SuppressWarnings("unchecked")
        CompletableFuture<Void> all = CompletableFuture.allOf(futures.toArray(CompletableFuture[]::new));
        all.join();

        List<Map<String, Object>> items = new ArrayList<>(futures.size());
        int succeeded = 0;
        int failed = 0;
        for (CompletableFuture<Map<String, Object>> f : futures) {
            Map<String, Object> row = f.join();
            items.add(row);
            if (Boolean.TRUE.equals(row.get("success"))) {
                succeeded++;
            } else {
                failed++;
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("success", failed == 0);
        result.put("message", failed == 0 ? "批量同步完成" : "批量同步结束，部分岗位失败");
        result.put("pendingCount", pending.size());
        result.put("succeeded", succeeded);
        result.put("failed", failed);
        result.put("items", items);
        return result;
    }

    /**
     * 统计岗位总数、已写入 RAG（{@code synRag = "1"}）、未同步数；可选按关键词限定在岗位名/企业名/地址/地区上的命中范围。
     */
    @Override
    public Map<String, Object> ragSyncStats(String keyword, String companyType, String industry) {
        String q = BizJobListScopeSupport.normalizeKeyword(keyword);
        String companyTypeCode = BizJobListScopeSupport.normalizeKeyword(companyType);
        String industryCode = BizJobListScopeSupport.normalizeKeyword(industry);
        LambdaQueryWrapper<BizJobsInfo> base = new LambdaQueryWrapper<>();
        bizJobListScopeSupport.applyListScope(base, q, companyTypeCode, industryCode);
        long total = bizJobsInfoService.count(base);

        long synced = countSyncedInScope(q, companyTypeCode, industryCode);

        long unsynced = Math.max(0L, total - synced);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("total", total);
        m.put("synced", synced);
        m.put("unsynced", unsynced);
        m.put("keyword", q);
        m.put("companyType", companyTypeCode);
        m.put("industry", industryCode);
        return m;
    }

    /**
     * 流式批量同步：通过 SSE 推送进度，并与 {@link RagSyncBatchCoordinator} / {@link RagSyncRunState} 协作实现暂停与取消。
     * <p>
     * 执行顺序概要：
     * <ol>
     *   <li>统计全库 total、已同步 initialSynced，并筛出本批 pending；先发 {@code stats} 事件（含 batchTotal）。</li>
     *   <li>若 pending 为空：发 {@code done} 后直接 complete，不占用「单批次」槽位。</li>
     *   <li>若非空：{@link RagSyncBatchCoordinator#tryBeginRun()} 占槽；失败则发 {@code error} 并结束。</li>
     *   <li>注册 SseEmitter 完成/超时/错误回调：一律 {@link RagSyncRunState#cancel()}，使「关页面」等价于取消。</li>
     *   <li>为每条岗位提交异步任务：先 {@link RagSyncRunState#awaitGate()}（支持暂停），若已取消则 {@link #skippedRow}，否则 {@link #syncOneJobInBatch}。</li>
     *   <li>每条任务结束时在 {@code whenComplete} 里累加成功数、推送 {@code progress}，并对 emitter 加锁发送以避免并发写乱序。</li>
     *   <li>{@link CountDownLatch} 等待本批全部结束（含跳过），汇总 skipped/cancelled，发 {@code done}，{@code emitter.complete()}。</li>
     *   <li>{@code finally} 中 {@link RagSyncBatchCoordinator#endRun} 释放槽位，允许下一次批量同步。</li>
     * </ol>
     * </p>
     *
     * @param emitter 由 Controller 创建并已设置无超时；本方法不负责在成功路径外重复 complete（异常路径会 completeWithError）
     */
    @Override
    public void streamSyncPendingJobs(
            SseEmitter emitter,
            String keyword,
            String companyType,
            String industry,
            boolean accelerate,
            boolean purgeBeforeSync
    ) {
        // 仅在本方法成功「占槽」后非空，用于 finally 中成对 endRun，以及中断时 cancel
        RagSyncRunState runState = null;
        try {
            String q = BizJobListScopeSupport.normalizeKeyword(keyword);
            String companyTypeCode = BizJobListScopeSupport.normalizeKeyword(companyType);
            String industryCode = BizJobListScopeSupport.normalizeKeyword(industry);
            LambdaQueryWrapper<BizJobsInfo> scope = new LambdaQueryWrapper<>();
            bizJobListScopeSupport.applyListScope(scope, q, companyTypeCode, industryCode);
            long total = bizJobsInfoService.count(scope);

            long initialSynced = countSyncedInScope(q, companyTypeCode, industryCode);

            List<BizJobsInfo> candidates = bizJobsInfoService.list(scope);
            List<BizJobsInfo> pending = candidates.stream()
                    .filter(Objects::nonNull)
                    .filter(j -> j.getJobid() != null && !j.getJobid().isBlank())
                    .filter(this::needsRagSync)
                    .toList();

            if (purgeBeforeSync && !pending.isEmpty()) {
                Map<String, Object> purgeResult = doPurgeLightRagBacklog();
                emitSse(emitter, "purge", purgeResult);
                if (Boolean.FALSE.equals(purgeResult.get("success"))) {
                    emitSse(emitter, "error", Map.of(
                            "detail",
                            Objects.toString(purgeResult.get("message"), "LightRAG 积压清理失败")
                    ));
                    emitter.complete();
                    return;
                }
            }

            Map<String, Object> startStats = new LinkedHashMap<>();
            startStats.put("total", total);
            startStats.put("synced", initialSynced);
            startStats.put("unsynced", Math.max(0L, total - initialSynced));
            int maxParallel = resolveBatchMaxParallel(accelerate);
            startStats.put("batchTotal", pending.size());
            startStats.put("keyword", q);
            startStats.put("companyType", companyTypeCode);
            startStats.put("industry", industryCode);
            startStats.put("accelerate", accelerate);
            startStats.put("maxParallel", maxParallel);
            emitSse(emitter, "stats", startStats);

            if (pending.isEmpty()) {
                Map<String, Object> done = new LinkedHashMap<>();
                done.put("success", true);
                done.put("message", "没有待同步的岗位");
                done.put("pendingCount", 0);
                done.put("succeeded", 0);
                done.put("failed", 0);
                done.put("skipped", 0);
                done.put("cancelled", false);
                done.put("items", List.of());
                emitSse(emitter, "done", done);
                emitter.complete();
                return;
            }

            Optional<RagSyncRunState> opt = ragSyncBatchCoordinator.tryBeginRun();
            if (opt.isEmpty()) {
                emitSse(emitter, "error", Map.of("detail", "已有批量同步在进行，请稍后再试"));
                emitter.complete();
                return;
            }
            runState = opt.get();
            // Lambda 内只能引用 effectively final 变量，故单独声明 final 引用供异步任务与回调共用
            final RagSyncRunState runRef = runState;
            Runnable releaseHook = () -> {
                runRef.cancel();
                ragSyncBatchCoordinator.endRun(runRef);
            };
            emitter.onCompletion(releaseHook);
            emitter.onTimeout(releaseHook);
            emitter.onError(e -> releaseHook.run());

            // 多线程写入 items，使用同步列表；进度中的 synced 用「本批已成功数 + initialSynced」近似展示
            List<Map<String, Object>> items = Collections.synchronizedList(new ArrayList<>(pending.size()));
            AtomicInteger batchSuccess = new AtomicInteger();
            AtomicInteger batchDone = new AtomicInteger();
            int batchSize = pending.size();
            CountDownLatch latch = new CountDownLatch(batchSize);
            Semaphore parallelGate = new Semaphore(maxParallel);

            for (BizJobsInfo job : pending) {
                CompletableFuture.supplyAsync(() -> {
                            try {
                                runRef.awaitGate();
                                if (runRef.isCancelled()) {
                                    return skippedRow(job, "已取消（未执行同步）");
                                }
                                parallelGate.acquire();
                                try {
                                    emitJobSyncing(emitter, job, batchSize);
                                    return syncOneJobInBatch(job);
                                } finally {
                                    parallelGate.release();
                                }
                            } catch (InterruptedException e) {
                                Thread.currentThread().interrupt();
                                return skippedRow(job, "已中断");
                            }
                        }, ragSyncExecutor)
                        .whenComplete((row, ex) -> {
                            try {
                                Map<String, Object> r = row;
                                if (ex != null) {
                                    r = new LinkedHashMap<>();
                                    r.put("jobId", job.getJobid());
                                    r.put("success", false);
                                    r.put("message", ex.getMessage() != null ? ex.getMessage() : String.valueOf(ex));
                                    log.error("批量同步 RAG 任务异常, jobId={}", job.getJobid(), ex);
                                }
                                items.add(r);
                                if (Boolean.TRUE.equals(r.get("success"))) {
                                    batchSuccess.incrementAndGet();
                                }
                                int done = batchDone.incrementAndGet();
                                long syncedNow = initialSynced + (long) batchSuccess.get();
                                Map<String, Object> progress = new LinkedHashMap<>();
                                progress.put("total", total);
                                progress.put("synced", syncedNow);
                                progress.put("unsynced", Math.max(0L, total - syncedNow));
                                progress.put("batchIndex", done);
                                progress.put("batchTotal", batchSize);
                                progress.put("item", r);
                                emitSse(emitter, "progress", progress);
                            } catch (Exception sendEx) {
                                log.warn("SSE progress 发送失败, jobId={}", job.getJobid(), sendEx);
                            } finally {
                                latch.countDown();
                            }
                        });
            }

            latch.await();

            int succeeded = batchSuccess.get();
            List<Map<String, Object>> snapshot;
            synchronized (items) {
                snapshot = new ArrayList<>(items);
            }
            int skipped = (int) snapshot.stream().filter(m -> Boolean.TRUE.equals(m.get("skipped"))).count();
            // 失败条数 = 本批总数 - 真正成功 - 跳过（跳过不计入业务失败，但 success 字段为 false）
            int failed = batchSize - succeeded - skipped;
            boolean cancelled = runRef.isCancelled();
            Map<String, Object> done = new LinkedHashMap<>();
            done.put("cancelled", cancelled);
            done.put("skipped", skipped);
            done.put("pendingCount", batchSize);
            done.put("succeeded", succeeded);
            done.put("failed", failed);
            done.put("items", snapshot);
            done.put("success", !cancelled && failed == 0);
            if (cancelled) {
                done.put("message", skipped > 0 ? "已取消：未开始的岗位已跳过（进行中的已尽力完成）" : "已取消");
            } else {
                done.put("message", failed == 0 ? "批量同步完成" : "批量同步结束，部分岗位失败");
            }
            emitSse(emitter, "done", done);
            emitter.complete();
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            if (runState != null) {
                runState.cancel();
            }
            try {
                Map<String, Object> done = new LinkedHashMap<>();
                done.put("success", false);
                done.put("message", "同步被中断");
                done.put("cancelled", true);
                emitSse(emitter, "done", done);
            } catch (Exception ignored) {
                // 连接可能已不可用
            }
            try {
                emitter.completeWithError(ie);
            } catch (Exception ignored) {
                // 同上
            }
        } catch (Exception e) {
            log.error("流式同步 RAG 失败", e);
            try {
                emitter.completeWithError(e);
            } catch (Exception ignored) {
                // 同上
            }
        } finally {
            if (runState != null) {
                ragSyncBatchCoordinator.endRun(runState);
            }
        }
    }

    /**
     * 构造一条「因取消/暂停闸门后仍取消而未实际调用 ai_job」的占位结果，便于前端日志与 skipped 统计。
     */
    private static Map<String, Object> skippedRow(BizJobsInfo job, String reason) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("jobId", job.getJobid());
        r.put("jobName", job.getZwmc());
        r.put("success", false);
        r.put("skipped", true);
        r.put("message", reason);
        return r;
    }

    /** 单条岗位开始写入 RAG 时推送，供前端展示「正在同步」岗位名与计时进度条。 */
    private void emitJobSyncing(SseEmitter emitter, BizJobsInfo job, int batchTotal) {
        try {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("jobId", job.getJobid());
            payload.put("jobName", job.getZwmc());
            payload.put("batchTotal", batchTotal);
            emitSse(emitter, "syncing", payload);
        } catch (IOException ex) {
            log.warn("SSE syncing 发送失败, jobId={}", job.getJobid(), ex);
        }
    }

    /**
     * 向 SSE 连接发送一条命名事件，负载为 JSON（Spring 使用 MappingJackson2HttpMessageConverter 序列化 Map）。
     * 对同一 emitter 加锁，避免多条岗位同时 whenComplete 时交错写入响应缓冲区。
     */
    private void emitSse(SseEmitter emitter, String eventName, Map<String, Object> data) throws IOException {
        synchronized (emitter) {
            emitter.send(SseEmitter.event().name(eventName).data(data, MediaType.APPLICATION_JSON));
        }
    }

    /**
     * 批量场景下的「单条」同步包装：内部调用 {@link #syncRagForJob}，捕获所有异常转为 Map 行结果，
     * 不向 CompletableFuture 链上抛错，避免一条失败导致 {@code allOf} 整体异常而其它任务结果丢失。
     */
    private Map<String, Object> syncOneJobInBatch(BizJobsInfo job) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("jobId", job.getJobid());
        row.put("jobName", job.getZwmc());
        try {
            Map<String, Object> detail = syncRagForJob(job);
            row.put("success", true);
            row.put("detail", detail);
            return row;
        } catch (ResponseStatusException ex) {
            row.put("success", false);
            row.put("httpStatus", ex.getStatusCode().value());
            row.put("message", ex.getReason());
            log.warn("批量同步 RAG 单条失败, jobId={}, status={}, reason={}", job.getJobid(), ex.getStatusCode(), ex.getReason());
            return row;
        } catch (Exception ex) {
            row.put("success", false);
            row.put("message", ex.getMessage());
            log.error("批量同步 RAG 单条异常, jobId={}, reason={}", job.getJobid(), ex.getMessage(), ex);
            return row;
        }
    }

    /**
     * 单岗位完整同步链路：
     * <ol>
     *   <li>{@link #buildRagText} 拼 Markdown 风格正文；组 LightRAG 请求体（texts、job_ids、source）。</li>
     *   <li>序列化 JSON；组 GrepRAG 的 filename + text。</li>
     *   <li>LightRAG / GrepRAG 两个 HTTP 使用 {@link ForkJoinPool#commonPool()} 并行提交，<strong>不得</strong>再使用 {@link #ragSyncExecutor}，
     *       否则外层批量任务已占满该池线程时，内层 {@code join} 会永久等待（表现为同步一条后卡住）。</li>
     *   <li>解析 HTTP 状态与 body；任一非 2xx 则抛 502。</li>
     *   <li>从 GrepRAG 响应取 file_path 写入 {@code ragMdPath}，synRag 置 {@code "1"}。</li>
     * </ol>
     */
    private Map<String, Object> syncRagForJob(BizJobsInfo job) {
        BizCompanyInfo company = loadCompanyForJob(job);
        String ragText = jobRagTextBuilder.build(job, company);
        String jobId = job.getJobid();
        Map<String, Object> requestBody = new LinkedHashMap<>();
        requestBody.put("texts", List.of(ragText));
        requestBody.put("job_ids", List.of(jobId));
        requestBody.put("source", ragSource);

        try {
            String requestJson = objectMapper.writeValueAsString(requestBody);
            Map<String, Object> grepRagRequestBody = new LinkedHashMap<>();
            String filename = jobRagTextBuilder.buildMarkdownFilename(job, company);
            grepRagRequestBody.put("filename", filename);
            grepRagRequestBody.put("text", ragText);
            String grepRagRequestJson = objectMapper.writeValueAsString(grepRagRequestBody);

            log.info("岗位同步到 RAG 开始(线程池并行上游), jobId={}, textLength={}, grepFilename={}",
                    jobId, ragText.length(), filename);

            CompletableFuture<AiJobHttpResponse> lightRagFuture = CompletableFuture.supplyAsync(
                    () -> postLightRagInsert(requestJson, jobId),
                    ForkJoinPool.commonPool()
            );
            CompletableFuture<AiJobHttpResponse> grepRagFuture = CompletableFuture.supplyAsync(
                    () -> postGrepRagTextToMd(grepRagRequestJson, jobId),
                    ForkJoinPool.commonPool()
            );

            try {
                CompletableFuture.allOf(lightRagFuture, grepRagFuture).join();
            } catch (CompletionException ex) {
                unwrapRagSyncCompletionException(ex);
            }

            AiJobHttpResponse graphRagUpstream = lightRagFuture.join();
            AiJobHttpResponse grepRagUpstream = grepRagFuture.join();

            Map<String, Object> graphRagBody = parseUpstreamBody(graphRagUpstream);
            log.info("岗位同步到 GraphRAG 完成, jobId={}, statusCode={}", jobId, graphRagUpstream.statusCode());

            if (graphRagUpstream.statusCode() < 200 || graphRagUpstream.statusCode() >= 300) {
                String detail = Objects.toString(graphRagBody.getOrDefault("detail", "GraphRAG 同步失败"), "GraphRAG 同步失败");
                log.error("岗位同步到 GraphRAG 失败, jobId={}, statusCode={}, detail={}", jobId, graphRagUpstream.statusCode(), detail);
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, detail);
            }

            Map<String, Object> grepRagBody = parseUpstreamBody(grepRagUpstream);
            log.info("岗位同步到 GrepRAG 完成, jobId={}, statusCode={}", jobId, grepRagUpstream.statusCode());
            if (grepRagUpstream.statusCode() < 200 || grepRagUpstream.statusCode() >= 300) {
                String detail = Objects.toString(grepRagBody.getOrDefault("detail", "GrepRAG 创建 Markdown 失败"), "GrepRAG 创建 Markdown 失败");
                log.error("岗位同步到 GrepRAG 失败, jobId={}, statusCode={}, detail={}", jobId, grepRagUpstream.statusCode(), detail);
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, detail);
            }

            String ragMdPath = extractRagMdPath(grepRagBody);
            bizJobsRagSyncService.markSynced(jobId, ragMdPath);

            Map<String, Object> result = new HashMap<>();
            result.put("success", true);
            result.put("message", "同步知识库成功");
            result.put("jobId", jobId);
            result.put("synRag", "1");
            result.put("ragMdPath", ragMdPath);
            result.put("graphRag", graphRagBody);
            result.put("grepRag", grepRagBody);
            return result;
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("岗位同步到 RAG 失败, jobId={}, reason={}", jobId, ex.getMessage(), ex);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "调用 ai_job 失败: " + ex.getMessage());
        }
    }

    /** 统计查询范围内已同步岗位数（关联 t_biz_jobs_rag_sync）。 */
    private long countSyncedInScope(String normalizedKeyword, String companyType, String industry) {
        LambdaQueryWrapper<BizJobsInfo> w = new LambdaQueryWrapper<>();
        bizJobListScopeSupport.applyListScope(w, normalizedKeyword, companyType, industry);
        w.inSql(BizJobsInfo::getJobid,
                "SELECT jobid FROM t_biz_jobs_rag_sync WHERE syn_rag = 1");
        return bizJobsInfoService.count(w);
    }

    /** 判断该岗位是否仍需要同步：独立 RAG 状态表未标记 syn_rag=1 视为待同步。 */
    private boolean needsRagSync(BizJobsInfo job) {
        return !bizJobsRagSyncService.isSynced(job.getJobid());
    }

    /** 批量 SSE：未加速时串行（1）；加速时按配置的线程池并行度。 */
    private int resolveBatchMaxParallel(boolean accelerate) {
        if (!accelerate) {
            return 1;
        }
        return Math.max(1, ragSyncParallelism);
    }

    private BizCompanyInfo loadCompanyForJob(BizJobsInfo job) {
        if (job.getYrdw() == null || job.getYrdw().isBlank()) {
            return null;
        }
        return bizCompanyInfoService.getByZzjgdm(job.getYrdw().trim());
    }

    /** 在线程池 worker 中执行：POST LightRAG insert；IOException 包装为 UncheckedIOException 供 join 路径统一处理。 */
    private AiJobHttpResponse postLightRagInsert(String requestJson, String jobId) {
        try {
            log.info("岗位同步 LightRAG HTTP 在线程中开始, jobId={}, path={}", jobId, ragInsertPath);
            return aiJobGatewayService.postJson(ragInsertPath, requestJson);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    @Override
    public Map<String, Object> purgeLightRagBacklog() {
        return doPurgeLightRagBacklog();
    }

    @Override
    public Map<String, Object> lightRagBacklogStats() {
        Map<String, Object> out = new LinkedHashMap<>();
        try {
            log.info("LightRAG 积压统计 HTTP 开始, path={}", lightRagBacklogStatsPath);
            AiJobHttpResponse resp = aiJobGatewayService.get(lightRagBacklogStatsPath, Map.of());
            Map<String, Object> body = parseUpstreamBody(resp);
            if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
                out.put("success", false);
                out.put("httpStatus", resp.statusCode());
                out.put("message", Objects.toString(body.getOrDefault("detail", "LightRAG 积压统计失败"), "LightRAG 积压统计失败"));
                out.put("body", body);
                return out;
            }
            out.put("success", true);
            out.putAll(body);
            return out;
        } catch (IOException e) {
            log.error("LightRAG 积压统计 IO 失败, reason={}", e.getMessage(), e);
            out.put("success", false);
            out.put("message", "调用 ai_job 失败: " + e.getMessage());
            return out;
        }
    }

    /**
     * 清理 LightRAG 中 pending / processing / failed 积压，避免历史半完成文档占用资源。
     * 返回 Map 含 success、candidate_count、success_count、fullyCleared 等；HTTP 非 2xx 时 success=false 并带 message。
     */
    private Map<String, Object> doPurgeLightRagBacklog() {
        Map<String, Object> out = new LinkedHashMap<>();
        try {
            String path = lightRagPurgeNonProcessedPath.replaceAll("/+$", "")
                    + "?dry_run=false&max_concurrent=1";
            log.info("LightRAG 积压清理 HTTP 开始, path={}", path);
            AiJobHttpResponse resp = aiJobGatewayService.postJson(path, "{}");
            Map<String, Object> body = parseUpstreamBody(resp);
            if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
                out.put("success", false);
                out.put("httpStatus", resp.statusCode());
                out.put("message", Objects.toString(body.getOrDefault("detail", "LightRAG 积压清理失败"), "LightRAG 积压清理失败"));
                out.put("body", body);
                log.warn("LightRAG 积压清理失败, status={}, body={}", resp.statusCode(), body);
                return out;
            }
            out.put("success", true);
            out.putAll(body);
            int candidate = toInt(body.get("candidate_count"));
            int successCnt = toInt(body.get("success_count"));
            int notFoundCnt = toInt(body.get("not_found_count"));
            int failureCnt = toInt(body.get("failure_count"));
            int exceptionCnt = toInt(body.get("exception_count"));
            boolean queueCleared = Boolean.TRUE.equals(body.get("queue_cleared"))
                    || toInt(body.get("remaining_non_processed_count")) == 0;
            boolean deepDeleteFullyCleared = Boolean.TRUE.equals(body.get("deep_delete_fully_cleared"));
            boolean fullyCleared = candidate <= 0
                    || deepDeleteFullyCleared
                    || (queueCleared && failureCnt == 0 && exceptionCnt == 0);
            out.put("fullyCleared", fullyCleared);
            out.put("queueCleared", queueCleared);
            out.put("deepDeleteFullyCleared", deepDeleteFullyCleared);
            log.info(
                    "LightRAG 积压清理完成, candidate={}, success={}, failure={}, exception={}, queueCleared={}, fullyCleared={}",
                    candidate,
                    successCnt,
                    failureCnt,
                    exceptionCnt,
                    queueCleared,
                    fullyCleared
            );
            return out;
        } catch (IOException e) {
            log.error("LightRAG 积压清理 IO 失败, reason={}", e.getMessage(), e);
            out.put("success", false);
            out.put("message", "调用 ai_job 失败: " + e.getMessage());
            return out;
        }
    }

    /** 在线程池 worker 中执行：POST GrepRAG text-to-md。 */
    private AiJobHttpResponse postGrepRagTextToMd(String grepRagRequestJson, String jobId) {
        try {
            log.info("岗位同步 GrepRAG HTTP 在线程中开始, jobId={}, path={}", jobId, grepRagTextToMdPath);
            return aiJobGatewayService.postJson(grepRagTextToMdPath, grepRagRequestJson);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private AiJobHttpResponse deleteLightRagDoc(String docId, String jobId) {
        try {
            String path = lightRagDeleteDocPath.replaceAll("/+$", "") + "/" + java.net.URLEncoder.encode(docId, StandardCharsets.UTF_8);
            log.info("岗位下架 LightRAG HTTP 开始, jobId={}, docId={}, path={}", jobId, docId, path);
            return aiJobGatewayService.delete(path);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private AiJobHttpResponse deleteGrepRagMarkdown(String ragMdPath, String jobId) {
        if (ragMdPath == null || ragMdPath.isBlank()) {
            log.info("岗位下架 GrepRAG 跳过（无 ragMdPath）, jobId={}", jobId);
            return new AiJobHttpResponse(404, Map.of(), new byte[0]);
        }
        try {
            String q = "file_path=" + java.net.URLEncoder.encode(ragMdPath.trim(), StandardCharsets.UTF_8);
            String path = grepRagDeleteMdPath.replaceAll("/+$", "") + "?" + q;
            log.info("岗位下架 GrepRAG HTTP 开始, jobId={}, path={}", jobId, path);
            return aiJobGatewayService.delete(path);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String toLightRagDocId(String jobId) {
        String s = jobId == null ? "" : jobId.trim();
        if (s.isEmpty()) {
            return s;
        }
        return s.startsWith("job-") ? s : "job-" + s;
    }

    /**
     * 将 CompletableFuture 链上的 {@link CompletionException} 拆开，把 IO 失败、已包装的 HTTP 异常继续往上抛成 {@link ResponseStatusException}，
     * 供 {@link #syncRagForJob} 统一转换为 502。
     */
    private void unwrapRagSyncCompletionException(CompletionException ex) {
        Throwable cause = ex.getCause() == null ? ex : ex.getCause();
        if (cause instanceof UncheckedIOException uio) {
            IOException ioe = uio.getCause();
            log.error("岗位同步到 RAG 上游 IO 失败, reason={}", ioe != null ? ioe.getMessage() : "", ioe);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                    "调用 ai_job 失败: " + (ioe != null ? ioe.getMessage() : "unknown"));
        }
        if (cause instanceof ResponseStatusException rse) {
            throw rse;
        }
        if (cause instanceof RuntimeException re) {
            throw re;
        }
        throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "调用 ai_job 失败: " + cause.getMessage());
    }

    /** 将 ai_job 返回的字节 body 解析为 Map；非 JSON 时放入 {@code raw} 键避免抛错。 */
    private Map<String, Object> parseUpstreamBody(AiJobHttpResponse upstream) {
        try {
            String body = new String(upstream.body(), StandardCharsets.UTF_8);
            if (body.isBlank()) {
                return Map.of();
            }
            return objectMapper.readValue(body, new TypeReference<Map<String, Object>>() {
            });
        } catch (Exception ignored) {
            return Map.of("raw", new String(upstream.body(), StandardCharsets.UTF_8));
        }
    }

    /** 去掉首尾空白；空串抛 400，避免无意义查库。 */
    private String normalizeJobId(String jobId) {
        String normalized = jobId == null ? "" : jobId.trim();
        if (normalized.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "jobId 不能为空");
        }
        return normalized;
    }

    /** 从 GrepRAG JSON 响应中取 file_path 字符串，供写回 t_biz_jobs_rag_sync.rag_md_path。 */
    private String extractRagMdPath(Map<String, Object> grepRagBody) {
        if (grepRagBody == null) {
            return null;
        }
        Object filePath = grepRagBody.get("file_path");
        if (filePath == null) {
            return null;
        }
        String value = String.valueOf(filePath).trim();
        return value.isEmpty() ? null : value;
    }

    private static int toInt(Object value) {
        if (value instanceof Number n) {
            return n.intValue();
        }
        if (value == null) {
            return 0;
        }
        try {
            return Integer.parseInt(String.valueOf(value).trim());
        } catch (NumberFormatException ignored) {
            return 0;
        }
    }

}
