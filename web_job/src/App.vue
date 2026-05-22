<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import PortalCompactNav from "./components/PortalCompactNav.vue";
import PortalNavWheel from "./components/PortalNavWheel.vue";

const route = useRoute();
const isLogin = computed(() => route.path === "/login" || route.path === "/");
const isEmbed = computed(() => route.query._embed === "1");
</script>

<template>
  <router-view v-if="isLogin || isEmbed" />
  <template v-else>
    <PortalCompactNav />
    <router-view />
    <PortalNavWheel />
  </template>
</template>
