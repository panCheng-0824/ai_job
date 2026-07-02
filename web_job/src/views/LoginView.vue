<script setup>
/**
 * 东华大学学生就业 AI 登录页：双栏布局 + 品牌标识 + 适度动效，不依赖外部图片。
 */
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { apiPost } from "../api/client";

const GRID_SIZE = 48;
const GRID_FADE_MS = 1000;

const router = useRouter();
const pageRef = ref(null);
const gridCanvas = ref(null);
const loginHeroUrl = ref("");

const loginHeroGlob = import.meta.glob("../assets/login-hero.png", {
  eager: false,
  import: "default"
});
const REMEMBER_KEY = "login_remember";
const PASSWORD_KEY = "login_password_hint";

const studentId = ref("");
const password = ref("");
const remember = ref(false);
const showPassword = ref(false);
const loading = ref(false);
const msg = ref("");
const isError = ref(false);
const pageReady = ref(false);
const focusField = ref("");

const heroFeatures = [
  { label: "简历上传", icon: "upload" },
  { label: "岗位检索", icon: "search" }
];

const heroCoreItems = [
  { label: "简历解析", icon: "parse" },
  { label: "岗位标签", icon: "tag" },
  { label: "智能匹配", icon: "match" }
];

const heroTracks = [
  { label: "应届生求职", icon: "grad" },
  { label: "实习招聘", icon: "intern" },
  { label: "社招择业", icon: "social" }
];

const heroStats = [
  { value: "AI", label: "多维度分析" },
  { value: "RAG", label: "知识库检索" },
  { value: "RTC", label: "实时推荐" }
];

let gridCells = new Map();
let gridAnimFrame = null;
let gridLastFrame = 0;
let gridReduceMotion = false;

function resizeGridCanvas() {
  const canvas = gridCanvas.value;
  if (!canvas) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = window.innerWidth;
  const h = window.innerHeight;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  const ctx = canvas.getContext("2d");
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  paintGridCanvas();
}

function igniteGridAt(clientX, clientY) {
  if (gridReduceMotion) return;
  const x = clientX;
  const y = clientY;
  const col = Math.floor(x / GRID_SIZE);
  const row = Math.floor(y / GRID_SIZE);

  for (let dc = -1; dc <= 1; dc += 1) {
    for (let dr = -1; dr <= 1; dr += 1) {
      const dist = Math.hypot(dc, dr);
      const intensity = 1 - dist * 0.32;
      if (intensity <= 0) continue;
      const key = `${col + dc},${row + dr}`;
      gridCells.set(key, Math.max(gridCells.get(key) || 0, intensity));
    }
  }
  ensureGridAnimLoop();
}

function ensureGridAnimLoop() {
  if (gridAnimFrame != null) return;
  gridLastFrame = performance.now();
  gridAnimFrame = requestAnimationFrame(animateGridCells);
}

function animateGridCells(now) {
  const dt = Math.min(now - gridLastFrame, 50);
  gridLastFrame = now;

  for (const [key, brightness] of gridCells.entries()) {
    const next = brightness - dt / GRID_FADE_MS;
    if (next <= 0.002) gridCells.delete(key);
    else gridCells.set(key, next);
  }

  paintGridCanvas();

  if (gridCells.size > 0) {
    gridAnimFrame = requestAnimationFrame(animateGridCells);
  } else {
    gridAnimFrame = null;
  }
}

function paintGridCanvas() {
  const canvas = gridCanvas.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const w = window.innerWidth;
  const h = window.innerHeight;
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(99, 102, 241, 0.045)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= w; x += GRID_SIZE) {
    ctx.beginPath();
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, h);
    ctx.stroke();
  }
  for (let y = 0; y <= h; y += GRID_SIZE) {
    ctx.beginPath();
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(w, y + 0.5);
    ctx.stroke();
  }

  for (const [key, brightness] of gridCells.entries()) {
    const [col, row] = key.split(",").map(Number);
    const x = col * GRID_SIZE;
    const y = row * GRID_SIZE;
    const cx = x + GRID_SIZE / 2;
    const cy = y + GRID_SIZE / 2;
    const alpha = brightness * 0.32;
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, GRID_SIZE * 0.72);
    grad.addColorStop(0, `rgba(99, 102, 241, ${alpha})`);
    grad.addColorStop(0.55, `rgba(129, 140, 248, ${alpha * 0.55})`);
    grad.addColorStop(1, `rgba(168, 85, 247, ${alpha * 0.08})`);
    ctx.fillStyle = grad;
    ctx.fillRect(x, y, GRID_SIZE, GRID_SIZE);
  }
}

function onPageMouseMove(event) {
  igniteGridAt(event.clientX, event.clientY);
}

function onPageTouchMove(event) {
  const touch = event.touches[0];
  if (touch) igniteGridAt(touch.clientX, touch.clientY);
}

async function loadLoginHeroBg() {
  const loader = loginHeroGlob["../assets/login-hero.png"];
  if (!loader) return;
  try {
    loginHeroUrl.value = await loader();
  } catch {
    loginHeroUrl.value = "";
  }
}

onMounted(() => {
  const remembered = localStorage.getItem(REMEMBER_KEY) === "1";
  remember.value = remembered;
  if (remembered) {
    studentId.value = localStorage.getItem("student_id") || "";
    password.value = sessionStorage.getItem(PASSWORD_KEY) || "";
  }
  gridReduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  loadLoginHeroBg();
  resizeGridCanvas();
  window.addEventListener("resize", resizeGridCanvas);
  window.addEventListener("mousemove", onPageMouseMove);
  window.addEventListener("touchmove", onPageTouchMove, { passive: true });
  requestAnimationFrame(() => {
    pageReady.value = true;
  });
});

onBeforeUnmount(() => {
  if (gridAnimFrame != null) cancelAnimationFrame(gridAnimFrame);
  window.removeEventListener("resize", resizeGridCanvas);
  window.removeEventListener("mousemove", onPageMouseMove);
  window.removeEventListener("touchmove", onPageTouchMove);
});

function persistRemember() {
  if (remember.value) {
    localStorage.setItem(REMEMBER_KEY, "1");
    if (password.value) sessionStorage.setItem(PASSWORD_KEY, password.value);
    else sessionStorage.removeItem(PASSWORD_KEY);
  } else {
    localStorage.removeItem(REMEMBER_KEY);
    sessionStorage.removeItem(PASSWORD_KEY);
  }
}

function showComingSoon(feature) {
  msg.value = `${feature}功能即将上线，请使用学号登录`;
  isError.value = false;
}

async function login() {
  if (!studentId.value.trim()) {
    msg.value = "请输入用户名（学号）";
    isError.value = true;
    return;
  }
  loading.value = true;
  msg.value = "";
  try {
    const data = await apiPost("/api/login", { student_id: studentId.value.trim() });
    const normalizedStudentId = String(data?.student_id || studentId.value.trim());
    localStorage.setItem("student_id", normalizedStudentId);
    persistRemember();
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
  <main
    ref="pageRef"
    class="login-page"
    :class="{ 'login-page--ready': pageReady, 'login-page--has-hero': !!loginHeroUrl }"
  >
    <div
      v-if="loginHeroUrl"
      class="login-bg-photo"
      :style="{ backgroundImage: `url(${loginHeroUrl})` }"
      aria-hidden="true"
    />
    <div v-if="loginHeroUrl" class="login-bg-scrim" aria-hidden="true" />
    <canvas ref="gridCanvas" class="login-grid-canvas" aria-hidden="true" />
    <div class="login-bg" aria-hidden="true">
      <span class="login-bg-orb login-bg-orb--1" />
      <span class="login-bg-orb login-bg-orb--2" />
      <span class="login-bg-orb login-bg-orb--3" />
    </div>

    <div class="login-shell">
      <section class="login-hero anim-block" style="--anim-delay: 0.05s">
        <div class="uni-brand">
          <div class="uni-emblem" aria-hidden="true">
            <svg viewBox="0 0 48 48" fill="none">
              <circle cx="24" cy="24" r="22" stroke="currentColor" stroke-width="1.5" opacity="0.25" />
              <circle cx="24" cy="24" r="17" fill="currentColor" opacity="0.08" />
              <text x="24" y="27" text-anchor="middle" font-size="11" font-weight="700" fill="currentColor">东华</text>
            </svg>
          </div>
          <div class="uni-copy">
            <p class="uni-name">东华大学</p>
            <p class="uni-en">Donghua University</p>
          </div>
        </div>

        <div class="hero-brand">
          <p class="hero-eyebrow">Student Employment Intelligence Platform</p>
          <h2 class="hero-title">学生就业 AI 智能匹配引擎</h2>
          <p class="hero-desc">
            面向东华大学全体学生的智能化就业服务平台，融合简历解析、岗位标签与多维度匹配，助力精准择业。
          </p>
        </div>

        <div class="hero-stats">
          <div v-for="(stat, i) in heroStats" :key="stat.label" class="hero-stat" :style="{ '--anim-delay': `${0.2 + i * 0.08}s` }">
            <span class="hero-stat-value">{{ stat.value }}</span>
            <span class="hero-stat-label">{{ stat.label }}</span>
          </div>
        </div>

        <div class="hero-visual">
          <div class="hero-pill-row">
            <span
              v-for="(item, i) in heroFeatures"
              :key="item.label"
              class="hero-pill anim-float"
              :style="{ '--float-delay': `${i * 0.6}s` }"
            >
              <svg class="hero-icon" viewBox="0 0 20 20" aria-hidden="true">
                <template v-if="item.icon === 'upload'">
                  <path d="M10 3v10M6 7l4-4 4 4" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" />
                  <path d="M4 14h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                </template>
                <template v-else>
                  <circle cx="8.5" cy="8.5" r="4.5" stroke="currentColor" stroke-width="1.6" fill="none" />
                  <path d="M12 12l4.5 4.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                </template>
              </svg>
              {{ item.label }}
            </span>
          </div>

          <div class="hero-card">
            <div class="hero-card-head">
              <span class="hero-card-head-shine" aria-hidden="true" />
              AI 多维度智能匹配
            </div>
            <div class="hero-card-grid">
              <div
                v-for="(item, i) in heroCoreItems"
                :key="item.label"
                class="hero-card-item anim-stagger"
                :style="{ '--anim-delay': `${0.35 + i * 0.1}s` }"
              >
                <span class="hero-card-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                    <rect x="5" y="3" width="14" height="18" rx="2" />
                    <path d="M9 8h6M9 12h6M9 16h4" stroke-linecap="round" />
                  </svg>
                </span>
                <span>{{ item.label }}</span>
              </div>
            </div>
          </div>

          <div class="hero-track-row">
            <span v-for="item in heroTracks" :key="item.label" class="hero-track">
              <span class="hero-track-dot" aria-hidden="true" />
              {{ item.label }}
            </span>
          </div>

          <div class="hero-api">
            <svg class="hero-icon" viewBox="0 0 20 20" aria-hidden="true">
              <ellipse cx="10" cy="5" rx="6" ry="2.5" stroke="currentColor" stroke-width="1.4" fill="none" />
              <path d="M4 5v6c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V5" stroke="currentColor" stroke-width="1.4" fill="none" />
              <path d="M4 11v3c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5v-3" stroke="currentColor" stroke-width="1.4" fill="none" />
            </svg>
            就业大数据 API
          </div>
        </div>
      </section>

      <section class="login-panel anim-block" style="--anim-delay: 0.18s">
        <div class="login-card">
          <header class="login-card-head">
            <h1 class="login-title">欢迎登录</h1>
            <p class="login-subtitle">东华大学 · 就业智能匹配平台</p>
          </header>

          <form class="login-form" @submit.prevent="login">
            <label
              class="input-shell"
              :class="{
                'input-shell--focus': focusField === 'username',
                'input-shell--error': isError && !studentId.trim()
              }"
            >
              <span class="input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <circle cx="12" cy="8" r="4" />
                  <path d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7" stroke-linecap="round" />
                </svg>
              </span>
              <input
                id="login-username"
                v-model="studentId"
                class="field"
                type="text"
                placeholder="用户名"
                autocomplete="username"
                @focus="focusField = 'username'"
                @blur="focusField = ''"
              />
            </label>

            <label
              class="input-shell input-shell--password"
              :class="{ 'input-shell--focus': focusField === 'password' }"
            >
              <span class="input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <rect x="5" y="11" width="14" height="10" rx="2" />
                  <path d="M8 11V8a4 4 0 1 1 8 0v3" stroke-linecap="round" />
                </svg>
              </span>
              <input
                id="login-password"
                v-model="password"
                class="field"
                :type="showPassword ? 'text' : 'password'"
                placeholder="密码"
                autocomplete="current-password"
                @focus="focusField = 'password'"
                @blur="focusField = ''"
              />
              <button
                type="button"
                class="password-toggle"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M3 3l18 18" />
                  <path d="M10.58 10.58A3 3 0 0 0 12 15a3 3 0 0 0 2.42-4.42" />
                  <path d="M9.88 5.09A10.94 10.94 0 0 1 12 5c6.5 0 10 7 10 7a17.8 17.8 0 0 1-3.17 4.12" />
                  <path d="M6.11 6.11A17.8 17.8 0 0 0 2 12s3.5 7 10 7a10.9 10.9 0 0 0 4.12-.89" />
                </svg>
              </button>
            </label>

            <div class="form-row">
              <label class="remember">
                <input v-model="remember" type="checkbox" class="remember-input" />
                <span class="remember-box" aria-hidden="true" />
                <span>记住密码</span>
              </label>
              <button type="button" class="link-btn" @click="showComingSoon('忘记密码')">忘记密码?</button>
            </div>

            <button type="submit" class="btn-primary" :class="{ 'btn-primary--loading': loading }" :disabled="loading">
              <span v-if="loading" class="btn-spinner" aria-hidden="true" />
              <span>{{ loading ? "登录中..." : "登 录" }}</span>
            </button>

            <Transition name="status-fade">
              <p v-if="msg" class="status" :class="isError ? 'error' : 'hint'">{{ msg }}</p>
            </Transition>
          </form>

          <div class="login-divider">
            <span>其他登录方式</span>
          </div>

          <div class="alt-login">
            <button type="button" class="btn-outline" @click="showComingSoon('手机号登录')">
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <rect x="6" y="2" width="8" height="16" rx="2" stroke="currentColor" stroke-width="1.4" fill="none" />
                <path d="M9 15h2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
              </svg>
              手机号登录
            </button>
            <button type="button" class="btn-outline" @click="showComingSoon('扫码登录')">
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <rect x="3" y="3" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.3" fill="none" />
                <rect x="11" y="3" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.3" fill="none" />
                <rect x="3" y="11" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.3" fill="none" />
                <path d="M11 14h2v2h2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
              </svg>
              扫码登录
            </button>
          </div>

          <div class="tips-box">
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <circle cx="10" cy="10" r="7.5" stroke="currentColor" stroke-width="1.4" fill="none" />
              <path d="M10 9v4M10 7h.01" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
            </svg>
            <span>测试学号：<strong>220692209</strong> / <strong>220692216</strong></span>
          </div>
        </div>

        <p class="login-footer">© 东华大学 · 学生就业指导中心</p>
      </section>
    </div>
  </main>
</template>

<style scoped>
.login-page {
  --dhu-red: #b5121b;
  --login-primary: var(--primary-color, #6366f1);
  --login-secondary: var(--secondary-color, #a855f7);
  --login-surface: rgba(255, 255, 255, 0.78);
  --login-border: rgba(99, 102, 241, 0.1);
  --login-radius: 12px;
  --login-shadow: 0 20px 50px rgba(99, 102, 241, 0.1), 0 4px 12px rgba(15, 23, 42, 0.04);
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);

  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 36px 24px;
  background: linear-gradient(165deg, #f8f6ff 0%, #faf9fc 40%, #ffffff 100%);
  overflow: hidden;
}

.login-page--has-hero {
  background: #f8f6ff;
}

.login-bg-photo {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.login-bg-scrim {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: linear-gradient(
    165deg,
    rgba(248, 246, 255, 0.78) 0%,
    rgba(250, 249, 252, 0.72) 42%,
    rgba(255, 255, 255, 0.68) 100%
  );
}

.login-grid-canvas {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  /* 全页可见，仅最外缘轻微淡出 */
  mask-image: radial-gradient(ellipse 130% 110% at 50% 50%, #000 88%, transparent 100%);
}

.login-bg {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

.login-bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.5;
  animation: orb-drift 18s ease-in-out infinite;
}

.login-bg-orb--1 {
  width: 440px;
  height: 440px;
  top: -100px;
  left: -80px;
  background: rgba(99, 102, 241, 0.16);
  animation-delay: 0s;
}

.login-bg-orb--2 {
  width: 380px;
  height: 380px;
  bottom: -120px;
  left: 25%;
  background: rgba(181, 18, 27, 0.08);
  animation-delay: -6s;
}

.login-bg-orb--3 {
  width: 300px;
  height: 300px;
  top: 18%;
  right: 6%;
  background: rgba(168, 85, 247, 0.1);
  animation-delay: -12s;
}

.login-shell {
  position: relative;
  z-index: 2;
  width: min(1240px, 100%);
  display: grid;
  grid-template-columns: minmax(520px, 1.4fr) minmax(260px, 320px);
  column-gap: clamp(72px, 10vw, 140px);
  align-items: center;
}

/* ── 入场动画 ── */
.anim-block {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.7s var(--ease-out), transform 0.7s var(--ease-out);
  transition-delay: var(--anim-delay, 0s);
}

.login-page--ready .anim-block {
  opacity: 1;
  transform: translateY(0);
}

.anim-stagger {
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.5s var(--ease-out), transform 0.5s var(--ease-out);
  transition-delay: var(--anim-delay, 0s);
}

.login-page--ready .anim-stagger {
  opacity: 1;
  transform: translateY(0);
}

.anim-float {
  animation: pill-float 4s ease-in-out infinite;
  animation-delay: var(--float-delay, 0s);
}

/* ── 东华大学品牌 ── */
.uni-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
}

.uni-emblem {
  width: 52px;
  height: 52px;
  color: var(--dhu-red);
  flex-shrink: 0;
  animation: emblem-glow 4s ease-in-out infinite;
}

.uni-emblem svg {
  width: 100%;
  height: 100%;
}

.uni-name {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--dhu-red);
  letter-spacing: 0.06em;
}

.uni-en {
  margin: 2px 0 0;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: var(--text-muted, #6b7280);
  text-transform: uppercase;
}

/* ── 左侧品牌区 ── */
.login-hero {
  display: flex;
  flex-direction: column;
  gap: 24px;
  justify-self: start;
  width: 100%;
  max-width: 640px;
}

.hero-eyebrow {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--login-primary);
  opacity: 0.7;
}

.hero-title {
  margin: 0;
  font-size: clamp(28px, 3.4vw, 36px);
  font-weight: 800;
  line-height: 1.28;
  letter-spacing: -0.02em;
  background: linear-gradient(100deg, #312e81 0%, var(--login-primary) 45%, var(--login-secondary) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-desc {
  margin: 12px 0 0;
  font-size: 15px;
  line-height: 1.75;
  color: var(--text-muted, #6b7280);
  max-width: 56ch;
}

.hero-stats {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-stat {
  flex: 1;
  min-width: 90px;
  padding: 12px 14px;
  border-radius: var(--login-radius);
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid var(--login-border);
  backdrop-filter: blur(8px);
  transition: transform 0.25s var(--ease-out), box-shadow 0.25s;
}

.hero-stat:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.1);
}

.hero-stat-value {
  display: block;
  font-size: 18px;
  font-weight: 800;
  color: var(--login-primary);
  letter-spacing: -0.02em;
}

.hero-stat-label {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted, #6b7280);
}

.hero-visual {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  padding: 24px;
  border-radius: 20px;
  background: var(--login-surface);
  border: 1px solid var(--login-border);
  backdrop-filter: blur(16px);
  box-shadow: var(--login-shadow);
  transition: box-shadow 0.3s;
}

.hero-visual:hover {
  box-shadow: 0 24px 56px rgba(99, 102, 241, 0.12), 0 4px 12px rgba(15, 23, 42, 0.05);
}

.hero-pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 15px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--login-primary), #818cf8);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.28);
  transition: transform 0.2s, box-shadow 0.2s;
}

.hero-pill:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
}

.hero-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.hero-card {
  border-radius: var(--login-radius);
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid var(--login-border);
  overflow: hidden;
}

.hero-card-head {
  position: relative;
  overflow: hidden;
  padding: 12px 16px;
  background: linear-gradient(90deg, #eef2ff, #faf5ff);
  color: #4338ca;
  font-size: 14px;
  font-weight: 700;
  text-align: center;
}

.hero-card-head-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 60%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.55), transparent);
  animation: head-shine 5s ease-in-out infinite;
}

.hero-card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 16px;
}

.hero-card-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted, #6b7280);
  text-align: center;
  transition: color 0.2s;
}

.hero-card-item:hover {
  color: var(--login-primary);
}

.hero-card-item:hover .hero-card-icon {
  transform: scale(1.06);
  background: linear-gradient(145deg, #e0e7ff, #c7d2fe);
}

.hero-card-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: linear-gradient(145deg, #eef2ff, #e0e7ff);
  color: var(--login-primary);
  transition: transform 0.25s var(--ease-out), background 0.25s;
}

.hero-card-icon svg {
  width: 20px;
  height: 20px;
}

.hero-track-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  justify-content: center;
}

.hero-track {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted, #6b7280);
}

.hero-track-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--dhu-red), #e11d48);
  flex-shrink: 0;
  animation: dot-pulse 2.5s ease-in-out infinite;
}

.hero-track:nth-child(2) .hero-track-dot { animation-delay: 0.4s; }
.hero-track:nth-child(3) .hero-track-dot { animation-delay: 0.8s; }

.hero-api {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  align-self: center;
  padding: 10px 20px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid var(--login-border);
  font-size: 13px;
  font-weight: 600;
  color: #4338ca;
  transition: border-color 0.2s, transform 0.2s;
}

.hero-api:hover {
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateY(-1px);
}

/* ── 右侧登录表单 ── */
.login-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  justify-self: end;
}

.login-card {
  position: relative;
  width: 100%;
  max-width: 320px;
  background: #fff;
  border: 1px solid rgba(99, 102, 241, 0.07);
  border-radius: 16px;
  box-shadow:
    0 16px 36px rgba(99, 102, 241, 0.08),
    0 4px 10px rgba(15, 23, 42, 0.03);
  padding: 26px 24px 20px;
  overflow: hidden;
  transition: box-shadow 0.35s var(--ease-out);
}

.login-card:hover {
  box-shadow:
    0 20px 40px rgba(99, 102, 241, 0.1),
    0 6px 14px rgba(15, 23, 42, 0.04);
}

.login-card-head {
  margin-bottom: 20px;
}

.login-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--text-main, #1f2937);
  letter-spacing: 0.01em;
}

.login-subtitle {
  margin: 5px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--text-muted, #6b7280);
}

.login-form {
  display: grid;
  gap: 11px;
}

.input-shell {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 11px;
  border: 1px solid #e8eaef;
  border-radius: 10px;
  background: #fafbfc;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.input-shell:hover {
  border-color: #d8dce6;
  background: #fff;
}

.input-shell--focus {
  border-color: var(--login-primary);
  background: #fff;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.09);
}

.input-shell--focus .input-icon {
  color: var(--login-primary);
}

.input-shell--error {
  border-color: #fca5a5;
  background: #fffafb;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.08);
}

.input-shell--error .input-icon {
  color: var(--danger, #dc2626);
}

.input-shell--password {
  padding-right: 6px;
}

.input-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: #9ca3af;
  transition: color 0.2s;
}

.input-icon svg {
  width: 16px;
  height: 16px;
}

.field {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 11px 0;
  font-size: 14px;
  color: var(--text-main, #1f2937);
  outline: none;
}

.field::placeholder {
  color: #a1a9b8;
}

.password-toggle {
  border: none;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  padding: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: color 0.15s, background 0.15s;
}

.password-toggle:hover {
  color: var(--login-primary);
  background: rgba(99, 102, 241, 0.06);
}

.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 2px;
}

.remember {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted, #6b7280);
  cursor: pointer;
  user-select: none;
}

.remember-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.remember-box {
  width: 14px;
  height: 14px;
  border: 1.5px solid #d1d5db;
  border-radius: 3px;
  background: #fff;
  transition: border-color 0.15s, background 0.15s;
  position: relative;
}

.remember-input:checked + .remember-box {
  border-color: var(--login-primary);
  background: var(--login-primary);
}

.remember-input:checked + .remember-box::after {
  content: "";
  position: absolute;
  left: 3px;
  top: 0;
  width: 4px;
  height: 8px;
  border: 2px solid #fff;
  border-top: none;
  border-left: none;
  transform: rotate(45deg);
}

.remember:hover .remember-box {
  border-color: #a5b4fc;
}

.link-btn {
  border: none;
  background: transparent;
  color: var(--login-primary);
  font-size: 12px;
  cursor: pointer;
  padding: 0;
  transition: color 0.15s;
}

.link-btn:hover {
  color: #4f46e5;
  text-decoration: underline;
}

.btn-primary {
  position: relative;
  width: 100%;
  margin-top: 4px;
  border: none;
  border-radius: 10px;
  padding: 11px 14px;
  background: linear-gradient(135deg, #5b67f0 0%, var(--login-primary) 50%, #4f46e5 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.1em;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  overflow: hidden;
  transition: transform 0.15s, box-shadow 0.2s, opacity 0.15s;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.26);
}

.btn-primary::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(105deg, transparent 40%, rgba(255, 255, 255, 0.2) 50%, transparent 60%);
  transform: translateX(-100%);
  transition: transform 0.55s;
}

.btn-primary:hover:not(:disabled)::before {
  transform: translateX(100%);
}

.btn-primary:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.36);
  transform: translateY(-1px);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0) scale(0.99);
}

.btn-primary:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.btn-primary--loading {
  pointer-events: none;
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.status {
  margin: 0;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
}

.status.error {
  color: #b91c1c;
  font-weight: 600;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.status.hint {
  color: var(--text-muted, #6b7280);
  background: #f9fafb;
  border: 1px solid #f3f4f6;
}

.status-fade-enter-active,
.status-fade-leave-active {
  transition: opacity 0.25s, transform 0.25s var(--ease-out);
}

.status-fade-enter-from,
.status-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.login-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 18px 0 12px;
  color: #9ca3af;
  font-size: 11px;
}

.login-divider::before,
.login-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
}

.alt-login {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border: 1px solid #e8eaef;
  border-radius: 10px;
  padding: 8px 6px;
  background: #fafbfc;
  color: #4b5563;
  font-size: 11px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, transform 0.15s, color 0.2s, box-shadow 0.2s;
}

.btn-outline svg {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  opacity: 0.7;
}

.btn-outline:hover {
  border-color: #c7d2fe;
  background: #f5f7ff;
  color: var(--login-primary);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
}

.btn-outline:hover svg {
  opacity: 1;
}

.tips-box {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 14px;
  padding: 8px 10px;
  border-radius: 8px;
  background: linear-gradient(135deg, #f8f9ff, #faf5ff);
  border: 1px solid rgba(99, 102, 241, 0.08);
  font-size: 11px;
  line-height: 1.45;
  color: #6b7280;
}

.tips-box svg {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--login-primary);
  opacity: 0.8;
}

.tips-box strong {
  color: #4338ca;
  font-weight: 600;
}

.login-footer {
  margin: 0;
  width: 100%;
  max-width: 320px;
  padding-top: 2px;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.03em;
  color: #b0b7c3;
  text-align: center;
}

/* ── 关键帧 ── */
@keyframes orb-drift {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(24px, -18px) scale(1.04); }
  66% { transform: translate(-16px, 12px) scale(0.97); }
}

@keyframes pill-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

@keyframes head-shine {
  0%, 100% { left: -100%; }
  50% { left: 140%; }
}

@keyframes emblem-glow {
  0%, 100% { filter: drop-shadow(0 0 0 transparent); }
  50% { filter: drop-shadow(0 0 8px rgba(181, 18, 27, 0.25)); }
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .login-bg-orb,
  .anim-float,
  .hero-card-head-shine,
  .uni-emblem,
  .hero-track-dot,
  .btn-spinner {
    animation: none;
  }

  .anim-block,
  .anim-stagger {
    opacity: 1;
    transform: none;
    transition: none;
  }
}

@media (max-width: 1024px) {
  .login-shell {
    grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
    column-gap: clamp(48px, 8vw, 96px);
  }

  .login-hero {
    max-width: 100%;
  }
}

@media (max-width: 900px) {
  .login-shell {
    grid-template-columns: 1fr;
    max-width: 400px;
    column-gap: 0;
    gap: 24px;
  }

  .login-card,
  .login-footer {
    max-width: 340px;
  }

  .login-hero {
    justify-self: center;
    max-width: none;
    text-align: center;
    align-items: center;
  }

  .login-panel {
    justify-self: center;
  }

  .uni-brand {
    justify-content: center;
  }

  .hero-desc {
    max-width: none;
  }

  .hero-stats {
    width: 100%;
  }

  .hero-visual {
    padding: 18px;
    width: 100%;
  }
}

@media (max-width: 480px) {
  .login-page {
    padding: 24px 16px;
  }

  .login-card {
    padding: 24px 20px 18px;
    max-width: 100%;
  }

  .login-footer {
    max-width: 100%;
  }

  .login-title {
    font-size: 20px;
  }

  .hero-stats {
    flex-direction: column;
  }

  .hero-card-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .hero-card-item {
    flex-direction: row;
    justify-content: flex-start;
  }

  .alt-login {
    grid-template-columns: 1fr;
  }
}
</style>
