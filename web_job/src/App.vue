<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import PortalCompactNav from "./components/PortalCompactNav.vue";
import PortalNavWheel from "./components/PortalNavWheel.vue";

const route = useRoute();
const isLogin = computed(() => route.path === "/login" || route.path === "/");
const isEmbed = computed(() => route.query._embed === "1");
/** 共享侧栏壳层内的路由（HomeLayout 子路由） */
const isHomeDashboard = computed(() => {
  if (route.query._embed === "1") return false;
  return route.matched.some((r) => r.meta.homeLayout);
});
</script>

<template>
  <router-view v-if="isLogin || isEmbed" />
  <template v-else>
    <router-view v-slot="{ Component, route: r }">
      <component :is="Component" :key="isHomeDashboard ? 'home-layout' : r.path" />
    </router-view>
    <PortalCompactNav v-if="!isHomeDashboard" />
    <PortalNavWheel v-if="!isHomeDashboard" />
  </template>
</template>
