<script setup>
/**
 * 岗位推荐交互面板（学生主页 / 会话聊天共用）。
 * 左侧岗位列表 + 右侧推荐理由 + 点击打开 FloatingFrame 岗位详情。
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import FloatingFramePanel from "./FloatingFramePanel.vue";
import JobMatchReasonBlocks from "./JobMatchReasonBlocks.vue";
import { resolveJobMatchReasonDisplay } from "../utils/jobMatchReason";

const props = defineProps({
  jobs: { type: Array, default: () => [] },
  recommendation: { type: Object, default: null },
  rag: { type: Object, default: null },
  cache: { type: Object, default: null },
  /** 聊天气泡内紧凑布局 */
  compact: { type: Boolean, default: false }
});

const selectedJobId = ref(null);
const hoverJobId = ref(null);

const jobDetailFrameOpen = ref(false);
const jobDetailFrameFullscreen = ref(false);
const jobDetailIframeSrc = ref("");
const jobDetailFrameTitle = ref("");

const cacheHitActive = computed(() => Boolean(props.cache?.hit));

const cacheHitTitle = computed(() => {
  const c = props.cache;
  if (!c?.hit) return "";
  if (c.type === "exact") return "缓存命中 · 精确匹配";
  if (c.type === "semantic") return "缓存命中 · 语义相似";
  return "缓存命中";
});

const cacheHitDetail = computed(() => {
  const c = props.cache;
  if (!c?.hit) return "";
  const parts = [];
  if (c.type === "semantic" && c.similarity != null) {
    const pct = (Number(c.similarity) * 100).toFixed(1);
    const th = c.threshold != null ? (Number(c.threshold) * 100).toFixed(0) : null;
    parts.push(`相似度 ${pct}%${th != null ? `（阈值 ≥ ${th}%）` : ""}`);
  } else if (c.type === "exact") {
    parts.push("改写检索句与历史请求完全一致");
  }
  if (c.cached_rag_q) parts.push(`历史检索句：${c.cached_rag_q}`);
  return parts.join(" · ");
});

function reasonMetaForJob(job) {
  if (!job?.job_id) {
    return { reason: "", sections: [], charCount: 0, score: null };
  }
  const rec = props.recommendation?.recommended_jobs || [];
  const hit = rec.find((x) => x.job_id === job.job_id);
  return resolveJobMatchReasonDisplay(hit, job);
}

const selectedReasonMeta = computed(() => {
  if (!previewJob.value) {
    return { reason: "", sections: [], charCount: 0, score: null };
  }
  return reasonMetaForJob(previewJob.value);
});

const selectedJob = computed(() => {
  const id = selectedJobId.value;
  if (!id) return null;
  return (props.jobs || []).find((j) => j.job_id === id) || null;
});

const previewJob = computed(() => {
  const h = hoverJobId.value;
  if (h) return (props.jobs || []).find((j) => j.job_id === h) || null;
  return selectedJob.value;
});

const reasonPanelTitle = computed(() => {
  if (!previewJob.value) return "";
  return previewJob.value.job_title || previewJob.value.job_name || "岗位";
});

const noJobReasonBlocks = computed(() => {
  const rec = props.recommendation;
  const detail = rec?.no_match_detail;
  if (detail?.causes?.length) {
    return {
      headline: detail.title || "暂无推荐",
      causes: detail.causes,
      suggestions: detail.suggestions || []
    };
  }
  const parts = [];
  if (props.rag?.hint) parts.push(String(props.rag.hint));
  if (props.rag?.detail) parts.push(String(props.rag.detail));
  if (rec?.notes?.length) parts.push(rec.notes.join(" "));
  if (!parts.length) parts.push("当前条件下未返回可展示的推荐岗位，请调整诉求后重试。");
  return { headline: "暂无推荐", causes: parts, suggestions: [] };
});

const ragPreview = computed(() => {
  const r = props.rag;
  if (!r?.enabled) return "";
  const text = String(r.retrieval_context || r.answer_preview || "").trim();
  if (!text) return "";
  return text.length > 800 ? `${text.slice(0, 800)}…` : text;
});

function closeJobDetailFrame() {
  jobDetailFrameOpen.value = false;
  jobDetailFrameFullscreen.value = false;
  jobDetailIframeSrc.value = "";
  jobDetailFrameTitle.value = "";
}

function jobDetailEmbedUrl(path) {
  const u = new URL(path, window.location.origin);
  u.searchParams.set("_embed", "1");
  return u.pathname + u.search + u.hash;
}

function openJobDetailFrame(job) {
  if (!job?.job_id) return;
  const id = encodeURIComponent(String(job.job_id).trim());
  jobDetailFrameTitle.value = job.job_title || job.job_name || job.job_id || "岗位详情";
  jobDetailIframeSrc.value = jobDetailEmbedUrl(`/jobs/${id}`);
  jobDetailFrameOpen.value = true;
  jobDetailFrameFullscreen.value = false;
}

function toggleJobDetailFullscreen() {
  jobDetailFrameFullscreen.value = !jobDetailFrameFullscreen.value;
}

function openJobDetailFullWindow() {
  if (!jobDetailIframeSrc.value) return;
  const u = new URL(jobDetailIframeSrc.value, window.location.origin);
  u.searchParams.delete("_embed");
  window.open(u.pathname + u.search + u.hash, "_blank", "noopener,noreferrer");
}

function selectJobForReason(job) {
  if (!job?.job_id) return;
  selectedJobId.value = job.job_id;
}

function onJobCardActivate(job) {
  if (!job?.job_id) return;
  selectJobForReason(job);
  openJobDetailFrame(job);
}

function onJobDetailDocKey(ev) {
  if (ev.key === "Escape" && jobDetailFrameOpen.value) closeJobDetailFrame();
}

onMounted(() => {
  document.addEventListener("keydown", onJobDetailDocKey);
  const list = props.jobs || [];
  if (list.length === 1 && list[0]?.job_id) {
    selectedJobId.value = list[0].job_id;
  }
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onJobDetailDocKey);
});
</script>

<template>
  <div class="job-rec-root" :class="{ 'job-rec-root--compact': compact }">
    <div v-if="cacheHitActive" class="cache-hit-banner" role="status">
      <span class="cache-hit-badge">{{ cacheHitTitle }}</span>
      <span v-if="cacheHitDetail" class="cache-hit-detail">{{ cacheHitDetail }}</span>
      <span class="cache-hit-hint">结果来自历史推荐，未重新检索知识库与大模型分析</span>
    </div>

    <div class="result-grid">
      <div class="result-col">
        <h3 class="section-title">推荐岗位</h3>
        <ul class="mini-list">
          <li v-if="!jobs.length" class="empty-tip">暂无数据</li>
          <template v-else>
          <li
            v-for="item in jobs"
            :key="item.job_id"
            class="job-pick"
            :class="{
              'job-pick--active': selectedJobId === item.job_id,
              'job-pick--hover': hoverJobId === item.job_id
            }"
            role="button"
            tabindex="0"
            @click="onJobCardActivate(item)"
            @keydown.enter.prevent="onJobCardActivate(item)"
            @mouseenter="hoverJobId = item.job_id"
            @mouseleave="hoverJobId = null"
          >
            <div class="job-pick-head">
              <span class="job-pick-title">{{ item.job_title || item.job_name || "-" }}</span>
            </div>
            <p class="job-pick-meta job-pick-ids">
              <span class="mono">ID {{ item.job_id || "-" }}</span>
              <span v-if="item.score != null && item.score !== ''" class="job-score">匹配分 {{ item.score }}</span>
            </p>
            <p class="job-pick-meta">
              {{ item.city || "-" }} {{ item.district || "" }} ｜
              {{ item.company_name || item.company_relation?.company_name || "-" }}
            </p>
          </li>
          </template>
        </ul>
      </div>
      <div class="result-col reason-panel">
        <h3 class="section-title">推荐理由</h3>
        <template v-if="!jobs.length">
          <p class="reason-headline">{{ noJobReasonBlocks.headline }}</p>
          <p class="muted reason-sub">未推荐岗位的可能原因：</p>
          <ul class="reason-list">
            <li v-for="(c, idx) in noJobReasonBlocks.causes" :key="'c-' + idx">{{ c }}</li>
          </ul>
          <template v-if="noJobReasonBlocks.suggestions?.length">
            <p class="muted reason-sub">建议：</p>
            <ul class="reason-list">
              <li v-for="(s, idx) in noJobReasonBlocks.suggestions" :key="'s-' + idx">{{ s }}</li>
            </ul>
          </template>
        </template>
        <template v-else>
          <p v-if="!previewJob" class="muted reason-placeholder">
            悬停卡片查看推荐理由；点击卡片打开岗位详情（可拖动、缩放、新标签页）。
          </p>
          <template v-else>
            <p class="reason-job-title">{{ reasonPanelTitle }}</p>
            <JobMatchReasonBlocks
              v-if="selectedReasonMeta.reason || selectedReasonMeta.sections?.length"
              :reason="selectedReasonMeta.reason"
              :sections="selectedReasonMeta.sections"
              :score="selectedReasonMeta.score"
              :char-count="selectedReasonMeta.charCount"
            />
            <p v-else class="muted reason-placeholder">该岗位暂无单独生成的推荐理由。</p>
          </template>
        </template>
      </div>
    </div>

    <details v-if="ragPreview" class="rag-details">
      <summary>查看本次 RAG 检索摘要</summary>
      <pre class="rag-pre">{{ ragPreview }}</pre>
    </details>
  </div>

  <Teleport to="body">
    <FloatingFramePanel
      :open="jobDetailFrameOpen"
      :fullscreen="jobDetailFrameFullscreen"
      :title="jobDetailFrameTitle"
      :z-index="13100"
      @backdrop-click="closeJobDetailFrame"
    >
      <template #actions>
        <button type="button" @click="toggleJobDetailFullscreen">
          {{ jobDetailFrameFullscreen ? "缩小" : "放大" }}
        </button>
        <button type="button" @click="openJobDetailFullWindow">完整页面</button>
        <button type="button" class="danger" @click="closeJobDetailFrame">关闭</button>
      </template>
      <iframe v-if="jobDetailIframeSrc" :title="jobDetailFrameTitle" :src="jobDetailIframeSrc" />
    </FloatingFramePanel>
  </Teleport>
</template>

<style scoped>
.job-rec-root {
  margin-top: 4px;
}
.job-rec-root--compact {
  min-width: 0;
}
.job-rec-root--compact .result-grid {
  grid-template-columns: 1fr;
}
@media (min-width: 720px) {
  .job-rec-root--compact .result-grid {
    grid-template-columns: 1fr 1fr;
  }
}
.job-rec-root--compact .mini-list {
  max-height: none;
}
.job-rec-root--compact .reason-panel {
  max-height: none;
}
.section-title {
  font-size: 0.92rem;
  margin: 0 0 8px;
  font-weight: 700;
  color: #1f2937;
}
.result-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: 1fr 1fr;
}
.result-col {
  min-width: 0;
}
.empty-tip {
  color: #6b7280;
  font-size: 0.88rem;
  padding: 10px;
  border: 1px dashed #d1d5db;
  border-radius: 10px;
}
.mini-list {
  list-style: none;
  display: grid;
  gap: 8px;
  padding: 0;
  margin: 0;
}
.mini-list li {
  border: 1px solid #eceff3;
  border-radius: 10px;
  padding: 10px;
}
.job-pick {
  cursor: pointer;
  user-select: none;
  transition: border-color 0.15s, background 0.15s;
}
.job-pick:focus {
  outline: 2px solid var(--primary-color, #6366f1);
  outline-offset: 2px;
}
.job-pick--active {
  border-color: #a5b4fc !important;
  background: #eef2ff !important;
}
.job-pick--hover {
  border-color: #c7d2fe !important;
  background: #f8fafc !important;
}
.job-pick-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.job-pick-title {
  font-weight: 600;
  color: #111827;
  font-size: 0.92rem;
  flex: 1;
  min-width: 0;
}
.job-pick-meta {
  color: #6b7280;
  font-size: 0.8rem;
  margin: 6px 0 0;
}
.job-pick-ids {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  align-items: center;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.72rem;
  color: #64748b;
  word-break: break-all;
}
.job-score {
  font-weight: 600;
  color: #4338ca;
  font-size: 0.78rem;
}
.reason-panel {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px;
  background: #fafafa;
  min-height: 100px;
  max-height: min(72vh, 640px);
  overflow: auto;
}
.reason-headline,
.reason-job-title {
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 8px;
  font-size: 0.95rem;
}
.reason-sub {
  margin: 10px 0 6px;
  font-size: 0.82rem;
  color: #6b7280;
}
.reason-list {
  margin: 0;
  padding-left: 1.1rem;
  color: #374151;
  font-size: 0.88rem;
  line-height: 1.55;
}
.reason-list li {
  margin-bottom: 6px;
}
.reason-placeholder {
  margin: 0;
  font-size: 0.88rem;
  color: #6b7280;
}
.muted {
  color: #6b7280;
}
.cache-hit-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin: 0 0 10px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid #a7f3d0;
  background: linear-gradient(180deg, #ecfdf5, #f0fdf4);
  font-size: 0.82rem;
}
.cache-hit-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: #059669;
  color: #fff;
  font-weight: 700;
  font-size: 0.76rem;
}
.cache-hit-detail {
  color: #047857;
  font-weight: 600;
}
.cache-hit-hint {
  color: #6b7280;
  font-size: 0.78rem;
}
.rag-details {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 8px 10px;
  background: #fafafa;
}
.rag-details > summary {
  cursor: pointer;
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--primary-color, #6366f1);
}
.rag-pre {
  margin: 8px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.78rem;
  line-height: 1.45;
  color: #374151;
  max-height: 180px;
  overflow: auto;
}
@media (max-width: 640px) {
  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
