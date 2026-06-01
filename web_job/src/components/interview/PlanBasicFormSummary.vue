<script setup>
/**
 * 基础信息折叠摘要 — 编辑弹窗收起时展示关键字段预览。
 */
import PlanStatusPill from "./PlanStatusPill.vue";

defineProps({
  title: { type: String, default: "" },
  summaryLine: { type: String, default: "" },
  introduction: { type: String, default: "" },
  tags: { type: Array, default: () => [] },
  statusLabel: { type: String, default: "" },
  statusTone: { type: String, default: "muted" }
});
</script>

<template>
  <div class="basic-summary">
    <PlanStatusPill :label="statusLabel" :tone="statusTone" />
    <p class="summary-title">{{ title || "未填写标题" }}</p>
    <p class="summary-text">{{ summaryLine }}</p>
    <p v-if="introduction" class="summary-intro">{{ introduction }}</p>
    <div v-if="tags.length" class="summary-tags">
      <span v-for="t in tags.slice(0, 4)" :key="t" class="tag">{{ t }}</span>
      <span v-if="tags.length > 4" class="tag-more">+{{ tags.length - 4 }}</span>
    </div>
  </div>
</template>

<style scoped>
.basic-summary {
  padding: 12px 14px 14px;
  display: grid;
  gap: 6px;
  border-top: 1px solid #f1f5f9;
}

.summary-title {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 600;
  color: #1f2937;
}

.summary-text {
  margin: 0;
  font-size: 0.82rem;
  color: #6b7280;
}

.summary-intro {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.5;
  color: #4b5563;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.summary-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag,
.tag-more {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
}

.tag-more {
  background: #f3f4f6;
  color: #6b7280;
}
</style>
