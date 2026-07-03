<script setup>
/**
 * 面试模块二级导航：面试中心 / 题目大纲 / 行业字典。
 */
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const items = [
  { path: "/interview/center", label: "面试中心", match: (p) => p === "/interview/center" || p.startsWith("/me/interviews/") },
  { path: "/interview/industry", label: "题目大纲", match: (p) => p.startsWith("/interview/industry") || p.startsWith("/interview/plans") },
  { path: "/interview/categories", label: "行业字典", match: (p) => p.startsWith("/interview/categories") }
];

const activePath = computed(() => route.path);

function isActive(item) {
  return item.match(activePath.value);
}
</script>

<template>
  <nav class="interview-section-nav" aria-label="面试模块导航">
    <RouterLink
      v-for="item in items"
      :key="item.path"
      :to="item.path"
      class="interview-section-nav__link"
      :class="{ active: isActive(item) }"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>

<style scoped>
.interview-section-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: -8px calc(-1 * var(--home-main-px, 20px)) 14px;
  padding: 0 var(--home-main-px, 20px) 12px;
  border-bottom: 1px solid rgba(91, 106, 223, 0.1);
}
.interview-section-nav__link {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.interview-section-nav__link:hover {
  border-color: #c7d2fe;
  color: #4338ca;
  background: #f8faff;
}
.interview-section-nav__link.active {
  border-color: transparent;
  background: linear-gradient(135deg, #5b6adf, #6366f1);
  color: #fff;
  box-shadow: 0 4px 12px rgba(91, 106, 223, 0.22);
}
@media (max-width: 720px) {
  .interview-section-nav {
    margin-left: -10px;
    margin-right: -10px;
    padding-left: 10px;
    padding-right: 10px;
  }
}
</style>
