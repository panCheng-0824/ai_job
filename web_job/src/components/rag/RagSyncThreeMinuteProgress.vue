<script setup>
import { computed } from "vue";
import { formatRagSyncDuration } from "../../composables/useRagSyncThreeMinuteProgress";

const props = defineProps({
  running: { type: Boolean, default: false },
  elapsedMs: { type: Number, default: 0 },
  fillPct: { type: Number, default: 0 },
  fillPctRounded: { type: Number, default: 0 },
  fillColorClass: { type: String, default: "rag3-fill--m1" },
  progressLabel: { type: String, default: "" },
  overScale: { type: Boolean, default: false },
  title: { type: String, default: "同步进度" },
  jobName: { type: String, default: "" },
});

const minuteTicks = computed(() =>
  [1, 2, 3].map((minute) => ({
    minute,
    leftPct: (minute / 3) * 100,
  }))
);
</script>

<template>
  <div
    v-if="running"
    class="rag3-progress-wrap"
    role="progressbar"
    :aria-valuenow="fillPctRounded"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-label="progressLabel || title"
  >
    <div class="rag3-progress-head">
      <span class="rag3-progress-title">{{ title }}</span>
      <strong class="rag3-elapsed">{{ formatRagSyncDuration(elapsedMs) }}</strong>
      <span v-if="overScale" class="rag3-over-tag">已超 3 分钟</span>
    </div>
    <p v-if="jobName" class="rag3-job-name" :title="jobName">正在同步：{{ jobName }}</p>
    <div class="rag3-track" :class="{ 'rag3-track--over': overScale }">
      <div
        v-for="tick in minuteTicks"
        :key="tick.minute"
        class="rag3-tick"
        :style="{ left: tick.leftPct + '%' }"
      >
        <span>{{ tick.minute }}′</span>
      </div>
      <div class="rag3-fill" :class="fillColorClass" :style="{ width: fillPct + '%' }" />
    </div>
    <p class="rag3-label">{{ progressLabel }}</p>
    <p class="rag3-hint muted">刻度固定 3 分钟：第 1 / 2 / 3 分钟区间颜色由浅到深。</p>
  </div>
</template>

<style scoped>
.rag3-progress-wrap {
  margin: 12px 0 0;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #dbeafe;
  background: linear-gradient(180deg, #f8fafc, #fff);
}
.rag3-progress-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 12px;
  margin-bottom: 10px;
}
.rag3-progress-title {
  font-size: 0.82rem;
  color: var(--text-muted);
  font-weight: 600;
}
.rag3-elapsed {
  font-size: 1.15rem;
  color: #1e293b;
  letter-spacing: 0.02em;
}
.rag3-over-tag {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  font-weight: 600;
}
.rag3-job-name {
  margin: 0 0 8px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rag3-track {
  position: relative;
  height: 18px;
  margin-top: 20px;
  border-radius: 999px;
  overflow: hidden;
  background: linear-gradient(
    90deg,
    #ecfdf5 0%,
    #ecfdf5 33.333%,
    #bbf7d0 33.333%,
    #bbf7d0 66.666%,
    #86efac 66.666%,
    #86efac 100%
  );
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.08);
}
.rag3-track--over {
  box-shadow: inset 0 0 0 1px #fca5a5, inset 0 1px 2px rgba(15, 23, 42, 0.08);
}
.rag3-tick {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(255, 255, 255, 0.7);
  z-index: 2;
  pointer-events: none;
}
.rag3-tick span {
  position: absolute;
  top: -18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.65rem;
  color: #64748b;
  white-space: nowrap;
}
.rag3-fill {
  position: relative;
  z-index: 1;
  height: 100%;
  border-radius: 999px;
  transition: width 0.55s linear, background 0.45s ease;
  min-width: 4px;
}
.rag3-fill--m1 {
  background: linear-gradient(90deg, #6ee7b7, #34d399);
}
.rag3-fill--m2 {
  background: linear-gradient(90deg, #34d399, #059669);
}
.rag3-fill--m3 {
  background: linear-gradient(90deg, #059669, #047857);
}
.rag3-label {
  margin: 8px 0 0;
  font-size: 0.8rem;
  color: #475569;
}
.rag3-hint {
  margin: 6px 0 0;
  font-size: 0.74rem;
  line-height: 1.45;
}
.muted {
  color: var(--text-muted);
}
</style>
