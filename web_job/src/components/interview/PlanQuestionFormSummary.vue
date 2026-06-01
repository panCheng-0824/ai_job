<script setup>
/**
 * 题目列表折叠摘要 — 收起时展示题量与首题预览。
 */
defineProps({
  count: { type: Number, default: 0 },
  preview: { type: String, default: "" },
  progressLabel: { type: String, default: "" }
});
</script>

<template>
  <div class="questions-summary">
    <p class="summary-meta">{{ progressLabel || `共 ${count} 题` }}</p>
    <p v-if="preview" class="summary-preview">{{ preview }}</p>
    <p v-else class="summary-empty">点击展开编辑题目</p>
  </div>
</template>

<style scoped>
.questions-summary {
  padding: 12px 14px 14px;
  border-top: 1px solid #f1f5f9;
}

.summary-meta {
  margin: 0;
  font-size: 0.82rem;
  color: #6b7280;
}

.summary-preview {
  margin: 6px 0 0;
  font-size: 0.85rem;
  line-height: 1.45;
  color: #374151;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.summary-empty {
  margin: 6px 0 0;
  font-size: 0.82rem;
  color: #9ca3af;
}
</style>
