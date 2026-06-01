<script setup>
/**
 * 总结状态徽章：未总结 / 已总结。
 */
import { SUMMARY_STATUS } from "../../modules/interview/constants";

defineProps({
  status: { type: String, default: "pending" }
});

function meta(s) {
  return SUMMARY_STATUS[s] || { label: s || "—", tone: "muted" };
}
</script>

<template>
  <span class="badge" :class="`badge--${meta(status).tone}`">{{ meta(status).label }}</span>
</template>

<style scoped>
.badge {
  display: inline-block;
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
}
.badge--warn {
  background: #fef3c7;
  color: #b45309;
}
.badge--ok {
  background: #d1fae5;
  color: #047857;
}
.badge--muted {
  background: #f3f4f6;
  color: #6b7280;
}
.badge--info {
  background: #eef2ff;
  color: #4338ca;
}
</style>
