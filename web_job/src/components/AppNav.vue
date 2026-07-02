<script setup>
import { useRouter } from "vue-router";
import { isLoggedIn, logout } from "../api/client";

const router = useRouter();

const links = [
  { path: "/student", label: "学生主页" },
  { path: "/resume/create", label: "创建简历" },
  { path: "/jobs", label: "岗位列表" },
  { path: "/companies", label: "企业列表" },
  { path: "/me", label: "我的" },
  { path: "/student-chat", label: "AI助手" }
];

function onLogout() {
  if (isLoggedIn()) logout({ router });
  else router.push("/login");
}
</script>

<template>
  <nav class="nav">
    <router-link v-for="item in links" :key="item.path" :to="item.path">{{ item.label }}</router-link>
    <button type="button" class="logout-link" @click="onLogout">退出登录</button>
  </nav>
</template>

<style scoped>
.nav { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }
a { text-decoration: none; color: #4f46e5; font-weight: 600; }
a.router-link-active { color: #1f2937; }
.logout-link {
  border: none;
  background: none;
  padding: 0;
  color: #b91c1c;
  font-weight: 600;
  cursor: pointer;
  font-size: inherit;
  font-family: inherit;
}
.logout-link:hover { text-decoration: underline; }
</style>
