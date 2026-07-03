<script setup>
/**
 * 岗位推荐等待态：3×3 骨架卡片 + 阶段进度 + 已等待时长；首页可带右侧理由栏骨架。
 */
import { computed } from "vue";
import {
  JOB_MATCH_WAIT_STEPS,
  formatJobMatchElapsed,
  resolveJobMatchStepIndex
} from "../../composables/useJobMatchWaitTimer";
import HomeMatchedJobPlaceholder from "../home/HomeMatchedJobPlaceholder.vue";

const GRID_SLOTS = 9;

const props = defineProps({
  elapsedMs: { type: Number, default: 0 },
  showReasonRail: { type: Boolean, default: false },
  title: { type: String, default: "智能匹配进行中" }
});

const elapsedLabel = computed(() => formatJobMatchElapsed(props.elapsedMs));

const stepIndex = computed(() => resolveJobMatchStepIndex(props.elapsedMs));

const stepLabel = computed(() => JOB_MATCH_WAIT_STEPS[stepIndex.value]?.label || "正在匹配");

const progressPercent = computed(() => {
  const idx = stepIndex.value;
  const total = JOB_MATCH_WAIT_STEPS.length;
  return Math.min(100, Math.round(((idx + 1) / total) * 100));
});
</script>

<template>
  <div
    class="match-wait"
    role="status"
    aria-live="polite"
    :aria-label="`${title}，已等待 ${elapsedLabel}`"
  >
    <header class="match-wait-head">
      <div class="match-wait-title-wrap">
        <span class="match-wait-pulse" aria-hidden="true" />
        <div>
          <p class="match-wait-title">{{ title }}</p>
          <p class="match-wait-step">{{ stepLabel }}…</p>
        </div>
      </div>
      <div class="match-wait-timer" aria-label="已等待时长">
        <span class="match-wait-timer-label">已等待</span>
        <strong class="match-wait-timer-value">{{ elapsedLabel }}</strong>
      </div>
    </header>

    <div class="match-wait-progress" aria-hidden="true">
      <div class="match-wait-progress-track">
        <div class="match-wait-progress-bar" :style="{ width: `${progressPercent}%` }" />
      </div>
      <ul class="match-wait-steps">
        <li
          v-for="(step, i) in JOB_MATCH_WAIT_STEPS"
          :key="step.label"
          class="match-wait-step-item"
          :class="{
            done: i < stepIndex,
            active: i === stepIndex,
            pending: i > stepIndex
          }"
        >
          <span class="match-wait-step-dot" />
          <span class="match-wait-step-text">{{ step.label }}</span>
        </li>
      </ul>
    </div>

    <div class="match-wait-body" :class="{ 'match-wait-body--with-rail': showReasonRail }">
      <div class="match-wait-grid-wrap">
        <div class="match-wait-grid">
          <HomeMatchedJobPlaceholder
            v-for="i in GRID_SLOTS"
            :key="`wait-${i}`"
            loading
            :stagger="i"
          />
        </div>
        <p class="match-wait-grid-hint">岗位卡片加载中，请稍候…</p>
      </div>

      <aside v-if="showReasonRail" class="match-wait-rail" aria-hidden="true">
        <div class="match-wait-rail-head">
          <span class="sk-line sk-line--sm" />
          <span class="sk-line sk-line--md" />
        </div>
        <div class="match-wait-rail-body">
          <span v-for="n in 4" :key="n" class="sk-block" />
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.match-wait {
  border-radius: 14px;
  border: 1px solid rgba(99, 102, 241, 0.18);
  background: linear-gradient(180deg, #fafbff 0%, #f8fafc 100%);
  padding: 14px 14px 16px;
}
.match-wait-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.match-wait-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.match-wait-pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #6366f1;
  flex-shrink: 0;
  animation: wait-pulse 1.2s ease-in-out infinite;
}
@keyframes wait-pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.45);
  }
  50% {
    transform: scale(1.15);
    opacity: 0.85;
    box-shadow: 0 0 0 8px rgba(99, 102, 241, 0);
  }
}
.match-wait-title {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: #1e293b;
}
.match-wait-step {
  margin: 2px 0 0;
  font-size: 0.78rem;
  color: #6366f1;
  font-weight: 600;
}
.match-wait-timer {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  padding: 8px 12px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e0e7ff;
  box-shadow: 0 1px 2px rgba(99, 102, 241, 0.06);
}
.match-wait-timer-label {
  font-size: 0.68rem;
  color: #94a3b8;
  font-weight: 600;
}
.match-wait-timer-value {
  font-size: 1rem;
  font-weight: 800;
  color: #4338ca;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}
.match-wait-progress {
  margin-bottom: 14px;
}
.match-wait-progress-track {
  height: 4px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
  margin-bottom: 10px;
}
.match-wait-progress-bar {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #818cf8, #6366f1);
  transition: width 0.45s ease;
}
.match-wait-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
}
.match-wait-step-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.68rem;
  color: #94a3b8;
  transition: color 0.25s ease;
}
.match-wait-step-item.done {
  color: #64748b;
}
.match-wait-step-item.active {
  color: #4338ca;
  font-weight: 700;
}
.match-wait-step-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.55;
}
.match-wait-step-item.active .match-wait-step-dot {
  opacity: 1;
  animation: wait-pulse 1.2s ease-in-out infinite;
}
.match-wait-step-text {
  white-space: nowrap;
}
.match-wait-body {
  min-width: 0;
}
.match-wait-body--with-rail {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(268px, 320px);
  gap: 16px;
  align-items: start;
}
.match-wait-grid-wrap {
  min-width: 0;
}
.match-wait-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.match-wait-grid-hint {
  margin: 8px 0 0;
  text-align: center;
  font-size: 0.68rem;
  color: #94a3b8;
}
.match-wait-rail {
  padding: 14px;
  border-radius: 12px;
  border: 1px dashed #c7d2fe;
  background: rgba(255, 255, 255, 0.72);
  min-height: 280px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.match-wait-rail-head {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px dashed #e2e8f0;
}
.sk-line {
  display: block;
  height: 10px;
  border-radius: 6px;
  background: linear-gradient(90deg, #e2e8f0 0%, #f1f5f9 50%, #e2e8f0 100%);
  background-size: 200% 100%;
  animation: sk-shimmer 1.4s ease-in-out infinite;
}
.sk-line--sm {
  width: 38%;
}
.sk-line--md {
  width: 72%;
  height: 14px;
}
.sk-block {
  display: block;
  height: 52px;
  border-radius: 8px;
  background: linear-gradient(90deg, #e8ecff 0%, #f8fafc 50%, #e8ecff 100%);
  background-size: 200% 100%;
  animation: sk-shimmer 1.4s ease-in-out infinite;
}
.sk-block:nth-child(2) {
  animation-delay: 0.15s;
}
.sk-block:nth-child(3) {
  animation-delay: 0.3s;
}
.sk-block:nth-child(4) {
  animation-delay: 0.45s;
}
@keyframes sk-shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
@media (max-width: 1100px) {
  .match-wait-body--with-rail {
    grid-template-columns: 1fr;
  }
  .match-wait-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .match-wait-grid {
    grid-template-columns: 1fr;
  }
  .match-wait-steps {
    display: none;
  }
}
</style>
