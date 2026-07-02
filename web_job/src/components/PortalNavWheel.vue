<script setup>
/**
 * 左下角浮动导航：圆形扇形花瓣展开 + 可拖动中心触发钮。
 * 悬停/点击中心按钮后，入口沿左上方弧线弹出；点击入口在 iframe 浮层中打开。
 */
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import FloatingFramePanel from "./FloatingFramePanel.vue";

const route = useRoute();

/** 扇形宿主尺寸（入口 ≥8 时略放大，避免花瓣重叠） */
const HOST_W = 256;
const HOST_H = 256;
const PAD = 8;
const LS_LEFT = "portal_nav_wheel_left";
const LS_BOTTOM = "portal_nav_wheel_bottom";
const LS_HIDDEN = "portal_nav_wheel_trigger_hidden";

const hostOpen = ref(false);
const frameOpen = ref(false);
const frameFullscreen = ref(false);
const iframeSrc = ref("");
const frameTitle = ref("");

const posLeft = ref(48);
const posBottom = ref(48);
const triggerHidden = ref(false);
const hotCornerHover = ref(false);
const suppressNextClick = ref(false);
const isDraggingWheel = ref(false);

/** @type {{ pointerId: number; startX: number; startY: number; origL: number; origB: number; dragging: boolean } | null} */
let dragState = null;

/** 快捷入口列表；顺序决定扇形上的排列位置 */
const items = [
  { path: "/student", label: "学生主页" },
  { path: "/resume/create", label: "我的简历" },
  { path: "/jobs", label: "岗位列表" },
  { path: "/companies", label: "企业列表" },
  { path: "/student-chat", label: "AI助手" },
  { path: "/interview/center", label: "面试中心" },
  { path: "/interview/industry", label: "面试分类" },
  { path: "/interview/categories", label: "行业字典" },
  { path: "/me", label: "我的" },
  { path: "/tools", label: "工具" }
];

/** 入口多时拉宽弧线并增大半径，减少花瓣挤在一起 */
const wheelMetrics = computed(() => {
  const n = items.length;
  if (n <= 7) {
    return { arcStart: 30, arcEnd: 150, petalR: 60, dialSize: 158, centerX: 116, centerY: 102 };
  }
  return { arcStart: 20, arcEnd: 168, petalR: 70, dialSize: 174, centerX: 128, centerY: 112 };
});

/** 花瓣沿左上方弧线均匀分布 */
const petalAngles = computed(() => {
  const n = items.length;
  const { arcStart, arcEnd } = wheelMetrics.value;
  if (n <= 1) return [90];
  return items.map((_, i) => arcStart + ((arcEnd - arcStart) * i) / (n - 1));
});

const isEmbed = computed(() => route.query._embed === "1");

const wheelHostStyle = computed(() => {
  const m = wheelMetrics.value;
  return {
    left: `${Math.round(posLeft.value)}px`,
    bottom: `${Math.round(posBottom.value)}px`,
    width: `${HOST_W}px`,
    height: `${HOST_H}px`,
    "--portal-wheel-center-x": `${m.centerX}px`,
    "--portal-wheel-center-y": `${m.centerY}px`,
    "--portal-wheel-petal-r": `${m.petalR}px`,
    "--portal-wheel-dial-size": `${m.dialSize}px`
  };
});

const isDense = computed(() => items.length > 7);

/** 路由 → 导航项 key，用于高亮当前页 */
function pathKey(pathname) {
  const p = pathname || "";
  if (p.startsWith("/student-chat")) return "/student-chat";
  if (p === "/student") return "/student";
  if (p.startsWith("/resume")) return "/resume/create";
  if (p.startsWith("/me/interviews/")) return "/interview/center";
  if (p.startsWith("/interview/center")) return "/interview/center";
  if (p.startsWith("/interview/plans") || p.startsWith("/interview/industry")) return "/interview/industry";
  if (p.startsWith("/interview/categories")) return "/interview/categories";
  if (p.startsWith("/jobs")) return "/jobs";
  if (p.startsWith("/companies")) return "/companies";
  if (p.startsWith("/me")) return "/me";
  if (p === "/tools" || p === "/data-search" || p === "/ai-search" || p === "/ocr") return "/tools";
  return "";
}

function embedUrl(path) {
  const u = new URL(path, window.location.origin);
  u.searchParams.set("_embed", "1");
  return u.pathname + u.search + u.hash;
}

function closeFrame() {
  frameOpen.value = false;
  frameFullscreen.value = false;
  iframeSrc.value = "";
}

function openFrame(path, label) {
  const key = pathKey(path);
  const cur = pathKey(route.path);
  if (key === cur && !isEmbed.value) {
    closeFrame();
    hostOpen.value = false;
    return;
  }
  frameTitle.value = label;
  iframeSrc.value = embedUrl(path);
  frameOpen.value = true;
  frameFullscreen.value = false;
  hostOpen.value = false;
}

function toggleFullscreen() {
  frameFullscreen.value = !frameFullscreen.value;
}

function openFullWindow() {
  if (!iframeSrc.value) return;
  const u = new URL(iframeSrc.value, window.location.origin);
  u.searchParams.delete("_embed");
  const href = u.pathname + u.search + u.hash;
  window.open(href, "_blank", "noopener,noreferrer");
}

function readNumberLs(key, fallback) {
  try {
    const n = parseInt(localStorage.getItem(key) || "", 10);
    return Number.isFinite(n) ? n : fallback;
  } catch (_) {
    return fallback;
  }
}

/** 保证扇形区域不超出视口 */
function clampWheel() {
  const maxL = Math.max(PAD, window.innerWidth - HOST_W - PAD);
  const maxB = Math.max(PAD, window.innerHeight - HOST_H - PAD);
  posLeft.value = Math.min(Math.max(PAD, posLeft.value), maxL);
  posBottom.value = Math.min(Math.max(PAD, posBottom.value), maxB);
}

function loadWheelLayout() {
  posLeft.value = readNumberLs(LS_LEFT, 48);
  posBottom.value = readNumberLs(LS_BOTTOM, 48);
  try {
    triggerHidden.value = localStorage.getItem(LS_HIDDEN) === "1";
  } catch (_) {
    triggerHidden.value = false;
  }
  clampWheel();
}

function saveWheelPosition() {
  try {
    localStorage.setItem(LS_LEFT, String(Math.round(posLeft.value)));
    localStorage.setItem(LS_BOTTOM, String(Math.round(posBottom.value)));
  } catch (_) {
    /* ignore */
  }
}

function hideTrigger() {
  triggerHidden.value = true;
  hostOpen.value = false;
  try {
    localStorage.setItem(LS_HIDDEN, "1");
  } catch (_) {
    /* ignore */
  }
}

function restoreTrigger() {
  triggerHidden.value = false;
  hotCornerHover.value = false;
  try {
    localStorage.removeItem(LS_HIDDEN);
  } catch (_) {
    /* ignore */
  }
}

function onWheelResize() {
  clampWheel();
}

function onWheelStorage(e) {
  if (e.storageArea !== localStorage || !e.key) return;
  if (e.key === LS_LEFT && e.newValue != null) {
    const n = parseInt(e.newValue, 10);
    if (Number.isFinite(n)) posLeft.value = n;
  }
  if (e.key === LS_BOTTOM && e.newValue != null) {
    const n = parseInt(e.newValue, 10);
    if (Number.isFinite(n)) posBottom.value = n;
  }
  if (e.key === LS_HIDDEN) {
    triggerHidden.value = e.newValue === "1";
  }
}

function onDocKey(ev) {
  if (ev.key === "Escape") {
    closeFrame();
    hostOpen.value = false;
  }
}

function onHostMouseLeave() {
  if (!isDraggingWheel.value) hostOpen.value = false;
}

function onTriggerMouseEnter() {
  if (!isDraggingWheel.value) hostOpen.value = true;
}

function onTriggerClick() {
  if (suppressNextClick.value) {
    suppressNextClick.value = false;
    return;
  }
  hostOpen.value = !hostOpen.value;
}

function onTriggerPointerDown(e) {
  if (e.button !== 0) return;
  dragState = {
    pointerId: e.pointerId,
    startX: e.clientX,
    startY: e.clientY,
    origL: posLeft.value,
    origB: posBottom.value,
    dragging: false
  };
  window.addEventListener("pointermove", onTriggerPointerMove);
  window.addEventListener("pointerup", onTriggerPointerUp);
  window.addEventListener("pointercancel", onTriggerPointerUp);
}

function onTriggerPointerMove(e) {
  if (!dragState || e.pointerId !== dragState.pointerId) return;
  const dx = e.clientX - dragState.startX;
  const dy = dragState.startY - e.clientY;
  if (!dragState.dragging && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
    dragState.dragging = true;
    isDraggingWheel.value = true;
    hostOpen.value = false;
  }
  if (dragState.dragging) {
    posLeft.value = dragState.origL + dx;
    posBottom.value = dragState.origB + dy;
    clampWheel();
  }
}

function onTriggerPointerUp(e) {
  if (!dragState || e.pointerId !== dragState.pointerId) return;
  window.removeEventListener("pointermove", onTriggerPointerMove);
  window.removeEventListener("pointerup", onTriggerPointerUp);
  window.removeEventListener("pointercancel", onTriggerPointerUp);
  const wasDrag = dragState.dragging;
  dragState = null;
  isDraggingWheel.value = false;
  if (wasDrag) {
    saveWheelPosition();
    suppressNextClick.value = true;
  }
}

function teardownDragListeners() {
  window.removeEventListener("pointermove", onTriggerPointerMove);
  window.removeEventListener("pointerup", onTriggerPointerUp);
  window.removeEventListener("pointercancel", onTriggerPointerUp);
  dragState = null;
  isDraggingWheel.value = false;
}

onMounted(() => {
  loadWheelLayout();
  document.addEventListener("keydown", onDocKey);
  window.addEventListener("resize", onWheelResize);
  window.addEventListener("storage", onWheelStorage);
});
onUnmounted(() => {
  document.removeEventListener("keydown", onDocKey);
  window.removeEventListener("resize", onWheelResize);
  window.removeEventListener("storage", onWheelStorage);
  teardownDragListeners();
});
</script>

<template>
  <template v-if="!isEmbed">
    <FloatingFramePanel
      :open="frameOpen"
      :fullscreen="frameFullscreen"
      :title="frameTitle"
      :z-index="13000"
      @backdrop-click="closeFrame"
    >
      <template #actions>
        <button type="button" @click="toggleFullscreen">{{ frameFullscreen ? "缩小" : "放大" }}</button>
        <button type="button" @click="openFullWindow">完整页面</button>
        <button type="button" class="danger" @click="closeFrame">关闭</button>
      </template>
      <iframe v-if="iframeSrc" :title="frameTitle" :src="iframeSrc" />
    </FloatingFramePanel>

    <div
      v-show="!triggerHidden"
      class="portal-wheel-host"
      :class="{ 'portal-wheel-open': hostOpen, 'portal-wheel-dragging': isDraggingWheel, 'portal-wheel-dense': isDense }"
      :style="wheelHostStyle"
      @mouseleave="onHostMouseLeave"
    >
      <div class="portal-wheel-fan" :class="{ open: hostOpen }" role="navigation" aria-label="快捷入口">
        <div
          v-for="(it, i) in items"
          :key="it.path"
          class="portal-wheel-item"
          :class="{ active: pathKey(it.path) === pathKey(route.path) }"
          :style="{ '--a': `${petalAngles[i]}deg`, '--i': i }"
        >
          <button type="button" class="portal-wheel-petal" @click="openFrame(it.path, it.label)">{{ it.label }}</button>
        </div>
      </div>
      <button
        type="button"
        class="portal-wheel-trigger"
        title="拖动移动位置 · 点击进入/展开 · 右击隐藏"
        :aria-expanded="hostOpen"
        @mouseenter="onTriggerMouseEnter"
        @click="onTriggerClick"
        @pointerdown="onTriggerPointerDown"
        @contextmenu.prevent="hideTrigger"
      >
        导航
      </button>
    </div>

    <div
      v-show="triggerHidden"
      class="portal-nav-hot-zone"
      aria-hidden="false"
      @mouseenter="hotCornerHover = true"
      @mouseleave="hotCornerHover = false"
    >
      <button v-show="hotCornerHover" type="button" class="portal-nav-show-btn" @click="restoreTrigger">
        显示导航
      </button>
    </div>
  </template>
</template>

<style scoped>
.portal-wheel-host {
  --portal-wheel-center-x: 128px;
  --portal-wheel-center-y: 112px;
  --portal-wheel-petal-r: 84px;
  --portal-wheel-dial-size: 174px;
  --portal-wheel-accent: #6366f1;
  --portal-wheel-accent2: #a855f7;
  position: fixed;
  z-index: 12000;
  width: 256px;
  height: 256px;
  pointer-events: none;
}
.portal-wheel-host * {
  pointer-events: auto;
}
.portal-wheel-host.portal-wheel-dragging .portal-wheel-trigger {
  cursor: grabbing;
  transform: scale(1.05);
}
.portal-wheel-fan {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}
.portal-wheel-host:hover .portal-wheel-fan,
.portal-wheel-fan.open {
  pointer-events: auto;
}
.portal-wheel-fan::before {
  content: "";
  position: absolute;
  left: var(--portal-wheel-center-x);
  bottom: var(--portal-wheel-center-y);
  width: calc(var(--portal-wheel-dial-size) + 36px);
  height: calc(var(--portal-wheel-dial-size) + 36px);
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(99, 102, 241, 0.18) 0%,
    rgba(168, 85, 247, 0.07) 50%,
    transparent 72%
  );
  opacity: 0;
  transform: translate(-50%, 50%) scale(0.5);
  pointer-events: none;
  transition: opacity 0.3s ease, transform 0.38s cubic-bezier(0.32, 1.2, 0.45, 1);
  z-index: 0;
}
.portal-wheel-host:hover .portal-wheel-fan::before,
.portal-wheel-fan.open::before {
  opacity: 1;
  transform: translate(-50%, 50%) scale(1);
}
.portal-wheel-fan::after {
  content: "";
  position: absolute;
  left: var(--portal-wheel-center-x);
  bottom: var(--portal-wheel-center-y);
  width: var(--portal-wheel-dial-size);
  height: var(--portal-wheel-dial-size);
  border-radius: 50%;
  border: 1.5px solid rgba(99, 102, 241, 0.38);
  background: rgba(255, 255, 255, 0.82);
  box-shadow:
    inset 0 0 28px rgba(99, 102, 241, 0.07),
    0 4px 20px rgba(15, 23, 42, 0.06);
  opacity: 0;
  transform: translate(-50%, 50%) scale(0.55);
  pointer-events: none;
  transition: opacity 0.28s ease, transform 0.38s cubic-bezier(0.32, 1.2, 0.45, 1);
  z-index: 1;
}
.portal-wheel-host:hover .portal-wheel-fan::after,
.portal-wheel-fan.open::after {
  opacity: 1;
  transform: translate(-50%, 50%) scale(1);
}
.portal-wheel-trigger {
  position: absolute;
  left: 50%;
  bottom: 12px;
  width: 46px;
  height: 46px;
  margin-left: -23px;
  border-radius: 50%;
  border: none;
  cursor: grab;
  touch-action: none;
  background: linear-gradient(145deg, var(--portal-wheel-accent), var(--portal-wheel-accent2));
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.02em;
  box-shadow:
    0 12px 40px rgba(15, 23, 42, 0.18),
    inset 0 -2px 10px rgba(0, 0, 0, 0.12),
    inset 0 2px 0 rgba(255, 255, 255, 0.25);
  transition: transform 0.22s ease;
  z-index: 3;
}
.portal-wheel-trigger:active {
  cursor: grabbing;
}
.portal-wheel-host:not(.portal-wheel-dragging) .portal-wheel-trigger:hover,
.portal-wheel-host:not(.portal-wheel-dragging):hover .portal-wheel-trigger,
.portal-wheel-host:not(.portal-wheel-dragging).portal-wheel-open .portal-wheel-trigger {
  transform: scale(1.08);
}
.portal-wheel-item {
  position: absolute;
  left: var(--portal-wheel-center-x);
  bottom: var(--portal-wheel-center-y);
  width: 0;
  height: 0;
  transform: rotate(calc(-1 * var(--a, 45deg))) translateX(0);
  transform-origin: 0 0;
  opacity: 0;
  z-index: 2;
  transition:
    transform 0.42s cubic-bezier(0.32, 1.28, 0.45, 1),
    opacity 0.28s ease;
  transition-delay: calc(var(--i, 0) * 0.04s);
}
.portal-wheel-host:hover .portal-wheel-item,
.portal-wheel-fan.open .portal-wheel-item {
  transform: rotate(calc(-1 * var(--a, 45deg))) translateX(var(--portal-wheel-petal-r));
  opacity: 1;
}
.portal-wheel-petal {
  position: relative;
  left: 0;
  top: 0;
  transform: translate(-50%, -50%);
  min-width: 76px;
  max-width: 102px;
  padding: 7px 9px;
  border-radius: 22px 18px 18px 9px;
  border: 1px solid rgba(99, 102, 241, 0.32);
  background: linear-gradient(118deg, rgba(255, 255, 255, 0.98) 0%, #f5f3ff 38%, #eef2ff 100%);
  color: #374151;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  box-shadow:
    0 5px 14px rgba(99, 102, 241, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, color 0.2s ease;
  white-space: nowrap;
  text-align: center;
  clip-path: ellipse(106% 70% at 42% 50%);
}
.portal-wheel-petal:hover {
  transform: translate(-50%, -50%) scale(1.06);
  color: #6366f1;
  border-color: rgba(99, 102, 241, 0.55);
  box-shadow:
    0 8px 22px rgba(99, 102, 241, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.95);
}
.portal-wheel-item.active .portal-wheel-petal {
  background: linear-gradient(118deg, #eef2ff, #ede9fe);
  color: #6366f1;
  border-color: #6366f1;
}

/* 入口 ≥8 时略缩小花瓣字号，配合更宽的 148° 弧线 */
.portal-wheel-host.portal-wheel-dense .portal-wheel-petal {
  min-width: 68px;
  max-width: 86px;
  padding: 6px 7px;
  font-size: 10px;
}
.portal-wheel-host.portal-wheel-dense .portal-wheel-item {
  transition-delay: calc(var(--i, 0) * 0.03s);
}

.portal-nav-hot-zone {
  position: fixed;
  left: 0;
  bottom: 0;
  width: min(200px, 32vw);
  height: min(200px, 36vh);
  z-index: 11990;
  display: flex;
  align-items: flex-end;
  justify-content: flex-start;
  padding: 12px 14px;
  box-sizing: border-box;
  pointer-events: auto;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0) 55%, rgba(99, 102, 241, 0.04) 100%);
}
.portal-nav-hot-zone:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0) 40%, rgba(99, 102, 241, 0.07) 100%);
}
.portal-nav-show-btn {
  border: 1px solid rgba(99, 102, 241, 0.45);
  background: rgba(255, 255, 255, 0.96);
  color: #4f46e5;
  font-size: 12px;
  font-weight: 700;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
}
.portal-nav-show-btn:hover {
  background: #eef2ff;
}
</style>
