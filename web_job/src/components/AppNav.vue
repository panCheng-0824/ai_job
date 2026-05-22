<script setup>
const links = [
  { path: "/student", label: "学生主页" },
  { path: "/resume/create", label: "创建简历" },
  { path: "/jobs", label: "岗位列表" },
  { path: "/companies", label: "企业列表" },
  { path: "/me", label: "我的" },
  { path: "/student-chat", label: "对话助手" },
  { path: "/login", label: "切换账号" }
];
</script>

<template>
  <nav class="nav">
    <router-link v-for="item in links" :key="item.path" :to="item.path">{{ item.label }}</router-link>
  </nav>
</template>

<style scoped>
.nav { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
a { text-decoration: none; color: #4f46e5; font-weight: 600; }
a.router-link-active { color: #1f2937; }
</style>
