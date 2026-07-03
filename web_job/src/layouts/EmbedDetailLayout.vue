<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { fullPageUrl } from "../utils/embedFrame";

const route = useRoute();

const isInIframe = computed(() => {
  if (typeof window === "undefined") return false;
  try {
    return window.self !== window.top;
  } catch {
    return true;
  }
});

const pageLabel = computed(() => {
  const p = route.path || "";
  if (p.startsWith("/companies")) return "企业详情";
  if (p.startsWith("/jobs")) return "岗位详情";
  return "详情预览";
});

function openFullPage() {
  const url = fullPageUrl(route.fullPath);
  window.open(url, "_blank", "noopener,noreferrer");
}

function closeWindow() {
  window.close();
}
</script>

<template>
  <div class="embed-page" :class="{ 'embed-page--iframe': isInIframe }">
    <header v-if="!isInIframe" class="embed-page__toolbar">
      <div class="embed-page__toolbar-left">
        <span class="embed-page__brand">{{ pageLabel }}</span>
        <span class="embed-page__hint">嵌入预览 · 风格与智能匹配一致</span>
      </div>
      <div class="embed-page__actions">
        <button type="button" class="embed-page__btn" @click="closeWindow">关闭窗口</button>
        <button type="button" class="embed-page__btn embed-page__btn--primary" @click="openFullPage">
          完整页面
        </button>
      </div>
    </header>
    <main class="embed-page__main" :class="{ 'embed-page__main--iframe': isInIframe }">
      <div class="embed-page__card" :class="{ 'embed-page__card--iframe': isInIframe }">
        <router-view />
      </div>
    </main>
  </div>
</template>

<style scoped>
.embed-page__toolbar-left {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px;
  min-width: 0;
}
</style>
