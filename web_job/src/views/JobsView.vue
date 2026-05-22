<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { apiGet, apiPost, apiPostSse, getStudentId } from "../api/client";
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
      credit_code: item.companyId
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
    const data = await apiGet(`/api/jobs/paged?page=${page.value}&pageSize=${pageSize}${kw}${sync}`);
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
  void loadNextPage();
}

onMounted(async () => {
  await loadFavorites();
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
const ragLive = ref({ total: 0, synced: 0, unsynced: 0, batchIndex: 0, batchTotal: 0 });
const syncRunning = ref(false);
const syncLog = ref([]);
const ragAbort = ref(null);
const syncDoneSummary = ref(null);
const ragPaused = ref(false);

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
}

async function loadRagStats() {
  try {
    const kw = searchInput.value.trim();
    const qs = kw ? `?keyword=${encodeURIComponent(kw)}` : "";
    const s = await apiGet(`/api/jobs/rag-sync/stats${qs}`);
    ragStats.value = {
      total: Number(s?.total ?? 0),
      synced: Number(s?.synced ?? 0),
      unsynced: Number(s?.unsynced ?? 0),
      keyword: String(s?.keyword ?? kw ?? "")
    };
    ragLive.value = {
      total: ragStats.value.total,
      synced: ragStats.value.synced,
      unsynced: ragStats.value.unsynced,
      batchIndex: 0,
      batchTotal: 0
    };
  } catch {
    ragStats.value = { total: 0, synced: 0, unsynced: 0, keyword: "" };
    ragLive.value = { total: 0, synced: 0, unsynced: 0, batchIndex: 0, batchTotal: 0 };
  }
}

let ragStatsDebounceTimer;
watch(syncedOnly, () => {
  resetPagedList();
  void loadNextPage();
});

watch(searchInput, () => {
  if (!ragPanelOpen.value) return;
  window.clearTimeout(ragStatsDebounceTimer);
  ragStatsDebounceTimer = window.setTimeout(() => {
    void loadRagStats();
  }, 400);
});

function toggleRagPanel() {
  ragPanelOpen.value = !ragPanelOpen.value;
  if (ragPanelOpen.value) {
    loadRagStats();
  }
}

function pushLog(line) {
  const next = [...syncLog.value, line];
  if (next.length > 40) next.splice(0, next.length - 40);
  syncLog.value = next;
}

async function startRagSync() {
  if (syncRunning.value) return;
  syncDoneSummary.value = null;
  syncLog.value = [];
  ragPaused.value = false;
  await loadRagStats();
  if (Number(ragStats.value.unsynced || 0) <= 0) {
    pushLog(
      searchInput.value.trim()
        ? `当前范围内没有待同步岗位（关键词「${searchInput.value.trim()}」下 synRag≠1 的条数为 0）。`
        : "当前没有待同步岗位（synRag≠1）。"
    );
    return;
  }
  syncRunning.value = true;
  const ac = new AbortController();
  ragAbort.value = ac;
  const ragBody = { keyword: searchInput.value.trim() };
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
              }。`
            );
          } else if (name === "error") {
            pushLog(`无法开始：${data.detail || JSON.stringify(data)}`);
          } else if (name === "progress") {
            applyStatsToLive(data);
            const it = data.item || {};
            const ok = it.success === true;
            const skip = it.skipped === true;
            pushLog(
              `[${data.batchIndex}/${data.batchTotal}] ${it.jobId} — ${
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
    await loadRagStats();
  }
}

async function pauseRagSync() {
  if (!syncRunning.value || ragPaused.value) return;
  try {
    await apiPost("/api/jobs/sync-rag/pause", {});
    ragPaused.value = true;
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
    pushLog("已继续同步。");
  } catch (e) {
    pushLog(`继续失败：${e?.message || e}`);
  }
}

async function cancelRagSync() {
  await ragFireCancel();
  ragAbort.value?.abort();
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
            placeholder="岗位名 / 城市 / 企业名 — 输入即本地筛选，回车查库"
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
        <div class="rag-toolbar-foot">
          <button type="button" class="btn-rag-toggle" @click="toggleRagPanel">
            {{ ragPanelOpen ? "收起「知识库同步」" : "展开「知识库同步」" }}
          </button>
        </div>
        <section v-show="ragPanelOpen" class="rag-sync-panel" aria-label="知识库同步">
          <div class="rag-sync-head">
            <h2 class="rag-sync-title">岗位写入 RAG</h2>
            <p class="rag-sync-desc muted">
              <template v-if="searchInput.trim()">
                统计与<strong>同步范围</strong>与上方输入框一致（关键词「<strong>{{ searchInput.trim() }}</strong>」：岗位名 / 企业名 / 地址 / 地区模糊匹配）。仅处理该范围内尚未写入 RAG 的岗位。
              </template>
              <template v-else> 统计与同步范围为<strong>全库</strong>未入库岗位；输入关键词后数字会随输入防抖更新，点「开始同步」仅同步该范围内未写入 RAG 的条目。 </template>
            </p>
          </div>
          <div class="rag-stats-row">
            <div class="rag-stat"><span class="lbl">总岗位</span><strong>{{ ragLive.total }}</strong></div>
            <div class="rag-stat"><span class="lbl">已同步</span><strong class="ok">{{ ragLive.synced }}</strong></div>
            <div class="rag-stat"><span class="lbl">未同步</span><strong class="warn">{{ ragLive.unsynced }}</strong></div>
          </div>
          <div class="rag-progress-wrap" role="progressbar" :aria-valuenow="progressIndeterminate ? undefined : progressPct" aria-valuemin="0" aria-valuemax="100" :aria-label="progressLabel">
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
          </div>
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
            上次结果：成功 {{ syncDoneSummary.succeeded }}，失败 {{ syncDoneSummary.failed
            }}<template v-if="syncDoneSummary.skipped != null">，跳过 {{ syncDoneSummary.skipped }}</template
            ><template v-if="syncDoneSummary.cancelled">（已取消）</template>。
          </p>
          <div class="rag-log-wrap">
            <div class="rag-log-title">实时日志</div>
            <ul class="rag-log">
              <li v-for="(line, idx) in syncLog" :key="idx" class="rag-log-line">{{ line }}</li>
              <li v-if="!syncLog.length" class="rag-log-line muted">暂无日志，点击「开始同步」后在此展示 SSE 推送内容。</li>
            </ul>
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
.rag-sync-title { font-size: 1.05rem; margin: 0 0 6px; }
.rag-sync-desc { margin: 0 0 14px; font-size: .88rem; }
.muted { color: var(--text-muted); }
.rag-stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 12px;
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
.rag-batch-hint { font-size: .82rem; margin-bottom: 10px; }
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
