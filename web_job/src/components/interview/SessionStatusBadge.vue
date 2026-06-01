<script setup>
/**
 * 会话状态徽章（待开始 / 进行中 / 已完成等）。
 */
import { SESSION_STATUS } from "../../modules/interview/constants";

defineProps({
  status: { type: String, default: "" }
});

function meta(s) {
  return SESSION_STATUS[s] || { label: s || "—", tone: "muted" };
}
</script>

<template>
  <span class="badge" :class="`badge--${meta(status).tone}`">{{ meta(status).label }}</span>
</template>

<style scoped>
.badge {
  display: inline-block;
  font-size: 0.75rem;
  padding: 2px 10px;
  border-radius: 999px;
  font-weight: 600;
}
.badge--info {
  background: #eef2ff;
  color: #4338ca;
}
.badge--ok {
  background: #d1fae5;
  color: #047857;
}
.badge--muted {
  background: #f3f4f6;
  color: #6b7280;
}
</style>
