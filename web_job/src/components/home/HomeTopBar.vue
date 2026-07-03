<script setup>
/**
 * 登录后页内顶栏：展示标题、副标题与快捷入口（岗位搜索）。
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const props = defineProps({
  title: { type: String, default: "" },
  subtitle: { type: String, default: "" },
  studentName: { type: String, default: "" }
});

const router = useRouter();
const orbCharging = ref(false);
const orbCharged = ref(false);
const orbAnim = ref("");
const orbAnimNonce = ref(0);
let pressTimer = null;
let pressed = false;
let idleRollTimer = null;
const lastInteractionAt = ref(Date.now());

const greeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 12) return "上午好";
  if (hour < 18) return "下午好";
  return "晚上好";
});

const displaySubtitle = computed(() => {
  if (props.subtitle) return props.subtitle;
  if (props.studentName) return `${greeting.value}，${props.studentName}，祝你求职顺利`;
  return `${greeting.value}，祝你求职顺利`;
});

const todayText = computed(() => {
  const d = new Date();
  const week = ["日", "一", "二", "三", "四", "五", "六"][d.getDay()];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 · 周${week}`;
});

function goJobs() {
  router.push("/jobs");
}

function clearPressTimer() {
  if (pressTimer) {
    clearTimeout(pressTimer);
    pressTimer = null;
  }
}

function restartOrbAnimation(name) {
  orbAnim.value = "";
  orbAnimNonce.value += 1;
  requestAnimationFrame(() => {
    orbAnim.value = name;
  });
}

function onOrbPointerDown() {
  lastInteractionAt.value = Date.now();
  pressed = true;
  orbCharging.value = false;
  orbCharged.value = false;
  clearPressTimer();
  pressTimer = setTimeout(() => {
    if (!pressed) return;
    orbCharging.value = true;
    orbCharged.value = true;
  }, 520);
}

function onOrbPointerUp() {
  lastInteractionAt.value = Date.now();
  if (!pressed) return;
  pressed = false;
  clearPressTimer();
  if (orbCharged.value) {
    orbCharging.value = false;
    orbCharged.value = false;
    restartOrbAnimation("top-bar-orb--launch");
    return;
  }
  orbCharging.value = false;
  restartOrbAnimation("top-bar-orb--roll");
}

function onOrbPointerCancel() {
  lastInteractionAt.value = Date.now();
  pressed = false;
  orbCharging.value = false;
  orbCharged.value = false;
  clearPressTimer();
}

onBeforeUnmount(() => {
  clearPressTimer();
  if (idleRollTimer) {
    clearInterval(idleRollTimer);
    idleRollTimer = null;
  }
});

onMounted(() => {
  idleRollTimer = setInterval(() => {
    if (pressed || orbCharging.value || document.hidden) return;
    const idleFor = Date.now() - lastInteractionAt.value;
    if (idleFor < 5000) return;
    lastInteractionAt.value = Date.now();
    restartOrbAnimation("top-bar-orb--roll");
  }, 1000);
});
</script>

<template>
  <header class="home-top-bar" aria-label="页面顶栏">
    <div class="top-bar-main">
      <div class="top-bar-brand">
        <span class="top-bar-kicker">智慧就业</span>
      </div>
      <div class="top-bar-titles">
        <h1>{{ title }}</h1>
        <p v-if="displaySubtitle">{{ displaySubtitle }}</p>
      </div>
      <div class="top-bar-orb-lane" aria-label="顶部互动球">
        <button
          :key="orbAnimNonce"
          type="button"
          class="top-bar-orb"
          :class="[orbAnim, { 'top-bar-orb--charging': orbCharging }]"
          title="点击滚动，长按蓄力后反弹"
          @pointerdown="onOrbPointerDown"
          @pointerup="onOrbPointerUp"
          @pointercancel="onOrbPointerCancel"
          @pointerleave="onOrbPointerCancel"
        />
      </div>
      <div class="top-bar-actions">
        <span class="top-bar-date">{{ todayText }}</span>
        <button type="button" class="top-bar-btn" @click="goJobs">岗位搜索</button>
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<style scoped>
.home-top-bar {
  position: sticky;
  top: 0;
  z-index: 30;
  isolation: isolate;
  flex-shrink: 0;
  margin: 0 calc(-1 * var(--home-main-px, 20px)) 0;
  padding: 0 var(--home-main-px, 20px);
  background: rgba(255, 255, 255, 0.76);
  border-bottom: 1px solid rgba(91, 106, 223, 0.1);
  backdrop-filter: blur(14px);
  box-shadow: 0 6px 20px rgba(91, 106, 223, 0.08);
}
.top-bar-main {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 16px;
  min-height: var(--home-topbar-h, 56px);
  padding: 10px 0;
}
.top-bar-brand {
  flex-shrink: 0;
}
.top-bar-kicker {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: linear-gradient(135deg, #5b6adf, #7c86ff);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  box-shadow: 0 4px 12px rgba(91, 106, 223, 0.22);
}
.top-bar-titles {
  min-width: 0;
  flex: 1;
}
.top-bar-titles h1 {
  margin: 0;
  font-size: 1.08rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
}
.top-bar-titles p {
  margin: 4px 0 0;
  font-size: 0.77rem;
  color: #6b7280;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.top-bar-orb-lane {
  flex: 1;
  min-width: 120px;
  height: 24px;
  position: relative;
  overflow: visible;
}
.top-bar-orb {
  position: absolute;
  left: 0;
  top: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: radial-gradient(circle at 30% 30%, #f8fafc 0%, #cbd5e1 45%, #94a3b8 100%);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.18);
  cursor: pointer;
  transform: rotate(0deg);
  transition: background 0.22s ease, box-shadow 0.22s ease;
}
.top-bar-orb::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 16px;
  width: 24px;
  height: 9px;
  transform: translateX(-50%) scale(0.85, 0.65);
  border-radius: 999px;
  background: radial-gradient(ellipse at center, rgba(71, 85, 105, 0.32) 0%, rgba(71, 85, 105, 0.12) 55%, rgba(71, 85, 105, 0) 100%);
  filter: blur(2.2px);
  opacity: 0;
  pointer-events: none;
}
.top-bar-orb--charging {
  background: radial-gradient(circle at 30% 30%, #64748b 0%, #1f2937 45%, #020617 100%);
  box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.1), 0 3px 10px rgba(2, 6, 23, 0.45);
}
.top-bar-orb--roll {
  animation: orb-roll-coast 6.8s cubic-bezier(0.18, 0.86, 0.22, 1) both;
}
.top-bar-orb--roll::after {
  animation: orb-trail-roll 6.8s cubic-bezier(0.18, 0.86, 0.22, 1) both;
}
.top-bar-orb--launch {
  animation: orb-launch-bounce 9.2s cubic-bezier(0.16, 0.9, 0.22, 1) both;
}
.top-bar-orb--launch::after {
  animation: orb-trail-launch 9.2s cubic-bezier(0.16, 0.9, 0.22, 1) both;
}
@keyframes orb-roll-coast {
  0% {
    left: 0;
    transform: rotate(0deg);
  }
  20% {
    left: calc(100% - 20px);
    transform: rotate(300deg);
  }
  /* 回程滚动 1 */
  36% {
    left: calc(100% - 82px);
    transform: rotate(560deg);
  }
  49% {
    left: calc(100% - 34px);
    transform: rotate(760deg);
  }
  /* 回程滚动 2 */
  63% {
    left: calc(100% - 68px);
    transform: rotate(940deg);
  }
  76% {
    left: calc(100% - 38px);
    transform: rotate(1090deg);
  }
  /* 回程滚动 3 */
  88% {
    left: calc(100% - 56px);
    transform: rotate(1210deg);
  }
  100% {
    left: calc(100% - 34px);
    transform: rotate(1300deg);
  }
}
@keyframes orb-launch-bounce {
  0% {
    left: 0;
    transform: rotate(0deg);
  }
  10% {
    left: -62px;
    transform: rotate(-220deg);
  }
  20% {
    left: calc(100% - 16px);
    transform: rotate(120deg);
  }
  /* 回程滚动 1 */
  30% {
    left: calc(100% - 90px);
    transform: rotate(340deg);
  }
  40% {
    left: calc(100% - 26px);
    transform: rotate(520deg);
  }
  /* 回程滚动 2 */
  50% {
    left: calc(100% - 78px);
    transform: rotate(700deg);
  }
  59% {
    left: calc(100% - 30px);
    transform: rotate(840deg);
  }
  /* 回程滚动 3 */
  68% {
    left: calc(100% - 66px);
    transform: rotate(980deg);
  }
  76% {
    left: calc(100% - 32px);
    transform: rotate(1090deg);
  }
  /* 回程滚动 4 */
  84% {
    left: calc(100% - 56px);
    transform: rotate(1200deg);
  }
  91% {
    left: calc(100% - 34px);
    transform: rotate(1280deg);
  }
  /* 回程滚动 5 */
  97% {
    left: calc(100% - 48px);
    transform: rotate(1340deg);
  }
  100% {
    left: calc(100% - 36px);
    transform: rotate(1380deg);
  }
}
@keyframes orb-trail-roll {
  0% {
    opacity: 0;
    transform: translateX(-50%) scale(0.82, 0.62);
    filter: blur(2.1px);
  }
  6% {
    opacity: 0.52;
    transform: translateX(-50%) scale(1.18, 0.72);
  }
  44% {
    opacity: 0.48;
    transform: translateX(-50%) scale(1.35, 0.68);
  }
  72% {
    opacity: 0.34;
    transform: translateX(-50%) scale(1.08, 0.64);
  }
  100% {
    opacity: 0;
    transform: translateX(-50%) scale(0.88, 0.6);
    filter: blur(2.5px);
  }
}
@keyframes orb-trail-launch {
  0% {
    opacity: 0.1;
    transform: translateX(-50%) scale(0.8, 0.6);
    filter: blur(2px);
  }
  22% {
    opacity: 0.68;
    transform: translateX(-50%) scale(1.58, 0.78);
  }
  52% {
    opacity: 0.56;
    transform: translateX(-50%) scale(1.28, 0.7);
  }
  78% {
    opacity: 0.32;
    transform: translateX(-50%) scale(1.02, 0.64);
  }
  100% {
    opacity: 0;
    transform: translateX(-50%) scale(0.86, 0.58);
    filter: blur(2.6px);
  }
}
.top-bar-date {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.22);
  font-size: 0.74rem;
  color: #64748b;
  white-space: nowrap;
}
.top-bar-btn {
  border: 1px solid #c7d2fe;
  border-radius: 10px;
  padding: 6px 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f8faff 100%);
  color: #4338ca;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}
.top-bar-btn:hover {
  background: #eef2ff;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(99, 102, 241, 0.16);
}
@media (max-width: 720px) {
  .home-top-bar {
    margin-left: -10px;
    margin-right: -10px;
    padding: 0 10px 0 52px;
    margin-bottom: 0;
  }
  .top-bar-kicker {
    display: none;
  }
  .top-bar-date {
    display: none;
  }
  .top-bar-orb-lane { min-width: 72px; }
  .top-bar-btn {
    padding: 6px 10px;
    font-size: 0.72rem;
  }
}
</style>
