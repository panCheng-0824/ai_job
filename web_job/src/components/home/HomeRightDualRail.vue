<script setup>
/**
 * 首页最右侧双抽屉：推荐理由 / 匹配记录，颜色区分，同时仅可展开一个。
 */
import { computed, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  /** null | 'reason' | 'history' */
  active: { type: String, default: null },
  panelWidth: { type: String, default: "300px" }
});

const emit = defineEmits(["update:active"]);

const isOpen = computed(() => props.active === "reason" || props.active === "history");
const MIN_PANEL_WIDTH = 220;
const MAX_PANEL_WIDTH = 420;
const OPEN_DRAG_THRESHOLD = 10;

function parsePanelWidth(value) {
  const n = Number.parseInt(String(value || "").replace("px", ""), 10);
  if (!Number.isFinite(n)) return 300;
  return Math.max(MIN_PANEL_WIDTH, Math.min(MAX_PANEL_WIDTH, n));
}

const dragWidth = ref(parsePanelWidth(props.panelWidth));
const dualRailStyle = computed(() => ({ "--dual-rail-width": `${Math.round(dragWidth.value)}px` }));

watch(
  () => props.panelWidth,
  (next) => {
    dragWidth.value = parsePanelWidth(next);
  }
);

const tabs = [
  { key: "reason", label: "推荐理由", short: "⇄", theme: "reason", offset: 0 },
  { key: "history", label: "匹配记录", short: "⇄", theme: "history", offset: 64 }
];

let dragCleanup = null;
let suppressClickKey = null;

function onTabClick(key) {
  if (suppressClickKey === key) {
    suppressClickKey = null;
    return;
  }
  emit("update:active", props.active === key ? null : key);
}

function onTabMouseDown(tabKey, event) {
  if (event.button !== 0) return;
  const startX = event.clientX;
  const startWidth = props.active === tabKey ? dragWidth.value : 0;
  let moved = false;

  const onMove = (moveEvent) => {
    const deltaX = moveEvent.clientX - startX;
    if (Math.abs(deltaX) > 1) moved = true;
    if (Math.abs(deltaX) > 4) suppressClickKey = tabKey;
    // 右侧抽屉向左拖（deltaX < 0）变宽
    const raw = startWidth - deltaX;

    if (raw <= OPEN_DRAG_THRESHOLD) {
      if (props.active === tabKey) emit("update:active", null);
      return;
    }

    const nextWidth = Math.max(MIN_PANEL_WIDTH, Math.min(MAX_PANEL_WIDTH, raw));
    dragWidth.value = nextWidth;
    if (props.active !== tabKey) emit("update:active", tabKey);
  };

  const onUp = () => {
    if (!moved) {
      dragCleanup?.();
      return;
    }
    dragCleanup?.();
  };

  window.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);
  dragCleanup = () => {
    window.removeEventListener("mousemove", onMove);
    window.removeEventListener("mouseup", onUp);
    dragCleanup = null;
  };
}

onBeforeUnmount(() => {
  dragCleanup?.();
});
</script>

<template>
  <div
    class="dual-rail"
    :class="{ 'dual-rail--open': isOpen, [`dual-rail--${active}`]: isOpen }"
    :style="dualRailStyle"
  >
    <aside
      v-if="active === 'reason'"
      class="dual-rail-panel dual-rail-panel--reason"
      aria-label="推荐理由"
    >
      <div class="dual-rail-panel-body">
        <slot name="reason" />
      </div>
    </aside>
    <aside
      v-else-if="active === 'history'"
      class="dual-rail-panel dual-rail-panel--history"
      aria-label="匹配记录"
    >
      <div class="dual-rail-panel-body">
        <slot name="history" />
      </div>
    </aside>

    <div class="dual-rail-tabs" role="tablist" aria-label="右侧抽屉">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        role="tab"
        class="dual-rail-tab"
        :class="[
          `dual-rail-tab--${tab.theme}`,
          'dual-rail-tab--puller',
          { 'dual-rail-tab--active': active === tab.key }
        ]"
        :style="{ '--puller-offset': `${tab.offset}px` }"
        :aria-selected="active === tab.key"
        :title="tab.label"
        @mousedown.prevent="onTabMouseDown(tab.key, $event)"
        @click="onTabClick(tab.key)"
      >
        <span class="dual-rail-tab-text">{{ tab.short }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.dual-rail {
  position: relative;
  display: flex;
  flex-direction: row-reverse;
  align-items: flex-start;
  align-self: stretch;
  min-height: 120px;
  padding-left: 8px;
}
.dual-rail--open {
  display: flex;
}
.dual-rail-tabs {
  position: sticky;
  top: calc(var(--home-topbar-h, 56px) + 12px);
  z-index: 7;
  width: 0;
  height: var(--side-rail-panel-h, min(680px, calc(100vh - var(--home-topbar-h, 56px) - 32px)));
  overflow: visible;
}
.dual-rail-tab {
  width: 16px;
  height: 56px;
  padding: 0;
  border: 1px solid #e2e8f0;
  border-radius: 10px 0 0 10px;
  background: #fff;
  cursor: pointer;
  writing-mode: horizontal-tb;
  text-orientation: mixed;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: #64748b;
  box-shadow: -2px 2px 12px rgba(15, 23, 42, 0.08);
  transition: background 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s;
}
.dual-rail-tab--puller {
  position: absolute;
  left: -8px;
  top: calc((100% - 56px) / 2 + var(--puller-offset, 0px));
}
.dual-rail-tab-text {
  display: inline-block;
  writing-mode: horizontal-tb;
}
.dual-rail-tab--reason:hover,
.dual-rail-tab--reason.dual-rail-tab--active {
  border-color: #a5b4fc;
  background: #eef2ff;
  color: #4338ca;
  box-shadow: -3px 4px 16px rgba(99, 102, 241, 0.2);
}
.dual-rail-tab--history:hover,
.dual-rail-tab--history.dual-rail-tab--active {
  border-color: #6ee7b7;
  background: #ecfdf5;
  color: #047857;
  box-shadow: -3px 4px 16px rgba(16, 185, 129, 0.2);
}
.dual-rail-panel {
  width: var(--dual-rail-width, 300px);
  max-width: min(var(--dual-rail-width, 300px), calc(100vw - 80px));
  flex-shrink: 0;
  position: sticky;
  top: calc(var(--home-topbar-h, 56px) + 12px);
  height: var(--side-rail-panel-h, min(680px, calc(100vh - var(--home-topbar-h, 56px) - 32px)));
  max-height: var(--side-rail-panel-h, min(680px, calc(100vh - var(--home-topbar-h, 56px) - 32px)));
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: -8px 0 28px rgba(15, 23, 42, 0.08);
}
.dual-rail-panel--reason {
  border-color: #c7d2fe;
  background: linear-gradient(180deg, #fafbff 0%, #fff 100%);
}
.dual-rail-panel--history {
  border-color: #a7f3d0;
  background: linear-gradient(180deg, #f0fdf9 0%, #fff 100%);
}
@media (max-width: 1100px) {
  .dual-rail {
    flex-direction: column;
    padding-left: 0;
  }
  .dual-rail-tabs {
    position: static;
    width: 100%;
    height: auto;
    margin-bottom: 8px;
    display: flex;
    gap: 8px;
  }
  .dual-rail-tab {
    width: auto;
    flex: 1;
    writing-mode: horizontal-tb;
    border-radius: 10px;
    padding: 8px 12px;
    height: auto;
  }
  .dual-rail-tab--puller {
    position: static;
    top: auto;
    left: auto;
  }
  .dual-rail-panel {
    position: static;
    height: auto;
    max-height: none;
    width: 100%;
    max-width: 100%;
    border-radius: 16px;
    border-right: 1px solid #e2e8f0;
  }
  .rail-slot {
    max-height: min(70vh, 560px);
  }
}
</style>
