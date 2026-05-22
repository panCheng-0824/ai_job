<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { apiPost } from "../api/client";

const router = useRouter();
const studentId = ref(localStorage.getItem("student_id") || "");
const loading = ref(false);
const msg = ref("");
const isError = ref(false);

async function login() {
  if (!studentId.value.trim()) {
    msg.value = "请输入 student_id";
    isError.value = true;
    return;
  }
  loading.value = true;
  try {
    const data = await apiPost("/api/login", { student_id: studentId.value.trim() });
    const normalizedStudentId = String(data?.student_id || studentId.value.trim());
    localStorage.setItem("student_id", normalizedStudentId);
    router.push("/student");
  } catch (err) {
    msg.value = err.message;
    isError.value = true;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="wrap">
    <section class="card">
      <h1>欢迎登录</h1>
      <p class="desc">输入你的学号继续使用学生就业助手。</p>
      <div class="field-wrap">
        <input v-model="studentId" class="field" placeholder="例如 220692209" @keydown.enter.prevent="login" />
        <button class="btn" :disabled="loading" @click="login">{{ loading ? "登录中..." : "登录" }}</button>
      </div>
      <p class="tips">测试账号：220692209 / 220692216。</p>
      <p class="status" :class="isError ? 'error' : 'ok'">{{ msg }}</p>
      <p class="footer">Student Portal</p>
    </section>
  </main>
</template>

<style scoped>
.wrap {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 15% 20%, rgba(0, 113, 227, 0.13), transparent 42%),
    radial-gradient(circle at 88% 80%, rgba(52, 199, 89, 0.12), transparent 46%),
    #f5f5f7;
}
.card {
  width: min(560px, 100%);
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 24px;
  backdrop-filter: blur(14px);
  box-shadow: 0 20px 44px rgba(0, 0, 0, 0.08);
  padding: 34px 30px 26px;
}
h1 { margin: 0; font-size: clamp(30px, 4vw, 42px); letter-spacing: -0.03em; }
.desc { margin: 10px 0 22px; color: #6e6e73; line-height: 1.5; }
.field-wrap { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; }
.field { border: 1px solid #d2d2d7; border-radius: 14px; padding: 13px 14px; font-size: 16px; background: #fff; }
.btn { border: none; border-radius: 999px; padding: 12px 22px; background: #0071e3; color: #fff; font-size: 15px; font-weight: 600; cursor: pointer; min-width: 112px; }
.tips { margin-top: 14px; font-size: 13px; color: #6e6e73; }
.status { min-height: 22px; margin-top: 12px; font-size: 14px; font-weight: 600; }
.status.error { color: #d70015; }
.status.ok { color: #068740; }
.footer { margin-top: 18px; font-size: 12px; color: #6e6e73; }
</style>
