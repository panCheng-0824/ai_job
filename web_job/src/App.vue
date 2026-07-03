<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import PortalCompactNav from "./components/PortalCompactNav.vue";
import PortalNavWheel from "./components/PortalNavWheel.vue";
import EmbedDetailLayout from "./layouts/EmbedDetailLayout.vue";

const route = useRoute();
const isLogin = computed(() => route.path === "/login" || route.path === "/");
const isEmbed = computed(() => route.query._embed === "1");
/** 岗位/企业详情嵌入页使用统一卡片布局；其他 _embed 页保持原样 */
const useEmbedDetailLayout = computed(() => {
  if (!isEmbed.value) return false;
  const p = route.path || "";
  return /^\/jobs\/[^/]+/.test(p) || /^\/companies\/[^/]+/.test(p);
});
/** 共享侧栏壳层内的路由（HomeLayout 子路由） */
const isHomeDashboard = computed(() => {
  if (route.query._embed === "1") return false;
  return route.matched.some((r) => r.meta.homeLayout);
});
</script>

<template>
  <EmbedDetailLayout v-if="useEmbedDetailLayout" />
  <router-view v-else-if="isLogin || isEmbed" />
  <template v-else>
    <router-view v-slot="{ Component, route: r }">
      <component :is="Component" :key="isHomeDashboard ? 'home-layout' : r.path" />
    </router-view>
    <PortalCompactNav v-if="!isHomeDashboard" />
    <PortalNavWheel v-if="!isHomeDashboard" />
  </template>
</template>
