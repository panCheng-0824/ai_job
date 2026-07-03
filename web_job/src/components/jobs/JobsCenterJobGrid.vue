<script setup>
/**
 * 岗位中心主区：Tab + 排序 + 3×3 岗位网格。
 */
import { computed, ref, watch } from "vue";
import { formatJobMatchElapsed } from "../../composables/useJobMatchWaitTimer";
import {
  findJobById,
  normalizeJobId,
  useJobRecommendDisplay
} from "../../composables/useJobRecommendDisplay";
import { dedupeJobs } from "../../utils/jobDedupe";
import JobMatchWaitingPanel from "./JobMatchWaitingPanel.vue";
import HomeMatchedJobCard from "../home/HomeMatchedJobCard.vue";
import HomeMatchedJobPlaceholder from "../home/HomeMatchedJobPlaceholder.vue";

const MIN_GRID_SLOTS = 9;
const MAX_VISIBLE_SLOTS = 9;

const props = defineProps({
  jobs: { type: Array, default: () => [] },
  recommendation: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  emptyText: { type: String, default: "暂无岗位" },
  padPlaceholders: { type: Boolean, default: false },
  /** 热招等分页列表：展开全部已加载项，由页面下滑触发加载更多 */
  expandAll: { type: Boolean, default: false },
  /** 智能匹配等待：已等待毫秒 */
  matchElapsedMs: { type: Number, default: 0 },
  /** 智能匹配完成后总耗时 */
  lastMatchDurationMs: { type: Number, default: null }
});

const emit = defineEmits(["view-detail", "apply", "resume", "interview"]);

const sortMode = defineModel("sortMode", { type: String, default: "score" });

const displayJobs = computed(() => {
  const list = dedupeJobs([...(props.jobs || [])]);
  if (sortMode.value === "score") {
    list.sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  } else {
    list.sort((a, b) => Number(b.createTime || b.create_time || 0) - Number(a.createTime || a.create_time || 0));
  }
  return list;
});

const gridSlots = computed(() => {
  const jobs = displayJobs.value;
  const slots = jobs.map((job) => ({
    type: "job",
    job,
    key: `${normalizeJobId(job.job_id || job.id)}-${job.job_title || ""}`
  }));
  if (!props.padPlaceholders) return slots;
  const pad = Math.max(0, MIN_GRID_SLOTS - jobs.length);
  for (let i = 0; i < pad; i += 1) {
    slots.push({ type: "placeholder", key: `placeholder-${i}` });
  }
  return slots;
});

const hasScrollableJobs = computed(
  () => !props.expandAll && displayJobs.value.length > MAX_VISIBLE_SLOTS
);

const scrollHint = computed(() => {
  if (props.expandAll) return "";
  const n = displayJobs.value.length;
  if (n <= MAX_VISIBLE_SLOTS) return "";
  return `共 ${n} 个岗位 · 区域内滑动查看更多`;
});

const showRichMatchWait = computed(() => props.loading && props.padPlaceholders);

const lastDurationLabel = computed(() => {
  if (props.lastMatchDurationMs == null) return "";
  return formatJobMatchElapsed(props.lastMatchDurationMs);
});

const reasonSelectEnabled = computed(() => props.padPlaceholders);
const pinnedJobId = ref(null);

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
  () => [displayJobs.value, reasonSelectEnabled.value],
  ([list, enabled]) => {
    if (!enabled) return;
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

const interactionHint = computed(() => {
  if (!reasonSelectEnabled.value) return "";
  if (pinnedJobId.value) return "已固定当前岗位，点击其他卡片可切换";
  return "悬停预览 · 点击卡片固定推荐理由";
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
  if (!reasonSelectEnabled.value) return;
  if (pinnedJobId.value) {
    onJobCardHover(job, { previewOnly: true });
    return;
  }
  onJobCardHover(job);
}

function onCardSelect(job) {
  if (!reasonSelectEnabled.value) return;
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

function onGridLeave() {
  if (!reasonSelectEnabled.value) return;
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
  <section class="jobs-center-panel">
    <header class="jobs-center-head">
      <div class="jobs-sort">
        <button
          type="button"
          class="sort-btn"
          :class="{ active: sortMode === 'latest' }"
          @click="sortMode = 'latest'"
        >
          按最新排序
        </button>
        <button
          type="button"
          class="sort-btn"
          :class="{ active: sortMode === 'score' }"
          @click="sortMode = 'score'"
        >
          按匹配度排序
        </button>
      </div>
    </header>

    <slot name="before-grid" />

    <JobMatchWaitingPanel
      v-if="showRichMatchWait"
      :elapsed-ms="matchElapsedMs"
      title="正在智能匹配岗位"
    />

    <div v-else-if="loading" class="jobs-loading">
      <div class="spinner" aria-hidden="true" />
      <p>加载中…</p>
    </div>

    <div v-else-if="!displayJobs.length" class="jobs-empty">{{ emptyText }}</div>

    <div v-else class="job-grid-wrap" @mouseleave="onGridLeave">
      <div
        class="job-grid-scroll"
        :class="{ 'job-grid-scroll--active': hasScrollableJobs }"
        tabindex="0"
      >
        <div class="job-grid">
          <template v-for="slot in gridSlots" :key="slot.key">
            <HomeMatchedJobCard
              v-if="slot.type === 'job'"
              :job="slot.job"
              :recommendation="recommendation"
              :active="reasonSelectEnabled && sameJobId(displayJobId, slot.job.job_id)"
              :hover="reasonSelectEnabled && sameJobId(hoverJobId, slot.job.job_id)"
              :pinned="reasonSelectEnabled && sameJobId(pinnedJobId, slot.job.job_id)"
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
      <p v-if="lastDurationLabel && padPlaceholders" class="match-done-hint">
        本次匹配用时 {{ lastDurationLabel }}
      </p>
    </div>

    <slot name="after-grid" />
  </section>
</template>

<style scoped>
.jobs-center-panel {
  min-width: 0;
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border);
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow);
  padding: 16px 18px;
}
.jobs-center-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 14px;
}
.jobs-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.jobs-tab {
  border: none;
  background: transparent;
  padding: 8px 4px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}
.jobs-tab.active {
  color: #4338ca;
  border-bottom-color: #6366f1;
}
.jobs-sort {
  display: flex;
  gap: 8px;
}
.sort-btn {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 6px 10px;
  background: #fff;
  color: #64748b;
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
}
.sort-btn.active {
  border-color: #c7d2fe;
  background: #eef2ff;
  color: #4338ca;
}
.jobs-loading,
.jobs-empty {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 0.88rem;
  gap: 10px;
}
.spinner {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 3px solid #e2e8f0;
  border-top-color: #5b6adf;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.job-grid-wrap {
  --job-grid-cols: 3;
  --job-grid-visible-rows: 3;
  --job-card-row-h: 196px;
  --job-grid-gap: 10px;
}
.job-grid-scroll--active {
  max-height: calc(
    var(--job-card-row-h) * var(--job-grid-visible-rows) +
      var(--job-grid-gap) * (var(--job-grid-visible-rows) - 1)
  );
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 4px;
}
.job-grid {
  display: grid;
  grid-template-columns: repeat(var(--job-grid-cols), minmax(0, 1fr));
  gap: var(--job-grid-gap);
  align-items: start;
}
.scroll-hint,
.match-done-hint {
  margin: 8px 0 0;
  font-size: 0.68rem;
  color: #94a3b8;
  text-align: center;
}
.match-done-hint {
  font-variant-numeric: tabular-nums;
}
@media (max-width: 1280px) {
  .job-grid-wrap { --job-grid-cols: 2; }
}
@media (max-width: 720px) {
  .job-grid-wrap {
    --job-grid-cols: 1;
    --job-grid-visible-rows: 4;
  }
}
</style>
