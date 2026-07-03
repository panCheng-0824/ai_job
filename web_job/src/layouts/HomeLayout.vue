<script setup>
/**
 * 登录后仪表盘共享壳层：侧栏固定，顶栏统一渲染，主内容区随路由切换。
 */
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { apiGet, getStudentId } from "../api/client";
import { setStudentServerAvatar, syncStudentAvatar } from "../composables/useStudentAvatar";
import { homePageHeader } from "../composables/useHomePageHeader";
import AvatarCropModal from "../components/home/AvatarCropModal.vue";
import HomeSidebar from "../components/home/HomeSidebar.vue";
import HomeTopBar from "../components/home/HomeTopBar.vue";

const route = useRoute();

/** 全屏页在壳层上加修饰类（聊天、面试房间、简历） */
const shellClass = computed(() => {
  const p = route.path;
  if (p.startsWith("/student-chat")) return "home-shell--chat";
  if (p.startsWith("/interview/center/room")) return "home-shell--room";
  if (p.startsWith("/resume")) return "home-shell--resume";
  return "";
});

const showTopBar = computed(() => !homePageHeader.hidden && Boolean(homePageHeader.title));

onMounted(async () => {
  const sid = getStudentId();
  syncStudentAvatar(sid);
  if (!sid) return;
  try {
    const q = new URLSearchParams({ student_id: sid });
    const profile = await apiGet(`/api/me/profile?${q}`);
    setStudentServerAvatar(profile?.["学生基本信息"]?.["头像"], sid);
  } catch {
    /* 侧栏等处仍可用 localStorage 占位 */
  }
});
</script>

<template>
  <div class="home-shell" :class="shellClass">
    <HomeSidebar />
    <div class="home-shell-main">
      <HomeTopBar
        v-if="showTopBar"
        :title="homePageHeader.title"
        :subtitle="homePageHeader.subtitle"
        :student-name="homePageHeader.studentName"
      />
      <router-view />
    </div>
    <AvatarCropModal />
  </div>
</template>
