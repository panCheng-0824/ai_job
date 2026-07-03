<script setup>
import { computed } from "vue";

const props = defineProps({
  count: { type: Number, default: 0 },
  max: { type: Number, default: 3 },
  /** 已选岗位摘要，用于底部预览 */
  previewJobs: { type: Array, default: () => [] }
});

defineEmits(["open", "clear"]);

const chips = computed(() =>
  (props.previewJobs || []).slice(0, props.max).map((job) => ({
    id: job.job_id || job.id,
    title: job.job_title || job.job_name || "未命名岗位",
    score: job.score ?? job.match_score
  }))
);
</script>

<template>
  <Transition name="compare-bar-slide">
    <div v-if="count > 0" class="compare-bar">
      <div class="compare-bar-main">
        <span class="compare-bar-info">已选 {{ count }}/{{ max }} 个岗位</span>
        <div v-if="chips.length" class="compare-bar-chips" aria-label="已选岗位预览">
          <span v-for="chip in chips" :key="chip.id" class="compare-chip" :title="chip.title">
            <span class="compare-chip-title">{{ chip.title }}</span>
            <span v-if="chip.score != null" class="compare-chip-score">{{ Math.round(chip.score) }}</span>
          </span>
        </div>
      </div>
      <div class="compare-bar-actions">
        <button type="button" class="compare-bar-btn primary" :disabled="count < 2" @click="$emit('open')">
          {{ count < 2 ? "至少选 2 个" : "开始对比" }}
        </button>
        <button type="button" class="compare-bar-btn" @click="$emit('clear')">清空</button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.compare-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.96);
  border-top: 1px solid #e2e8f0;
  box-shadow: 0 -6px 24px rgba(15, 23, 42, 0.1);
  backdrop-filter: blur(8px);
}
.compare-bar-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.compare-bar-info {
  font-size: 0.84rem;
  font-weight: 700;
  color: #1e293b;
}
.compare-bar-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.compare-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: min(220px, 42vw);
  padding: 4px 10px;
  border-radius: 999px;
  background: #eef2ff;
  border: 1px solid #e0e7ff;
  font-size: 0.72rem;
  color: #4338ca;
}
.compare-chip-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.compare-chip-score {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 999px;
  background: #4338ca;
  color: #fff;
  font-weight: 700;
  font-size: 0.64rem;
}
.compare-bar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.compare-bar-btn {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.compare-bar-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.compare-bar-btn.primary {
  background: var(--home-primary, #5b6adf);
  color: #fff;
  border-color: transparent;
}
.compare-bar-btn.primary:hover:not(:disabled) {
  background: #4f5ad4;
}
.compare-bar-slide-enter-active,
.compare-bar-slide-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.compare-bar-slide-enter-from,
.compare-bar-slide-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

@media (max-width: 640px) {
  .compare-bar {
    flex-direction: column;
    align-items: stretch;
    padding: 10px 14px 14px;
  }
  .compare-bar-actions {
    justify-content: flex-end;
  }
}
</style>
