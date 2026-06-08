<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { apiGet, apiPost, apiPostSse, getStudentId } from "../api/client";
import RagSyncThreeMinuteProgress from "../components/rag/RagSyncThreeMinuteProgress.vue";
import { useRagSyncThreeMinuteProgress } from "../composables/useRagSyncThreeMinuteProgress";
import {
  RAG_SYNC_SECONDS_PER_JOB,
  formatRagSyncHms,
  useRagSyncEtaCountdown,
} from "../composables/useRagSyncEtaCountdown";
const jobs = ref([]);
const page = ref(1);
const pageSize = 20;
const total = ref(0);
const hasMore = ref(true);
const loadingMore = ref(false);
/** 输入框内容：未按回车时仅参与本地过滤；按回车后写入 remoteKeyword 并走接口分页 */
const searchInput = ref("");
/** 最近一次「回车」提交给后端的检索词；空表示全量分页 */
const remoteKeyword = ref("");
/** 为 true 时仅查询已同步知识库（synRag=1）的岗位 */
const syncedOnly = ref(true);
/** 筛选：公司类型（单位性质 job_dwxz）与行业（job_hylb） */
const filterFacets = ref({ companyTypes: [], industries: [] });
const filterFacetsLoading = ref(false);
const filterPanelOpen = ref(true);
const filterRefreshing = ref(false);
const selectedCompanyType = ref("");
const selectedIndustry = ref("");
const error = ref("");
const favoriteJobIds = ref(new Set());
const sentinelRef = ref(null);
const listScrollRef = ref(null);
let observer;
const normalizedJobs = computed(() =>
  (jobs.value || []).map((item) => ({
    job_id: item.id,
    job_title: item.jobName,
    city: item.address,
    district: item.area,
    salary_range_month: item.salaryRange,
    salary_months: "-",
    company_relation: {
      company_name: item.companyName,
      credit_code: item.companyWid || item.companyId
    }
  }))
);

const filtered = computed(() => {
  const q = searchInput.value.trim().toLowerCase();
  if (!q) return normalizedJobs.value;
  return normalizedJobs.value.filter((item) => {
    const text = `${item.job_title || ""} ${item.city || ""} ${item.company_relation?.company_name || ""}`.toLowerCase();
    return text.includes(q);
  });
});

const totalText = computed(() => {
  const draft = searchInput.value.trim();
  const remote = remoteKeyword.value.trim();
  if (remote) {
    return `检索「${remote}」：库内共 ${total.value} 条（当前已加载 ${filtered.value.length} 条）`;
  }
  if (draft) {
    return `本地筛选 ${filtered.value.length} 条（回车可向库内检索）`;
  }
  return `共 ${total.value} 个岗位`;
});
/** 仅输入未回车：本地过滤已加载列表，不展示服务端分页文案 */
const isLocalFilterOnly = computed(() => {
  const draft = searchInput.value.trim();
  const remote = remoteKeyword.value.trim();
  return Boolean(draft) && !remote;
});
const loadedPage = computed(() => Math.max(0, page.value - 1));
const totalPages = computed(() => (total.value > 0 ? Math.ceil(total.value / pageSize) : 0));
const showPageText = computed(() => !isLocalFilterOnly.value && total.value > 0 && totalPages.value > 0);
const pageText = computed(() => {
  const loaded = Math.min(loadedPage.value, totalPages.value);
  return `已加载 ${loaded} / 共 ${totalPages.value} 页`;
});

async function loadFavorites() {
  const sid = getStudentId();
  if (!sid) {
    favoriteJobIds.value = new Set();
    return;
  }
  try {
    const f = await apiGet(`/api/me/favorites?student_id=${encodeURIComponent(sid)}`);
    favoriteJobIds.value = new Set(f.job_ids || []);
  } catch {
    favoriteJobIds.value = new Set();
  }
}

async function toggleFavorite(jobId, ev) {
  ev?.preventDefault();
  ev?.stopPropagation();
  const sid = getStudentId();
  if (!sid) {
    window.alert("请先登录");
    return;
  }
  try {
    const resp = await apiPost("/api/me/favorites/toggle", { student_id: sid, job_id: jobId });
    favoriteJobIds.value = new Set(resp.favorite_jobs || []);
  } catch (err) {
    window.alert(err.message || "操作失败");
  }
}

function isFavorite(jobId) {
  return favoriteJobIds.value.has(jobId);
}

async function loadNextPage() {
  if (loadingMore.value || !hasMore.value) return;
  loadingMore.value = true;
  try {
    const rk = remoteKeyword.value.trim();
    const kw = rk ? `&keyword=${encodeURIComponent(rk)}` : "";
    const sync = `&syncedOnly=${syncedOnly.value}`;
    const ct = selectedCompanyType.value
      ? `&companyType=${encodeURIComponent(selectedCompanyType.value)}`
      : "";
    const ind = selectedIndustry.value ? `&industry=${encodeURIComponent(selectedIndustry.value)}` : "";
    const data = await apiGet(
      `/api/jobs/paged?page=${page.value}&pageSize=${pageSize}${kw}${sync}${ct}${ind}`
    );
    const items = data?.items || [];
    jobs.value.push(...items);
    total.value = Number(data?.total || 0);
    hasMore.value = Boolean(data?.hasMore);
    page.value += 1;
  } catch (err) {
    error.value = err.message;
  } finally {
    loadingMore.value = false;
  }
}

async function loadFilterFacets() {
  filterFacetsLoading.value = true;
  try {
    const data = await apiGet(`/api/jobs/filter-facets${buildJobScopeQueryParams()}`);
    filterFacets.value = {
      companyTypes: data?.companyTypes || [],
      industries: data?.industries || []
    };
  } catch {
    filterFacets.value = { companyTypes: [], industries: [] };
  } finally {
    filterFacetsLoading.value = false;
  }
}

/** 与岗位列表、RAG 同步统计共用的查询范围参数 */
function buildJobScopeQueryParams() {
  const params = new URLSearchParams();
  const rk = remoteKeyword.value.trim();
  if (rk) params.set("keyword", rk);
  if (selectedCompanyType.value) params.set("companyType", selectedCompanyType.value);
  if (selectedIndustry.value) params.set("industry", selectedIndustry.value);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

async function applyFilterScope() {
  resetPagedList();
  await Promise.all([loadFilterFacets(), loadRagStats()]);
  await loadNextPage();
}

async function refreshFilterData() {
  if (filterRefreshing.value) return;
  filterRefreshing.value = true;
  try {
    await Promise.all([loadFilterFacets(), loadRagStats()]);
  } finally {
    filterRefreshing.value = false;
  }
}

function toggleFilterPanel() {
  filterPanelOpen.value = !filterPanelOpen.value;
}

function toggleCompanyType(code) {
  selectedCompanyType.value = selectedCompanyType.value === code ? "" : code;
  void applyFilterScope();
}

function toggleIndustry(code) {
  selectedIndustry.value = selectedIndustry.value === code ? "" : code;
  void applyFilterScope();
}

function clearCompanyTypeFilter() {
  if (!selectedCompanyType.value) return;
  selectedCompanyType.value = "";
  void applyFilterScope();
}

function clearIndustryFilter() {
  if (!selectedIndustry.value) return;
  selectedIndustry.value = "";
  void applyFilterScope();
}

function clearFacetFilters() {
  if (!selectedCompanyType.value && !selectedIndustry.value) return;
  selectedCompanyType.value = "";
  selectedIndustry.value = "";
  void applyFilterScope();
}

/** 回车：用当前输入向服务端检索并重置无限滚动 */
function resetPagedList() {
  jobs.value = [];
  page.value = 1;
  hasMore.value = true;
  total.value = 0;
  error.value = "";
}

function onSearchEnter() {
  remoteKeyword.value = searchInput.value.trim();
  resetPagedList();
  void Promise.all([loadFilterFacets(), loadRagStats()]).then(() => loadNextPage());
}

const hasFacetFilter = computed(
  () => Boolean(selectedCompanyType.value || selectedIndustry.value)
);

const selectedFilterSummary = computed(() => {
  const parts = [];
  if (selectedCompanyType.value) {
    const item = (filterFacets.value.companyTypes || []).find((i) => i.code === selectedCompanyType.value);
    parts.push(`公司类型：${item?.label || selectedCompanyType.value}`);
  }
  if (selectedIndustry.value) {
    const item = (filterFacets.value.industries || []).find((i) => i.code === selectedIndustry.value);
    parts.push(`行业：${item?.label || selectedIndustry.value}`);
  }
  return parts.join(" · ");
});

watch(syncedOnly, () => {
  resetPagedList();
  void loadNextPage();
});

watch(remoteKeyword, () => {
  void loadFilterFacets();
  if (ragPanelOpen.value) void loadRagStats();
});

onMounted(async () => {
  await loadFavorites();
  await loadFilterFacets();
  await loadNextPage();
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        loadNextPage();
      }
    },
    { root: listScrollRef.value, rootMargin: "200px 0px" }
  );
  if (sentinelRef.value) observer.observe(sentinelRef.value);
});

onBeforeUnmount(() => {
  window.clearTimeout(ragStatsDebounceTimer);
  if (observer) observer.disconnect();
  if (syncRunning.value) {
    void ragFireCancel();
    ragAbort.value?.abort();
  }
});

/** ---------- 知识库 RAG 批量同步（默认折叠） ---------- */
const ragPanelOpen = ref(false);
const ragStats = ref({ total: 0, synced: 0, unsynced: 0, keyword: "" });
const ragBacklog = ref({
  pending: 0,
  processing: 0,
  failed: 0,
  backlogTotal: 0,
  processed: 0,
  loaded: false,
  error: ""
});
const backlogLoading = ref(false);
const ragLive = ref({ total: 0, synced: 0, unsynced: 0, batchIndex: 0, batchTotal: 0 });
const syncRunning = ref(false);
const syncLog = ref([]);
const ragAbort = ref(null);
const syncDoneSummary = ref(null);
const ragPaused = ref(false);
/** 加速同步：默认关闭（串行）；开启后按服务端配置并行处理多条岗位 */
const ragAccelerate = ref(false);
/** 同步开始前清理 LightRAG 积压（pending/processing/failed），默认开启 */
const ragPurgeBeforeSync = ref(true);
/** 单独清理积压（不触发同步） */
const purgeRunning = ref(false);
const purgeLog = ref([]);
const purgeDoneSummary = ref(null);
/** 知识库面板当前 Tab：sync | purge */
const ragPanelTab = ref("sync");

/** ---------- 串行同步：3 分钟刻度进度条 + 当前岗位名 ---------- */
const currentSyncJobName = ref("");
/** 加速模式下并行同步中的岗位 id -> 名称 */
const activeSyncJobs = ref(new Map());

/** 加速模式下服务端并行度（来自 SSE stats） */
const ragMaxParallel = ref(1);

const ragEta = useRagSyncEtaCountdown();
const {
  displayHms: ragEtaDisplayHms,
  syncAnchor: syncRagEtaAnchor,
  startTicker: startRagEtaTicker,
  pause: pauseRagEtaCountdown,
  resume: resumeRagEtaCountdown,
  stop: stopRagEtaCountdown,
  estimateSeconds: estimateRagSyncSeconds,
} = ragEta;

const ragIdleEtaHms = computed(() => {
  const jobs = Math.max(0, Number(ragStats.value.unsynced || 0));
  if (jobs <= 0) return "00:00:00";
  const sec = estimateRagSyncSeconds(jobs, ragAccelerate.value, ragMaxParallel.value);
  return formatRagSyncHms(sec);
});

function refreshRagEtaAnchor(syncRunningFlag = syncRunning.value) {
  syncRagEtaAnchor({
    ragLive: ragLive.value,
    syncRunning: syncRunningFlag,
    accelerate: ragAccelerate.value,
    maxParallel: ragMaxParallel.value,
  });
}

const ragSerialProgress = useRagSyncThreeMinuteProgress();
const {
  elapsedMs: ragSerialElapsedMs,
  fillPct: ragSerialFillPct,
  fillPctRounded: ragSerialFillPctRounded,
  fillColorClass: ragSerialFillColorClass,
  progressLabel: ragSerialProgressLabel,
  overScale: ragSerialOverScale,
  start: startRagSerialProgress,
  stop: stopRagSerialProgress,
  reset: resetRagSerialProgress,
} = ragSerialProgress;

function resolveJobName(data) {
  const name = String(data?.jobName || data?.job_name || "").trim();
  if (name) return name;
  const id = String(data?.jobId || data?.job_id || "").trim();
  return id || "未知岗位";
}

function onJobSyncing(data) {
  const id = String(data?.jobId || data?.job_id || "").trim();
  const name = resolveJobName(data);
  if (ragAccelerate.value) {
    if (!id) return;
    const next = new Map(activeSyncJobs.value);
    next.set(id, name);
    activeSyncJobs.value = next;
    return;
  }
  currentSyncJobName.value = name;
  startRagSerialProgress();
}

function onJobProgressDone(item) {
  const id = String(item?.jobId || item?.job_id || "").trim();
  if (ragAccelerate.value) {
    if (id && activeSyncJobs.value.has(id)) {
      const next = new Map(activeSyncJobs.value);
      next.delete(id);
      activeSyncJobs.value = next;
    }
    return;
  }
  stopRagSerialProgress();
  currentSyncJobName.value = "";
}

function resetSyncJobDisplay() {
  currentSyncJobName.value = "";
  activeSyncJobs.value = new Map();
  resetRagSerialProgress();
}

const showSerialTimeProgress = computed(() => syncRunning.value && !ragAccelerate.value);

const activeSyncJobLabel = computed(() => {
  if (!syncRunning.value) return "";
  if (ragAccelerate.value) {
    const names = [...activeSyncJobs.value.values()];
    if (!names.length) return "等待岗位开始同步…";
    if (names.length === 1) return `正在同步：${names[0]}`;
    return `正在同步 ${names.length} 条：${names.join("、")}`;
  }
  return currentSyncJobName.value ? `正在同步：${currentSyncJobName.value}` : "等待岗位开始同步…";
});

async function ragFireCancel() {
  try {
    await apiPost("/api/jobs/sync-rag/cancel", {});
  } catch {
    /* 忽略：连接可能已断开 */
  }
}

/** 同步进行中且拿到本批总数时，用「本批条数」驱动进度条，避免全库已同步 99% 时条几乎不动、像没进度 */
const progressPct = computed(() => {
  const bt = Number(ragLive.value.batchTotal || 0);
  const bi = Number(ragLive.value.batchIndex || 0);
  if (syncRunning.value && bt > 0) {
    return Math.min(100, Math.round((bi / bt) * 100));
  }
  const t = Number(ragLive.value.total || 0);
  if (t <= 0) return 0;
  const s = Number(ragLive.value.synced || 0);
  return Math.min(100, Math.round((s / t) * 100));
});

const progressIndeterminate = computed(() => {
  if (!syncRunning.value) return false;
  const bt = Number(ragLive.value.batchTotal || 0);
  const bi = Number(ragLive.value.batchIndex || 0);
  const t = Number(ragLive.value.total || 0);
  if (bt > 0 && bi === 0) return true;
  if (bt === 0 && t > 0) return true;
  return false;
});

const progressLabel = computed(() => {
  if (progressIndeterminate.value) {
    const bt = Number(ragLive.value.batchTotal || 0);
    if (bt > 0) return `本批 0 / ${bt}（首条完成后显示百分比）`;
    return "已连接，等待服务端推送统计…";
  }
  const bt = Number(ragLive.value.batchTotal || 0);
  const bi = Number(ragLive.value.batchIndex || 0);
  if (syncRunning.value && bt > 0) {
    return `${progressPct.value}%（本批 ${bi} / ${bt}）`;
  }
  return `${progressPct.value}%（当前范围内已同步 / 总岗位）`;
});

function applyStatsToLive(s) {
  ragLive.value = {
    total: Number(s?.total ?? 0),
    synced: Number(s?.synced ?? 0),
    unsynced: Number(s?.unsynced ?? 0),
    batchIndex: Number(s?.batchIndex ?? ragLive.value.batchIndex ?? 0),
    batchTotal: Number(s?.batchTotal ?? ragLive.value.batchTotal ?? 0)
  };
  if (s?.maxParallel != null) {
    ragMaxParallel.value = Math.max(1, Number(s.maxParallel) || 1);
  }
  refreshRagEtaAnchor();
}

async function loadRagStats() {
  try {
    const s = await apiGet(`/api/jobs/rag-sync/stats${buildJobScopeQueryParams()}`);
    ragStats.value = {
      total: Number(s?.total ?? 0),
      synced: Number(s?.synced ?? 0),
      unsynced: Number(s?.unsynced ?? 0),
      keyword: String(s?.keyword ?? remoteKeyword.value.trim() ?? "")
    };
    ragLive.value = {
      total: ragStats.value.total,
      synced: ragStats.value.synced,
      unsynced: ragStats.value.unsynced,
      batchIndex: 0,
      batchTotal: 0
    };
    refreshRagEtaAnchor(false);
  } catch {
    ragStats.value = { total: 0, synced: 0, unsynced: 0, keyword: "" };
    ragLive.value = { total: 0, synced: 0, unsynced: 0, batchIndex: 0, batchTotal: 0 };
  }
}

async function loadRagBacklogStats() {
  if (backlogLoading.value) return;
  backlogLoading.value = true;
  try {
    const b = await apiGet("/api/jobs/rag-sync/backlog-stats");
    if (b?.success === false) {
      ragBacklog.value = {
        pending: 0,
        processing: 0,
        failed: 0,
        backlogTotal: 0,
        processed: 0,
        loaded: false,
        error: String(b?.message || "无法读取 LightRAG 积压")
      };
      return;
    }
    ragBacklog.value = {
      pending: Number(b?.pending ?? 0),
      processing: Number(b?.processing ?? 0),
      failed: Number(b?.failed ?? 0),
      backlogTotal: Number(b?.backlog_total ?? 0),
      processed: Number(b?.processed ?? 0),
      loaded: true,
      error: ""
    };
  } catch (e) {
    ragBacklog.value = {
      pending: 0,
      processing: 0,
      failed: 0,
      backlogTotal: 0,
      processed: 0,
      loaded: false,
      error: e?.message || "无法连接 ai_job"
    };
  } finally {
    backlogLoading.value = false;
  }
}

async function refreshRagPanelStats() {
  await Promise.all([loadRagStats(), loadRagBacklogStats()]);
}

let ragStatsDebounceTimer;
watch(searchInput, () => {
  if (!ragPanelOpen.value) return;
  window.clearTimeout(ragStatsDebounceTimer);
  ragStatsDebounceTimer = window.setTimeout(() => {
    void refreshRagPanelStats();
  }, 400);
});

watch(ragAccelerate, () => {
  if (syncRunning.value) {
    refreshRagEtaAnchor(true);
  }
});

function toggleRagPanel() {
  ragPanelOpen.value = !ragPanelOpen.value;
  if (ragPanelOpen.value) {
    void refreshRagPanelStats();
  }
}

function switchRagPanelTab(tab) {
  if (tab !== "sync" && tab !== "purge") return;
  ragPanelTab.value = tab;
  if (tab === "purge" && !ragBacklog.value.loaded && !backlogLoading.value) {
    void loadRagBacklogStats();
  }
}

function pushLog(line) {
  const next = [...syncLog.value, line];
  if (next.length > 40) next.splice(0, next.length - 40);
  syncLog.value = next;
}

function pushPurgeLog(line) {
  const next = [...purgeLog.value, line];
  if (next.length > 60) next.splice(0, next.length - 60);
  purgeLog.value = next;
}

function appendPurgeDetailLines(data, pushFn) {
  if (!data || data.success !== true) {
    pushFn(`清理失败：${data?.message || data?.detail || "未知错误"}`);
    return;
  }
  const candidate = Number(data.candidate_count ?? 0);
  const successCnt = Number(data.success_count ?? 0);
  const notFound = Number(data.not_found_count ?? 0);
  const failure = Number(data.failure_count ?? 0);
  const exception = Number(data.exception_count ?? 0);
  pushFn(
    `统计：候选 ${candidate}，成功 ${successCnt}，未找到 ${notFound}，失败 ${failure}，异常 ${exception}。`
  );
  if (candidate === 0) {
    pushFn("结论：当前无 pending/processing/failed 积压。");
  } else if (data.fullyCleared === true || data.deepDeleteFullyCleared === true) {
    pushFn("结论：积压已全部清理（含 Neo4j/Milvus 深删）。");
  } else if (data.queueCleared === true || data.queue_cleared === true) {
    pushFn(
      "结论：任务队列已清空（doc_status 无积压）；部分 dup/failed 记录在 Neo4j 深删失败，一般不影响后续同步。"
    );
  } else {
    pushFn("结论：清理不完整；请重试或查看 ai_job 日志。");
  }
  const remaining = Number(data.remaining_non_processed_count ?? NaN);
  if (Number.isFinite(remaining)) {
    pushFn(`清理后 doc_status 剩余非 processed 条目：${remaining}。`);
  }
  const strip = data.disk_strip;
  if (strip && (strip.doc_status_entries_removed || strip.doc_status_files_rewritten)) {
    pushFn(
      `磁盘 doc_status 兜底：改写 ${strip.doc_status_files_rewritten ?? 0} 个文件，移除 ${strip.doc_status_entries_removed ?? 0} 条非 processed 记录。`
    );
  }
  const failures = Array.isArray(data.failures) ? data.failures : [];
  const errors = Array.isArray(data.errors) ? data.errors : [];
  const sample = [...failures.slice(0, 5), ...errors.slice(0, 3)];
  for (const item of sample) {
    const id = item.doc_id || "?";
    const msg = item.message || item.error || item.status || "未知原因";
    pushFn(`  · ${id}：${msg}`);
  }
  const hidden = failures.length + errors.length - sample.length;
  if (hidden > 0) {
    pushFn(`  … 另有 ${hidden} 条失败/异常未展示`);
  }
}

async function purgeLightRagBacklog() {
  if (purgeRunning.value || syncRunning.value) return;
  ragPanelTab.value = "purge";
  purgeLog.value = [];
  purgeDoneSummary.value = null;
  purgeRunning.value = true;
  pushPurgeLog("开始清理 LightRAG 积压（pending / processing / failed）…");
  pushPurgeLog("说明：仅清理 LightRAG 任务队列，不会修改岗位 synRag 状态。");
  try {
    const data = await apiPost("/api/jobs/rag-sync/purge-backlog", {});
    appendPurgeDetailLines(data, pushPurgeLog);
    purgeDoneSummary.value = {
      candidate: Number(data?.candidate_count ?? 0),
      success: Number(data?.success_count ?? 0),
      failure: Number(data?.failure_count ?? 0),
      fullyCleared: data?.fullyCleared === true,
      queueCleared: data?.queueCleared === true || data?.queue_cleared === true
    };
  } catch (e) {
    pushPurgeLog(`错误：${e?.message || e}`);
  } finally {
    purgeRunning.value = false;
    await loadRagBacklogStats();
  }
}

async function startRagSync() {
  if (syncRunning.value) return;
  ragPanelTab.value = "sync";
  syncDoneSummary.value = null;
  syncLog.value = [];
  ragPaused.value = false;
  await loadRagStats();
  await loadRagBacklogStats();
  if (Number(ragStats.value.unsynced || 0) <= 0) {
    const scopeHint = [
      remoteKeyword.value.trim() ? `关键词「${remoteKeyword.value.trim()}」` : "",
      selectedFilterSummary.value
    ]
      .filter(Boolean)
      .join(" · ");
    pushLog(
      scopeHint
        ? `当前范围内没有待同步岗位（${scopeHint} 下 synRag≠1 的条数为 0）。`
        : "当前没有待同步岗位（synRag≠1）。"
    );
    return;
  }
  syncRunning.value = true;
  resetSyncJobDisplay();
  startRagEtaTicker();
  refreshRagEtaAnchor(true);
  const ac = new AbortController();
  ragAbort.value = ac;
  const ragBody = {
    keyword: remoteKeyword.value.trim(),
    companyType: selectedCompanyType.value,
    industry: selectedIndustry.value,
    accelerate: ragAccelerate.value,
    purgeBeforeSync: ragPurgeBeforeSync.value
  };
  if (ragPurgeBeforeSync.value) {
    pushLog("已开启同步前清理：将删除 LightRAG 中 pending/processing/failed 积压。");
  }
  if (ragAccelerate.value) {
    pushLog("已开启加速：本批将并行同步（并行度由服务端配置）。");
  } else {
    pushLog("未开启加速：本批将串行同步（一次 1 条，更稳定）。");
  }
  try {
    await apiPostSse(
      "/api/jobs/sync-rag/pending",
      ragBody,
      {
        signal: ac.signal,
        onEvent: (name, data) => {
          if (name === "stats") {
            applyStatsToLive(data);
            pushLog(
              `统计：总数 ${data.total}，已同步 ${data.synced}，未同步 ${data.unsynced}，本批 ${data.batchTotal ?? 0} 条${
                data.keyword ? `（关键词「${data.keyword}」）` : "（全库）"
              }${data.accelerate ? ` · 加速并行×${data.maxParallel ?? "?"}` : " · 串行"}。`
            );
          } else if (name === "purge") {
            appendPurgeDetailLines(data, pushLog);
          } else if (name === "error") {
            pushLog(`无法开始：${data.detail || JSON.stringify(data)}`);
          } else if (name === "syncing") {
            onJobSyncing(data);
          } else if (name === "progress") {
            applyStatsToLive(data);
            const it = data.item || {};
            const ok = it.success === true;
            const skip = it.skipped === true;
            onJobProgressDone(it);
            pushLog(
              `[${data.batchIndex}/${data.batchTotal}] ${resolveJobName(it)} — ${
                skip ? "跳过" : ok ? "成功" : "失败"
              }${it.message ? `：${it.message}` : ""}`
            );
          } else if (name === "done") {
            syncDoneSummary.value = data;
            ragPaused.value = false;
            pushLog(
              `结束：成功 ${data.succeeded ?? 0}，失败 ${data.failed ?? 0}，跳过 ${data.skipped ?? 0}${
                data.cancelled ? "（已取消）" : ""
              }。`
            );
          }
        }
      }
    );
  } catch (e) {
    if (e?.name !== "AbortError") {
      pushLog(`错误：${e?.message || e}`);
    }
  } finally {
    syncRunning.value = false;
    ragPaused.value = false;
    ragAbort.value = null;
    resetSyncJobDisplay();
    stopRagEtaCountdown();
    await refreshRagPanelStats();
  }
}

async function pauseRagSync() {
  if (!syncRunning.value || ragPaused.value) return;
  try {
    await apiPost("/api/jobs/sync-rag/pause", {});
    ragPaused.value = true;
    pauseRagEtaCountdown();
    pushLog("已暂停：未开始的岗位会排队等待；进行中的会跑完。");
  } catch (e) {
    pushLog(`暂停失败：${e?.message || e}`);
  }
}

async function resumeRagSync() {
  if (!syncRunning.value || !ragPaused.value) return;
  try {
    await apiPost("/api/jobs/sync-rag/resume", {});
    ragPaused.value = false;
    resumeRagEtaCountdown();
    refreshRagEtaAnchor(true);
    pushLog("已继续同步。");
  } catch (e) {
    pushLog(`继续失败：${e?.message || e}`);
  }
}

async function cancelRagSync() {
  ragAbort.value?.abort();
  await ragFireCancel();
  ragPaused.value = false;
}
</script>

<template>
  <div>
    <section class="hero">
      <h1>岗位列表</h1>
      <p>统一浏览岗位、企业与学生画像，让信息不再割裂。</p>
    </section>
    <div class="container">
      <main class="panel">
        <div class="toolbar sticky-toolbar">
          <input
            v-model="searchInput"
            class="search"
            placeholder="职位名 / 工作地点 / 用人单位 — 输入即本地筛选，回车查库"
            @keydown.enter.prevent="onSearchEnter"
          />
          <div class="toolbar-meta">
            <router-link class="me-link" to="/me">我的</router-link>
            <span class="count">{{ totalText }}</span>
            <span v-if="showPageText" class="count">{{ pageText }}</span>
          </div>
        </div>
        <label class="switch-line">
          <input v-model="syncedOnly" type="checkbox" />
          仅显示已同步知识库
        </label>
        <section class="job-facet-panel" aria-label="岗位筛选">
          <div class="job-facet-head">
            <h2 class="job-facet-title">筛选</h2>
            <div class="job-facet-actions">
              <button
                type="button"
                class="btn-linkish"
                :disabled="filterFacetsLoading || filterRefreshing"
                @click="refreshFilterData"
              >
                {{ filterRefreshing ? "刷新中…" : "刷新" }}
              </button>
              <button type="button" class="btn-linkish" @click="toggleFilterPanel">
                {{ filterPanelOpen ? "收起" : "展开" }}
              </button>
              <button
                v-if="hasFacetFilter && filterPanelOpen"
                type="button"
                class="btn-linkish job-facet-clear"
                @click="clearFacetFilters"
              >
                清除筛选
              </button>
            </div>
          </div>
          <p v-if="hasFacetFilter && !filterPanelOpen" class="job-facet-collapsed-hint muted">
            已选：{{ selectedFilterSummary }}
          </p>
          <template v-if="filterPanelOpen">
          <div v-if="filterFacetsLoading && !filterFacets.companyTypes.length" class="job-facet-loading muted">统计加载中…</div>
          <div class="job-facet-group">
            <div class="job-facet-label">公司类型（单位性质）</div>
            <div class="job-facet-chips">
              <button
                type="button"
                class="facet-chip"
                :class="{ active: !selectedCompanyType }"
                @click="clearCompanyTypeFilter"
              >
                全部
              </button>
              <button
                v-for="item in filterFacets.companyTypes"
                :key="'ct-' + item.code"
                type="button"
                class="facet-chip"
                :class="{ active: selectedCompanyType === item.code }"
                :title="`${item.label}：共 ${item.total} 个岗位，已同步 ${item.synced}`"
                @click="toggleCompanyType(item.code)"
              >
                <span class="facet-chip-label">{{ item.label }}</span>
                <span class="facet-chip-count">{{ item.total }} / {{ item.synced }}</span>
              </button>
            </div>
          </div>
          <div class="job-facet-group">
            <div class="job-facet-label">行业性质</div>
            <div class="job-facet-chips job-facet-chips--scroll">
              <button
                type="button"
                class="facet-chip"
                :class="{ active: !selectedIndustry }"
                @click="clearIndustryFilter"
              >
                全部
              </button>
              <button
                v-for="item in filterFacets.industries"
                :key="'ind-' + item.code"
                type="button"
                class="facet-chip"
                :class="{ active: selectedIndustry === item.code }"
                :title="`${item.label}：共 ${item.total} 个岗位，已同步 ${item.synced}`"
                @click="toggleIndustry(item.code)"
              >
                <span class="facet-chip-label">{{ item.label }}</span>
                <span class="facet-chip-count">{{ item.total }} / {{ item.synced }}</span>
              </button>
            </div>
          </div>
          <p class="job-facet-foot muted">数字格式：岗位总数 / 已同步数；与列表、知识库同步范围一致（关键词需回车查库）。</p>
          </template>
        </section>
        <div class="rag-toolbar-foot">
          <button type="button" class="btn-rag-toggle" @click="toggleRagPanel">
            {{ ragPanelOpen ? "收起「知识库同步」" : "展开「知识库同步」" }}
          </button>
        </div>
        <section v-show="ragPanelOpen" class="rag-sync-panel" aria-label="知识库同步">
          <div class="rag-sync-head">
            <h2 class="rag-sync-title">知识库 RAG</h2>
            <nav class="rag-tab-bar" role="tablist" aria-label="RAG 操作">
              <button
                type="button"
                role="tab"
                class="rag-tab"
                :class="{ active: ragPanelTab === 'sync' }"
                :aria-selected="ragPanelTab === 'sync'"
                @click="switchRagPanelTab('sync')"
              >
                同步岗位
                <span v-if="syncRunning" class="rag-tab-badge rag-tab-badge--live">进行中</span>
              </button>
              <button
                type="button"
                role="tab"
                class="rag-tab"
                :class="{ active: ragPanelTab === 'purge' }"
                :aria-selected="ragPanelTab === 'purge'"
                @click="switchRagPanelTab('purge')"
              >
                清理积压
                <span v-if="ragBacklog.backlogTotal > 0" class="rag-tab-badge">{{ ragBacklog.backlogTotal }}</span>
              </button>
            </nav>
          </div>

          <!-- Tab：同步岗位 -->
          <div v-show="ragPanelTab === 'sync'" class="rag-tab-panel" role="tabpanel">
            <p class="rag-sync-desc muted">
              <template v-if="remoteKeyword.trim() || hasFacetFilter">
                统计与<strong>同步范围</strong>与上方筛选一致<template v-if="remoteKeyword.trim()">（关键词「<strong>{{ remoteKeyword.trim() }}</strong>」）</template><template v-if="selectedFilterSummary">（{{ selectedFilterSummary }}）</template>。仅处理该范围内尚未写入 RAG 的岗位。
              </template>
              <template v-else>
                统计与同步范围为<strong>全库</strong>未入库岗位；筛选或输入关键词后数字会更新，点「开始同步」仅同步当前范围内未写入 RAG 的条目。
              </template>
            </p>
            <div class="rag-stats-row">
              <div class="rag-stat"><span class="lbl">总岗位</span><strong>{{ ragLive.total }}</strong></div>
              <div class="rag-stat"><span class="lbl">已同步</span><strong class="ok">{{ ragLive.synced }}</strong></div>
              <div class="rag-stat"><span class="lbl">未同步</span><strong class="warn">{{ ragLive.unsynced }}</strong></div>
            </div>
            <div v-if="syncRunning || ragStats.unsynced > 0" class="rag-eta-block" aria-live="polite">
              <div class="rag-eta-main">
                <span class="lbl">{{ syncRunning ? "剩余时间" : "预计耗时" }}</span>
                <strong class="rag-eta-time">{{ syncRunning ? ragEtaDisplayHms : ragIdleEtaHms }}</strong>
              </div>
              <p class="rag-eta-hint muted">
                按每岗约 {{ RAG_SYNC_SECONDS_PER_JOB }} 秒估算
                <template v-if="syncRunning">
                  · 未同步 {{ ragLive.unsynced }} 条
                  <template v-if="ragLive.batchTotal > 0">（本批剩余 {{ Math.max(0, ragLive.batchTotal - ragLive.batchIndex) }} 条）</template>
                  <template v-if="ragPaused"> · 已暂停</template>
                </template>
                <template v-else-if="ragAccelerate"> · 加速模式已开启（按并行度折算）</template>
              </p>
            </div>
            <RagSyncThreeMinuteProgress
              v-if="showSerialTimeProgress"
              :running="true"
              :elapsed-ms="ragSerialElapsedMs"
              :fill-pct="ragSerialFillPct"
              :fill-pct-rounded="ragSerialFillPctRounded"
              :fill-color-class="ragSerialFillColorClass"
              :progress-label="ragSerialProgressLabel"
              :over-scale="ragSerialOverScale"
              :job-name="currentSyncJobName"
              title="单条同步耗时"
            />
            <div
              v-else-if="syncRunning && ragAccelerate"
              class="rag-progress-wrap"
              role="progressbar"
              :aria-valuenow="progressIndeterminate ? undefined : progressPct"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="progressLabel"
            >
              <p v-if="activeSyncJobLabel" class="rag-sync-job-name" :title="activeSyncJobLabel">
                {{ activeSyncJobLabel }}
              </p>
              <div class="rag-progress-track rag-progress-track--minute-zones" :class="{ 'rag-progress-track--busy': progressIndeterminate }">
                <div
                  class="rag-progress-fill rag-batch-fill"
                  :class="{ 'rag-progress-fill--pulse': progressIndeterminate }"
                  :style="progressIndeterminate ? {} : { width: progressPct + '%' }"
                />
              </div>
              <span class="rag-progress-label">{{ progressLabel }}</span>
            </div>
            <div
              v-else-if="syncRunning"
              class="rag-progress-wrap"
              role="progressbar"
              :aria-valuenow="progressIndeterminate ? undefined : progressPct"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="progressLabel"
            >
              <div class="rag-progress-track" :class="{ 'rag-progress-track--busy': progressIndeterminate }">
                <div
                  class="rag-progress-fill"
                  :class="{ 'rag-progress-fill--pulse': progressIndeterminate }"
                  :style="progressIndeterminate ? {} : { width: progressPct + '%' }"
                />
              </div>
              <span class="rag-progress-label">{{ progressLabel }}</span>
            </div>
            <div v-if="ragLive.batchTotal > 0 && syncRunning" class="rag-batch-hint muted">
              本批：{{ ragLive.batchIndex }} / {{ ragLive.batchTotal }}（与进度条一致）
              · {{ ragAccelerate ? "加速并行" : "串行" }}
            </div>
            <label class="switch-line rag-accelerate-line">
              <input v-model="ragPurgeBeforeSync" type="checkbox" :disabled="syncRunning" />
              同步前清理 LightRAG 积压（pending/processing/failed，默认开启）
            </label>
            <label class="switch-line rag-accelerate-line">
              <input v-model="ragAccelerate" type="checkbox" :disabled="syncRunning" />
              加速同步（并行处理多条，默认关闭；开启后更快但占用更多 ai_job 资源）
            </label>
            <div class="rag-actions">
              <button type="button" class="btn primary rag-sync-btn" :disabled="syncRunning || ragStats.unsynced <= 0" @click="startRagSync">
                {{ syncRunning ? "同步中…" : "开始同步未入库岗位" }}
              </button>
              <button
                v-if="syncRunning"
                type="button"
                class="btn secondary"
                :disabled="ragPaused"
                @click="pauseRagSync"
              >
                暂停
              </button>
              <button
                v-if="syncRunning && ragPaused"
                type="button"
                class="btn secondary"
                @click="resumeRagSync"
              >
                继续
              </button>
              <button v-if="syncRunning" type="button" class="btn secondary" @click="cancelRagSync">取消</button>
            </div>
            <p v-if="syncRunning && ragPaused" class="rag-paused-hint muted">当前为暂停状态，未开始的岗位不会继续执行，点「继续」恢复。</p>
            <p v-if="syncDoneSummary" class="rag-done muted">
              上次同步：成功 {{ syncDoneSummary.succeeded }}，失败 {{ syncDoneSummary.failed
              }}<template v-if="syncDoneSummary.skipped != null">，跳过 {{ syncDoneSummary.skipped }}</template
              ><template v-if="syncDoneSummary.cancelled">（已取消）</template>。
            </p>
            <div class="rag-log-wrap">
              <div class="rag-log-title">同步日志</div>
              <ul class="rag-log">
                <li v-for="(line, idx) in syncLog" :key="'s-' + idx" class="rag-log-line">{{ line }}</li>
                <li v-if="!syncLog.length" class="rag-log-line muted">点击「开始同步」后在此展示 SSE 推送内容。</li>
              </ul>
            </div>
          </div>

          <!-- Tab：清理积压 -->
          <div v-show="ragPanelTab === 'purge'" class="rag-tab-panel" role="tabpanel">
            <p class="rag-sync-desc muted">
              清理 ai_job LightRAG 中 pending / processing / failed 文档，释放任务队列与模型占用；<strong>不会</strong>修改岗位 synRag 状态。
            </p>
            <div class="rag-backlog-block rag-backlog-block--tab">
              <div class="rag-backlog-head">
                <h3 class="rag-backlog-title">当前积压</h3>
                <button
                  type="button"
                  class="btn-linkish"
                  :disabled="backlogLoading || purgeRunning"
                  @click="loadRagBacklogStats"
                >
                  {{ backlogLoading ? "刷新中…" : "刷新" }}
                </button>
              </div>
              <div v-if="ragBacklog.error" class="rag-backlog-error muted">{{ ragBacklog.error }}</div>
              <div v-else class="rag-stats-row rag-stats-row--backlog">
                <div class="rag-stat">
                  <span class="lbl">排队 pending</span>
                  <strong :class="{ warn: ragBacklog.pending > 0 }">{{ ragBacklog.pending }}</strong>
                </div>
                <div class="rag-stat">
                  <span class="lbl">处理中</span>
                  <strong :class="{ warn: ragBacklog.processing > 0 }">{{ ragBacklog.processing }}</strong>
                </div>
                <div class="rag-stat">
                  <span class="lbl">失败 failed</span>
                  <strong :class="{ danger: ragBacklog.failed > 0 }">{{ ragBacklog.failed }}</strong>
                </div>
                <div class="rag-stat rag-stat--total">
                  <span class="lbl">积压合计</span>
                  <strong :class="{ danger: ragBacklog.backlogTotal > 0 }">{{ ragBacklog.backlogTotal }}</strong>
                </div>
              </div>
              <p v-if="ragBacklog.loaded && !ragBacklog.error" class="rag-backlog-foot muted">
                LightRAG 已成功 processed：{{ ragBacklog.processed }} 条
              </p>
            </div>
            <div class="rag-actions">
              <button
                type="button"
                class="btn primary"
                :disabled="syncRunning || purgeRunning"
                @click="purgeLightRagBacklog"
              >
                {{ purgeRunning ? "清理中…" : "开始清理 LightRAG 积压" }}
              </button>
            </div>
            <p v-if="purgeDoneSummary" class="rag-done muted">
              上次清理：候选 {{ purgeDoneSummary.candidate }}，成功 {{ purgeDoneSummary.success }}，失败
              {{ purgeDoneSummary.failure
              }}<template v-if="purgeDoneSummary.fullyCleared">（已全部清理）</template
              ><template v-else-if="purgeDoneSummary.queueCleared">（队列已清空）</template
              ><template v-else-if="purgeDoneSummary.candidate > 0">（未完成）</template>。
            </p>
            <div class="rag-log-wrap">
              <div class="rag-log-title">清理日志</div>
              <ul class="rag-log">
                <li v-for="(line, idx) in purgeLog" :key="'p-' + idx" class="rag-log-line">{{ line }}</li>
                <li v-if="!purgeLog.length" class="rag-log-line muted">点击「开始清理 LightRAG 积压」后在此展示结果。</li>
              </ul>
            </div>
          </div>
        </section>
        <div ref="listScrollRef" class="list-scroll-wrap">
        <ul class="post-grid">
          <li v-if="!filtered.length" class="empty">没有匹配结果</li>
          <li v-for="item in filtered" v-else :key="item.job_id" class="post-card">
            <router-link class="post-title" :to="`/jobs/${item.job_id}`">{{ item.job_title || "-" }}</router-link>
            <div class="post-meta">企业：{{ item.company_relation?.company_name || "-" }}</div>
            <div class="post-meta">行业：{{ item.district || "-" }} </div>
            <div class="post-meta">薪资：{{ item.salary_range_month || "-" }} </div>
            <div class="post-meta">地址：{{ item.city || "-" }} </div>
            <div class="links-row">
              <button
                type="button"
                class="fav-btn"
                :class="{ on: isFavorite(item.job_id) }"
                @click="toggleFavorite(item.job_id, $event)"
              >
                {{ isFavorite(item.job_id) ? "已收藏" : "收藏" }}
              </button>
              <router-link class="inline-link" :to="`/jobs/${item.job_id}`">查看岗位详情</router-link>
              <router-link class="inline-link" :to="`/companies/${item.company_relation?.credit_code || ''}`">查看企业详情</router-link>
            </div>
          </li>
        </ul>
        <div ref="sentinelRef" class="load-state">
          <span v-if="loadingMore">加载中...</span>
          <span v-else-if="!hasMore && jobs.length">已加载全部岗位</span>
        </div>
        </div>
        <p class="error">{{ error }}</p>
      </main>
    </div>
  </div>
</template>

<style scoped>
.hero { padding: 88px 20px 52px; text-align: center; background: radial-gradient(circle at top right, #eef2ff, transparent), radial-gradient(circle at top left, #f5f3ff, transparent); }
.hero h1 { font-size: clamp(2rem, 4.8vw, 3rem); margin-bottom: 12px; }
.hero p { color: var(--text-muted); }
.container { max-width: 1100px; margin: 0 auto; padding: 0 20px 80px; }
.toolbar { display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center; margin-bottom: 12px; }
.switch-line { display: flex; align-items: center; gap: 8px; margin: 0 0 12px; color: var(--text-muted); font-size: .9rem; }
.job-facet-panel {
  margin: 0 0 14px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: #fafbff;
}
.job-facet-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.job-facet-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.job-facet-collapsed-hint {
  margin: 0 0 8px;
  font-size: .84rem;
}
.job-facet-title {
  margin: 0;
  font-size: 1rem;
}
.job-facet-loading { font-size: .85rem; margin-bottom: 8px; }
.job-facet-clear { font-size: .85rem; }
.job-facet-group { margin-bottom: 12px; }
.job-facet-group:last-of-type { margin-bottom: 8px; }
.job-facet-label {
  font-size: .84rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.job-facet-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.job-facet-chips--scroll {
  max-height: 160px;
  overflow-y: auto;
  padding-right: 4px;
}
.facet-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #dbeafe;
  background: #fff;
  color: var(--text-main);
  font-size: .82rem;
  cursor: pointer;
  transition: border-color .15s, background .15s;
}
.facet-chip:hover { border-color: #93c5fd; background: #eff6ff; }
.facet-chip.active {
  border-color: var(--primary-color);
  background: #eef2ff;
  color: var(--primary-color);
  font-weight: 600;
}
.facet-chip-label { max-width: 12rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.facet-chip-count {
  font-size: .74rem;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.facet-chip.active .facet-chip-count { color: #4338ca; }
.job-facet-foot { margin: 0; font-size: .78rem; }
.sticky-toolbar { position: sticky; top: 10px; z-index: 5; background: #fff; padding: 8px; border-radius: 12px; border: 1px solid #eceff3; box-shadow: 0 8px 20px rgba(15,23,42,.06); }
.toolbar-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.me-link { font-size: .86rem; color: var(--primary-color); font-weight: 600; text-decoration: none; }
.search { width: 100%; padding: 11px 12px; border-radius: 10px; border: 1px solid #d1d5db; font-size: .95rem; }
.search:focus { outline: none; border-color: var(--primary-color); box-shadow: 0 0 0 4px rgba(99,102,241,.15); }
.count { font-size: .85rem; color: var(--text-muted); }
.rag-toolbar-foot { margin-bottom: 10px; }
.btn-rag-toggle {
  font-size: .86rem;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px dashed #c7d2fe;
  background: #f8fafc;
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
}
.btn-rag-toggle:hover { background: #eef2ff; }
.rag-sync-panel {
  margin-bottom: 16px;
  padding: 16px 18px;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #fafbff, #fff);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}
.rag-sync-title { font-size: 1.05rem; margin: 0 0 10px; }
.rag-sync-desc { margin: 0 0 14px; font-size: .88rem; }
.rag-tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  border-bottom: 1px solid #eceff3;
  padding-bottom: 0;
}
.rag-tab {
  position: relative;
  border: none;
  background: transparent;
  padding: 10px 14px;
  font-size: .9rem;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.rag-tab:hover {
  color: var(--text-main);
}
.rag-tab.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}
.rag-tab-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  font-size: .72rem;
  font-weight: 700;
  line-height: 18px;
  text-align: center;
}
.rag-tab-badge--live {
  background: #dbeafe;
  color: #1d4ed8;
  min-width: auto;
  padding: 0 8px;
}
.rag-tab-panel {
  animation: rag-tab-in .18s ease;
}
@keyframes rag-tab-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.rag-backlog-block--tab {
  margin-top: 0;
}
.muted { color: var(--text-muted); }
.rag-stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}
.rag-eta-block {
  margin: 0 0 14px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #dbeafe;
  background: linear-gradient(180deg, #f8fbff, #fff);
}
.rag-eta-main {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 4px;
}
.rag-eta-time {
  font-size: 1.45rem;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: #1e40af;
}
.rag-eta-hint { margin: 0; font-size: .82rem; }
.rag-stats-row--backlog {
  grid-template-columns: repeat(4, 1fr);
}
.rag-backlog-block {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px dashed #dbeafe;
  border-radius: 12px;
  background: #f8fbff;
}
.rag-backlog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.rag-backlog-title {
  margin: 0;
  font-size: .92rem;
  font-weight: 600;
}
.rag-backlog-desc,
.rag-backlog-foot,
.rag-backlog-error {
  margin: 0 0 10px;
  font-size: .82rem;
}
.rag-backlog-foot {
  margin-bottom: 0;
}
.btn-linkish {
  border: none;
  background: transparent;
  color: var(--primary-color);
  font-size: .82rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.btn-linkish:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.rag-stat--total {
  border-color: #bfdbfe;
  background: #eff6ff;
}
.rag-stat {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rag-stat .lbl { font-size: .78rem; color: var(--text-muted); }
.rag-stat strong { font-size: 1.25rem; }
.rag-stat strong.ok { color: #059669; }
.rag-stat strong.warn { color: #b45309; }
.rag-stat strong.danger { color: #dc2626; }
.rag-progress-wrap { margin-bottom: 10px; }
.rag-progress-track {
  height: 10px;
  border-radius: 999px;
  background: #e5e7eb;
  overflow: hidden;
}
.rag-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  transition: width 0.35s ease;
}
.rag-progress-track--busy {
  background: linear-gradient(90deg, #e5e7eb, #eef2ff, #e5e7eb);
  background-size: 200% 100%;
  animation: rag-progress-track-shimmer 1.4s ease-in-out infinite;
}
.rag-progress-fill--pulse {
  width: 42% !important;
  max-width: 42%;
  animation: rag-progress-fill-slide 1.1s ease-in-out infinite;
  opacity: 0.95;
}
@keyframes rag-progress-track-shimmer {
  0% { background-position: 0% 0%; }
  100% { background-position: 200% 0%; }
}
@keyframes rag-progress-fill-slide {
  0% { transform: translateX(-30%); }
  100% { transform: translateX(190%); }
}
.rag-progress-label { display: block; margin-top: 6px; font-size: .8rem; color: var(--text-muted); }
.rag-sync-job-name {
  margin: 0 0 8px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rag-progress-track--minute-zones {
  background: linear-gradient(
    90deg,
    #ecfdf5 0%,
    #ecfdf5 33.333%,
    #bbf7d0 33.333%,
    #bbf7d0 66.666%,
    #86efac 66.666%,
    #86efac 100%
  );
}
.rag-batch-fill {
  transition: width 0.55s linear;
  background: linear-gradient(90deg, #34d399, #059669);
}
.rag-batch-hint { font-size: .82rem; margin-bottom: 10px; }
.rag-accelerate-line { margin: 0 0 12px; }
.rag-actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 10px; }
.rag-paused-hint { font-size: .84rem; margin: 0 0 8px; }
.btn {
  padding: 9px 16px;
  border-radius: 10px;
  font-size: .9rem;
  font-weight: 600;
  border: 1px solid transparent;
  cursor: pointer;
}
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.btn.primary {
  background: var(--primary-color, #6366f1);
  color: #fff;
}
.btn.secondary {
  background: #fff;
  border-color: #d1d5db;
  color: #334155;
}
.rag-done { font-size: .86rem; margin: 0 0 8px; }
.rag-log-wrap {
  border: 1px solid #eceff3;
  border-radius: 12px;
  background: #0f172a;
  color: #e2e8f0;
  max-height: 220px;
  overflow: auto;
  margin-bottom: 10px;
}
.rag-log-wrap:last-child {
  margin-bottom: 0;
}
.rag-log-title {
  padding: 8px 12px;
  font-size: .78rem;
  color: #94a3b8;
  border-bottom: 1px solid #1e293b;
}
.rag-log { list-style: none; margin: 0; padding: 8px 12px 12px; font-family: ui-monospace, monospace; font-size: .78rem; line-height: 1.45; }
.rag-log-line { margin-bottom: 4px; word-break: break-all; }
.post-grid { list-style: none; display: flex; flex-direction: column; gap: 14px; padding: 0; }
.list-scroll-wrap { max-height: calc(100vh - 280px); overflow: auto; padding-right: 4px; }
.post-card { border: 1px solid #eceff3; border-radius: 14px; padding: 16px; background: linear-gradient(180deg, #fff, #fcfcff); transition: all .3s cubic-bezier(0.4, 0, 0.2, 1); }
.post-card:hover { transform: translateY(-3px); box-shadow: 0 16px 26px rgba(15,23,42,.08); }
.post-title { font-size: 1.1rem; font-weight: 600; text-decoration: none; color: var(--text-main); }
.post-meta { font-size: .86rem; color: var(--text-muted); margin-top: 6px; }
.links-row { margin-top: 10px; display: flex; gap: 12px; }
.inline-link { font-size: .86rem; text-decoration: none; color: var(--primary-color); font-weight: 600; }
.empty { text-align: center; padding: 28px 8px; color: var(--text-muted); }
.load-state { text-align: center; color: var(--text-muted); font-size: .86rem; padding: 6px 0 4px; min-height: 26px; }
.error { color: var(--danger); margin-top: 8px; min-height: 20px; font-weight: 600; font-size: .9rem; }
@media (max-width: 900px) { .list-scroll-wrap { max-height: 62vh; } .toolbar-meta { align-items: flex-start; } }
</style>
