<script setup>
/** 大纲状态徽章 — 草稿/已发布/已归档 */
defineProps({
  status: { type: String, default: "" },
  label: { type: String, default: "" },
  tone: { type: String, default: "muted" }
});
</script>

<template>
  <span class="status-pill" :class="`tone-${tone}`">{{ label }}</span>
</template>

<style scoped>
.status-pill {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
}

.tone-draft {
  background: #fef3c7;
  color: #b45309;
}

.tone-published {
  background: #dcfce7;
  color: #15803d;
}

.tone-archived,
.tone-muted {
  background: #f3f4f6;
  color: #6b7280;
}
</style>
