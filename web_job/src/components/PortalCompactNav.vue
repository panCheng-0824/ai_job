<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { chatSidebarVisibleRef } from "../composables/useChatSidebarVisible";

const router = useRouter();
const route = useRoute();
const options = [
  { value: "/student", label: "学生主页" },
  { value: "/companies", label: "企业列表" },
  { value: "/jobs", label: "岗位列表" },
  { value: "/me", label: "我的" },
  { value: "/login", label: "切换账号" }
];

const model = ref("");

function syncFromRoute() {
  const p = route.path;
  let v = "";
  if (p.startsWith("/companies")) v = "/companies";
  else if (p.startsWith("/jobs")) v = "/jobs";
  else if (p === "/me") v = "/me";
  else if (p === "/student") v = "/student";
  else if (p === "/login") v = "/login";
  model.value = v || "";
}

watch(() => route.fullPath, syncFromRoute, { immediate: true });

const hideForChatFocus = computed(
  () => route.path.startsWith("/student-chat") && !chatSidebarVisibleRef.value
);

function onChange() {
  if (model.value) router.push(model.value);
}
</script>

<template>
  <header v-show="!hideForChatFocus" class="portal-top-nav">
    <div class="nav-container">
      <div class="logo">智能 · AI 就业</div>
      <select v-model="model" class="nav-select" aria-label="主导航" @change="onChange">
        <option value="" disabled>页面跳转…</option>
        <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
    </div>
  </header>
</template>

<style scoped>
.portal-top-nav {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 1100;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
.nav-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.logo {
  font-size: 1.25rem;
  font-weight: 700;
  background: linear-gradient(to right, var(--primary-color, #6366f1), var(--secondary-color, #a855f7));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.nav-select {
  min-width: 190px;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 0.9rem;
  background: #fff;
  color: #1f2937;
}
</style>
