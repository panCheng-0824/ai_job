<script setup>
/**
 * 首页「智能匹配职位」：岗位网格；推荐理由可由父级抽屉展示。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import JobMatchReasonBlocks from "../JobMatchReasonBlocks.vue";
import { formatJobMatchElapsed } from "../../composables/useJobMatchWaitTimer";
import { useScrollWheelContain } from "../../composables/useScrollWheelContain";
import {
  findJobById,
  normalizeJobId,
  useJobRecommendDisplay
} from "../../composables/useJobRecommendDisplay";
import { dedupeJobs } from "../../utils/jobDedupe";
import JobMatchWaitingPanel from "../jobs/JobMatchWaitingPanel.vue";
import HomeMatchedJobCard from "./HomeMatchedJobCard.vue";
import HomeMatchedJobPlaceholder from "./HomeMatchedJobPlaceholder.vue";

const MIN_GRID_SLOTS = 9;

const props = defineProps({
  jobs: { type: Array, default: () => [] },
  recommendation: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  /** 正在加载服务端历史记录 */
  historyLoading: { type: Boolean, default: false },
  searched: { type: Boolean, default: false },
  /** 是否存在已保存的匹配历史 */
  hasHistory: { type: Boolean, default: false },
  /** 是否展示右侧推荐理由栏 */
  showReasonRail: { type: Boolean, default: true },
  minScore: { type: Number, default: 85 },
  /** 匹配进行中已等待毫秒 */
  matchElapsedMs: { type: Number, default: 0 },
  /** 最近一次匹配总耗时（毫秒），完成后展示 */
  lastMatchDurationMs: { type: Number, default: null }
});

const emit = defineEmits(["view-detail", "apply", "resume", "interview", "refresh", "view-more"]);

const regionFilter = defineModel("regionFilter", { type: String, default: "" });
const salaryFilter = defineModel("salaryFilter", { type: String, default: "" });
const sortFilter = defineModel("sortFilter", { type: String, default: "score" });

/** 点击固定的岗位 id；未固定时悬停预览，移出区域后回到首条 */
const pinnedJobId = ref(null);
const jobGridScrollRef = ref(null);
const jobsPaneCanScroll = ref(false);
let jobsPaneObserver = null;

const regions = computed(() => {
  const set = new Set();
  for (const j of props.jobs) {
    if (j.city) set.add(j.city);
  }
  return ["", ...set];
});

const displayJobs = computed(() => {
  let list = dedupeJobs([...(props.jobs || [])]);
  if (regionFilter.value) {
    list = list.filter((j) => j.city === regionFilter.value);
  }
  if (salaryFilter.value === "high") {
    list = list.filter((j) => String(j.salary_range_month || "").includes("K"));
  }
  if (sortFilter.value === "score") {
    list.sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  }
  return list;
});

/** 至少展示 9 个网格位，不足时用空白占位卡补齐 */
const gridSlots = computed(() => {
  const jobs = displayJobs.value;
  const slots = jobs.map((job) => ({
    type: "job",
    job,
    key: `${normalizeJobId(job.job_id || job.id)}-${job.job_title || ""}`
  }));
  const pad = Math.max(0, MIN_GRID_SLOTS - jobs.length);
  for (let i = 0; i < pad; i += 1) {
    slots.push({ type: "placeholder", key: `placeholder-${i}` });
  }
  return slots;
});

const scrollHint = computed(() => {
  if (!jobsPaneCanScroll.value) return "";
  const n = displayJobs.value.length;
  return `共 ${n} 个岗位 · 在此区域内滑动查看更多`;
});

function updateJobsPaneScrollState() {
  const el = jobGridScrollRef.value;
  if (!el) {
    jobsPaneCanScroll.value = false;
    return;
  }
  jobsPaneCanScroll.value = el.scrollHeight > el.clientHeight + 2;
}

function bindJobsPaneObserver() {
  jobsPaneObserver?.disconnect();
  jobsPaneObserver = null;
  const el = jobGridScrollRef.value;
  if (!el || typeof ResizeObserver === "undefined") return;
  jobsPaneObserver = new ResizeObserver(() => updateJobsPaneScrollState());
  jobsPaneObserver.observe(el);
  if (el.firstElementChild) jobsPaneObserver.observe(el.firstElementChild);
}

const {
  displayJobId,
  hoverJobId,
  previewJob,
  selectedReasonMeta,
  reasonReady,
  pinJobForReason,
  onJobCardHover,
  onJobCardLeave,
  syncDisplayJobFromList,
  sameJobId
} = useJobRecommendDisplay(
  () => displayJobs.value,
  () => props.recommendation,
  { autoSync: false }
);

watch(
  displayJobs,
  (list) => {
    pinnedJobId.value = null;
    syncDisplayJobFromList(list);
  },
  { deep: true }
);

const reasonPanelTitle = computed(() => {
  if (!previewJob.value) return "选择岗位查看理由";
  return previewJob.value.job_title || previewJob.value.job_name || "岗位";
});

const reasonCompany = computed(() => {
  const j = previewJob.value;
  if (!j) return "";
  return j.company_name || j.company_relation?.company_name || "";
});

const showMatchBody = computed(() => displayJobs.value.length > 0 && !props.loading && props.searched);

watch(
  () => [showMatchBody.value, gridSlots.value.length, displayJobs.value.length],
  () => nextTick(() => {
    updateJobsPaneScrollState();
    bindJobsPaneObserver();
  })
);

onMounted(() => {
  nextTick(() => {
    updateJobsPaneScrollState();
    bindJobsPaneObserver();
  });
});

onBeforeUnmount(() => {
  jobsPaneObserver?.disconnect();
  jobsPaneObserver = null;
});

useScrollWheelContain(jobGridScrollRef, () => showMatchBody.value);

const idleHint = computed(() => {
  if (props.historyLoading) return "正在加载匹配记录…";
  if (!props.hasHistory) return "暂无匹配记录，点击下方开始第一次智能匹配";
  return "正在准备个性化推荐…";
});

const showFirstMatchAction = computed(
  () => !props.searched && !props.loading && !props.historyLoading && !props.hasHistory
);

const interactionHint = computed(() => {
  if (!props.showReasonRail) {
    if (pinnedJobId.value) return "已选择岗位，点击右侧边框按钮展开推荐理由";
    return "悬停或点击卡片选择岗位，再展开右侧推荐理由";
  }
  if (pinnedJobId.value) return "已固定当前岗位，点击其他卡片可切换";
  return "悬停预览 · 点击卡片固定推荐理由";
});

const lastDurationLabel = computed(() => {
  if (props.lastMatchDurationMs == null) return "";
  return formatJobMatchElapsed(props.lastMatchDurationMs);
});

function restorePinnedOrFirst() {
  if (pinnedJobId.value) {
    const pinned = findJobById(displayJobs.value, pinnedJobId.value);
    if (pinned) {
      pinJobForReason(pinned);
      return;
    }
    pinnedJobId.value = null;
  }
  syncDisplayJobFromList(displayJobs.value);
}

function onCardHover(job) {
  if (pinnedJobId.value) {
    onJobCardHover(job, { previewOnly: true });
    return;
  }
  onJobCardHover(job);
}

function onCardSelect(job) {
  const id = normalizeJobId(job?.job_id);
  if (!id) return;
  if (pinnedJobId.value === id) {
    pinnedJobId.value = null;
    onJobCardHover(job);
    return;
  }
  pinnedJobId.value = id;
  pinJobForReason(job);
}

function onMatchBodyLeave() {
  onJobCardLeave();
  if (pinnedJobId.value) {
    restorePinnedOrFirst();
    return;
  }
  syncDisplayJobFromList(displayJobs.value);
}

defineExpose({
  previewJob,
  selectedReasonMeta,
  reasonReady,
  reasonPanelTitle,
  reasonCompany,
  interactionHint
});
</script>

<template>
  <section class="match-section card-panel">
    <header class="section-head">
      <div class="section-title-wrap">
        <h2>智能匹配职位</h2>
        <span class="score-badge">匹配度≥{{ minScore }}%</span>
      </div>
      <div class="filters">
        <select v-model="regionFilter" class="filter-select" aria-label="地区筛选">
          <option value="">全部地区</option>
          <option v-for="r in regions.filter(Boolean)" :key="r" :value="r">{{ r }}</option>
        </select>
        <select v-model="salaryFilter" class="filter-select" aria-label="薪资筛选">
          <option value="">全部薪资</option>
          <option value="high">10K 以上</option>
        </select>
        <select v-model="sortFilter" class="filter-select" aria-label="排序">
          <option value="score">按匹配度</option>
        </select>
      </div>
    </header>

    <JobMatchWaitingPanel
      v-if="loading"
      :elapsed-ms="matchElapsedMs"
      show-reason-rail
      title="正在智能匹配岗位"
    />

    <div v-if="loading" class="skeleton-grid">
      <div v-for="i in 3" :key="i" class="skeleton-card"></div>
    </div>

    <div v-else-if="!searched" class="empty-box">
      <p>{{ idleHint }}</p>
      <button v-if="showFirstMatchAction" type="button" class="empty-match-action" @click="$emit('refresh')">
        开始匹配
      </button>
    </div>

    <div v-else-if="!displayJobs.length" class="empty-match">
      <p class="empty-match-title">暂未找到匹配的岗位</p>
      <p class="empty-match-desc">可以试试调整匹配条件、扩大搜索范围，或修改五维权重配置</p>
      <button class="empty-match-action" @click="$emit('refresh')">重新匹配</button>
    </div>

    <div
      v-else-if="showMatchBody"
      class="match-body"
      :class="{ 'match-body--single': !showReasonRail }"
      @mouseleave="onMatchBodyLeave"
    >
      <div class="job-grid-wrap">
        <div
          ref="jobGridScrollRef"
          class="job-grid-scroll job-grid-scroll--pane"
          tabindex="0"
          :aria-label="jobsPaneCanScroll ? '推荐岗位列表，可滚动查看更多' : '推荐岗位列表'"
        >
          <div class="job-grid">
            <template v-for="slot in gridSlots" :key="slot.key">
              <HomeMatchedJobCard
                v-if="slot.type === 'job'"
                :job="slot.job"
                :recommendation="recommendation"
                :active="sameJobId(displayJobId, slot.job.job_id)"
                :hover="sameJobId(hoverJobId, slot.job.job_id)"
                :pinned="sameJobId(pinnedJobId, slot.job.job_id)"
                @hover="onCardHover"
                @select="onCardSelect"
                @view-detail="emit('view-detail', $event)"
                @apply="emit('apply', $event)"
                @resume="emit('resume', $event)"
                @interview="emit('interview', $event)"
              />
              <HomeMatchedJobPlaceholder v-else />
            </template>
          </div>
        </div>
        <p v-if="scrollHint" class="scroll-hint">{{ scrollHint }}</p>
      </div>

      <aside v-if="showReasonRail" class="reason-rail" aria-live="polite" aria-label="推荐理由">
        <header class="reason-rail-head">
          <div class="reason-rail-title-wrap">
            <p class="reason-rail-label">推荐理由</p>
            <h3 class="reason-rail-title">{{ reasonPanelTitle }}</h3>
            <p v-if="reasonCompany" class="reason-rail-meta">{{ reasonCompany }}</p>
          </div>
          <button
            v-if="previewJob"
            type="button"
            class="reason-detail-btn"
            @click="emit('view-detail', previewJob)"
          >
            详情
          </button>
        </header>

        <div :key="displayJobId || 'empty'" class="reason-rail-body">
          <JobMatchReasonBlocks
            v-if="previewJob && reasonReady"
            :reason="selectedReasonMeta.reason"
            :sections="selectedReasonMeta.sections"
            :score="selectedReasonMeta.score"
            :char-count="selectedReasonMeta.charCount"
          />
          <div v-else-if="previewJob" class="reason-empty">
            该岗位暂无结构化推荐理由，可查看岗位详情了解更多。
          </div>
          <div v-else class="reason-empty">将鼠标移到左侧岗位卡片上，或点击卡片固定查看。</div>
        </div>

        <p class="reason-hint">{{ interactionHint }}</p>
      </aside>
    </div>

    <div v-if="displayJobs.length && !loading" class="section-foot">
      <p v-if="lastDurationLabel" class="match-done-hint">本次匹配用时 {{ lastDurationLabel }}</p>
      <button type="button" class="more-btn" @click="emit('view-more')">查看更多</button>
    </div>
  </section>
</template>

<style scoped>
.match-section {
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow);
  padding: 18px 18px 16px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.card-panel {
  margin-bottom: 4px;
}
.section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-shrink: 0;
}
.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.section-title-wrap h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
}
.score-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: #ecfdf5;
  color: #059669;
  font-size: 0.72rem;
  font-weight: 700;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.filter-select {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 0.76rem;
  color: #475569;
  background: #fff;
  min-width: 96px;
}
.match-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(268px, 320px);
  gap: 16px;
  align-items: start;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.match-body--single {
  grid-template-columns: minmax(0, 1fr);
  height: 100%;
}
.job-grid-wrap {
  min-width: 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  --job-grid-cols: 3;
  --job-grid-visible-rows: 3;
  --job-card-row-h: 196px;
  --job-grid-gap: 10px;
}
.job-grid-scroll {
  min-width: 0;
  min-height: 0;
}
.job-grid-scroll--pane {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  padding-right: 4px;
  margin-right: -4px;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  touch-action: pan-y;
}
.job-grid-scroll--pane::-webkit-scrollbar {
  width: 6px;
}
.job-grid-scroll--pane::-webkit-scrollbar-thumb {
  background: rgba(91, 106, 223, 0.35);
  border-radius: 999px;
}
.job-grid-scroll--pane::-webkit-scrollbar-track {
  background: transparent;
}
.job-grid {
  display: grid;
  grid-template-columns: repeat(var(--job-grid-cols), minmax(0, 1fr));
  gap: var(--job-grid-gap);
  min-width: 0;
  align-items: start;
  align-content: start;
}
.scroll-hint {
  margin: 8px 0 0;
  font-size: 0.68rem;
  color: #94a3b8;
  text-align: center;
}
.reason-rail {
  display: flex;
  flex-direction: column;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid #e0e7ff;
  background: linear-gradient(180deg, #fafbff 0%, #f8fafc 100%);
  position: sticky;
  top: 12px;
  align-self: start;
  width: 100%;
  min-height: 280px;
  max-height: min(calc(100vh - 120px), 640px);
}
.reason-rail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e8ecff;
  flex-shrink: 0;
}
.reason-rail-label {
  margin: 0 0 4px;
  font-size: 0.7rem;
  font-weight: 700;
  color: #6366f1;
  letter-spacing: 0.06em;
}
.reason-rail-title {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.35;
}
.reason-rail-meta {
  margin: 4px 0 0;
  font-size: 0.72rem;
  color: #64748b;
}
.reason-detail-btn {
  flex-shrink: 0;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid #c7d2fe;
  background: #fff;
  color: #4338ca;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}
.reason-detail-btn:hover {
  background: #eef2ff;
}
.reason-rail-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-right: 2px;
}
.reason-rail-body :deep(.job-match-reason-block) {
  padding: 8px 10px;
}
.reason-rail-body :deep(.job-match-reason-block-title) {
  font-size: 0.78rem;
}
.reason-rail-body :deep(.job-match-reason-block-body) {
  font-size: 0.76rem;
  line-height: 1.55;
}
.reason-empty {
  padding: 20px 8px;
  text-align: center;
  font-size: 0.8rem;
  color: #94a3b8;
  line-height: 1.6;
}
.reason-hint {
  margin: 10px 0 0;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
  font-size: 0.68rem;
  color: #94a3b8;
  text-align: center;
  flex-shrink: 0;
}
.loading-box,
.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 200px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px dashed #cbd5e1;
  color: #64748b;
  font-size: 0.88rem;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}
.skeleton-card {
  height: 120px;
  border-radius: 12px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.empty-match {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 200px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px dashed #cbd5e1;
  padding: 28px 24px;
  text-align: center;
}
.empty-match-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #334155;
}
.empty-match-desc {
  margin: 0;
  font-size: 0.82rem;
  color: #64748b;
  line-height: 1.6;
  max-width: 320px;
}
.empty-match-action {
  border: 1px solid #c7d2fe;
  background: #fff;
  color: #4338ca;
  border-radius: 999px;
  padding: 8px 18px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.empty-match-action:hover {
  background: #eef2ff;
}
.spinner {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 3px solid #e2e8f0;
  border-top-color: #5b6adf;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.ghost-btn,
.more-btn {
  border: 1px solid #c7d2fe;
  background: #fff;
  color: #4338ca;
  border-radius: 999px;
  padding: 8px 18px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.section-foot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  flex-shrink: 0;
}
.match-done-hint {
  margin: 0;
  font-size: 0.72rem;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}
.more-btn:hover,
.ghost-btn:hover {
  background: #eef2ff;
}
@media (max-width: 1100px) {
  .match-body {
    grid-template-columns: 1fr;
  }
  .reason-rail {
    position: static;
    max-height: min(36vh, 320px);
  }
  .job-grid-wrap {
    --job-grid-cols: 2;
    --job-grid-visible-rows: 3;
  }
}
@media (max-width: 640px) {
  .job-grid-wrap {
    --job-grid-cols: 1;
    --job-grid-visible-rows: 4;
  }
}
</style>
