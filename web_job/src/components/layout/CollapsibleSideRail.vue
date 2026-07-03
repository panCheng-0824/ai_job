<script setup>
/**
 * 可折叠侧栏：展开时显示面板；收起后保留竖向把手（原位展开）。
 */
import { computed, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  open: { type: Boolean, default: true },
  side: {
    type: String,
    default: "left",
    validator: (value) => ["left", "right"].includes(value)
  },
  title: { type: String, default: "" },
  panelWidth: { type: String, default: "280px" },
  /** profile | filter | history | reason | default */
  theme: {
    type: String,
    default: "default",
    validator: (value) => ["default", "profile", "filter", "history", "reason"].includes(value)
  }
});

const emit = defineEmits(["update:open"]);

const handleLabel = computed(() => props.title || (props.side === "left" ? "侧栏" : "面板"));
const useDragPuller = computed(
  () => (props.theme === "profile" || props.theme === "filter") && props.side === "left"
);
const MIN_PANEL_WIDTH = 220;
const MAX_PANEL_WIDTH = 420;
const OPEN_DRAG_THRESHOLD = 10;

function parsePanelWidth(value) {
  const n = Number.parseInt(String(value || "").replace("px", ""), 10);
  if (!Number.isFinite(n)) return 292;
  return Math.max(MIN_PANEL_WIDTH, Math.min(MAX_PANEL_WIDTH, n));
}

const dragWidth = ref(parsePanelWidth(props.panelWidth));
const sideRailStyle = computed(() => {
  if (useDragPuller.value) {
    return {
      "--side-rail-width": `${Math.round(dragWidth.value)}px`,
      "--side-rail-active-panel-h":
        props.theme === "filter"
          ? "var(--side-rail-panel-h-filter, min(580px, calc(100vh - var(--home-topbar-h, 56px) - 32px)))"
          : "var(--side-rail-panel-h, min(680px, calc(100vh - var(--home-topbar-h, 56px) - 32px)))"
    };
  }
  return props.open ? { "--side-rail-width": props.panelWidth } : undefined;
});

watch(
  () => props.panelWidth,
  (next) => {
    if (!useDragPuller.value) return;
    dragWidth.value = parsePanelWidth(next);
  }
);

let dragCleanup = null;
let suppressNextClick = false;

function onHandleMouseDown(event) {
  if (!useDragPuller.value || event.button !== 0) return;
  const startX = event.clientX;
  const startWidth = props.open ? dragWidth.value : 0;
  let moved = false;

  const onMove = (moveEvent) => {
    const deltaX = moveEvent.clientX - startX;
    if (Math.abs(deltaX) > 1) moved = true;
    if (Math.abs(deltaX) > 4) suppressNextClick = true;
    const raw = startWidth + deltaX;

    if (raw <= OPEN_DRAG_THRESHOLD) {
      if (props.open) emit("update:open", false);
      return;
    }

    const nextWidth = Math.max(MIN_PANEL_WIDTH, Math.min(MAX_PANEL_WIDTH, raw));
    dragWidth.value = nextWidth;
    if (!props.open) {
      emit("update:open", true);
    }
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

function onHandleClick() {
  if (useDragPuller.value && suppressNextClick) {
    suppressNextClick = false;
    return;
  }
  toggle();
}

onBeforeUnmount(() => {
  dragCleanup?.();
});
function toggle() {
  emit("update:open", !props.open);
}
</script>

<template>
  <div
    class="side-rail"
    :class="[
      `side-rail--${side}`,
      `side-rail--${theme}`,
      { 'side-rail--open': open, 'side-rail--collapsed': !open }
    ]"
    :style="sideRailStyle"
  >
    <aside
      v-if="open"
      class="side-rail-panel"
      :class="`side-rail-panel--${theme}`"
      :aria-label="title"
    >
      <div class="side-rail-panel-body">
        <slot />
      </div>
    </aside>

    <button
      type="button"
      class="side-rail-handle"
      :class="[
        `side-rail-handle--${theme}`,
        { 'side-rail-handle--drag-puller': useDragPuller },
        { 'side-rail-handle--active': open }
      ]"
      :aria-expanded="open"
      :aria-label="open ? `收起${title}` : `展开${title}`"
      :title="open ? `收起${title}` : `展开${title}`"
      @mousedown.prevent="onHandleMouseDown"
      @click="onHandleClick"
    >
      <span v-if="!useDragPuller" class="side-rail-handle-text">{{ handleLabel }}</span>
      <span v-else class="side-rail-puller-icon" aria-hidden="true">⇄</span>
    </button>
  </div>
</template>

<style scoped>
.side-rail {
  position: relative;
  display: flex;
  align-items: flex-start;
  align-self: stretch;
  min-height: 120px;
}
.side-rail--left {
  flex-direction: row;
  padding-right: 8px;
}
.side-rail--right {
  flex-direction: row-reverse;
  padding-left: 8px;
}
.side-rail-handle {
  flex-shrink: 0;
  position: sticky;
  top: calc(var(--home-topbar-h, 56px) + 12px);
  z-index: 7;
  width: 28px;
  padding: 9px 4px;
  border: 1px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #64748b;
  transition: background 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s;
}
.side-rail-handle-text {
  display: inline-block;
}
.side-rail-puller-icon {
  font-size: 0.62rem;
  line-height: 1;
  color: #0369a1;
  letter-spacing: -0.5px;
  writing-mode: horizontal-tb;
}
.side-rail-handle--drag-puller {
  position: absolute;
  left: auto;
  right: 0;
  width: 16px;
  height: 56px;
  padding: 0;
  top: calc(
    var(--home-topbar-h, 56px) + 12px +
    (var(--side-rail-active-panel-h, var(--side-rail-panel-h, min(680px, calc(100vh - var(--home-topbar-h, 56px) - 32px)))) - 56px) / 2
  );
  transform: none;
  writing-mode: horizontal-tb;
  text-orientation: mixed;
  border-radius: 0 10px 10px 0;
  border-color: #7dd3fc;
  background: linear-gradient(180deg, #f0f9ff 0%, #e0f2fe 100%);
  box-shadow: 2px 4px 14px rgba(14, 165, 233, 0.2);
}
.side-rail--left .side-rail-handle {
  border-radius: 0 8px 8px 0;
  box-shadow: 2px 2px 10px rgba(15, 23, 42, 0.1);
}
.side-rail--right .side-rail-handle {
  border-radius: 8px 0 0 8px;
  box-shadow: -2px 2px 10px rgba(15, 23, 42, 0.1);
}
.side-rail--left .side-rail-handle.side-rail-handle--drag-puller {
  border-radius: 0 10px 10px 0;
  margin-left: 0;
  margin-right: -8px;
}
.side-rail-handle--profile:hover,
.side-rail-handle--profile.side-rail-handle--active {
  border-color: #7dd3fc;
  background: #f0f9ff;
  color: #0369a1;
  box-shadow: 2px 4px 16px rgba(14, 165, 233, 0.2);
}
.side-rail-handle--profile.side-rail-handle--drag-puller:hover,
.side-rail-handle--profile.side-rail-handle--drag-puller.side-rail-handle--active {
  border-color: #38bdf8;
  background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%);
  box-shadow: 2px 6px 16px rgba(14, 165, 233, 0.24);
}
.side-rail-handle--filter.side-rail-handle--drag-puller:hover,
.side-rail-handle--filter.side-rail-handle--drag-puller.side-rail-handle--active {
  border-color: #a78bfa;
  background: linear-gradient(180deg, #ede9fe 0%, #ddd6fe 100%);
  box-shadow: 2px 6px 16px rgba(139, 92, 246, 0.24);
}
.side-rail--right .side-rail-handle--profile:hover,
.side-rail--right .side-rail-handle--profile.side-rail-handle--active {
  box-shadow: -3px 4px 14px rgba(14, 165, 233, 0.22);
}
.side-rail-handle--filter:hover,
.side-rail-handle--filter.side-rail-handle--active {
  border-color: #c4b5fd;
  background: #f5f3ff;
  color: #6d28d9;
  box-shadow: 2px 4px 16px rgba(139, 92, 246, 0.2);
}
.side-rail--right .side-rail-handle--filter:hover,
.side-rail--right .side-rail-handle--filter.side-rail-handle--active {
  box-shadow: -3px 4px 14px rgba(139, 92, 246, 0.22);
}
.side-rail-handle--history:hover,
.side-rail-handle--history.side-rail-handle--active {
  border-color: #6ee7b7;
  background: #ecfdf5;
  color: #047857;
  box-shadow: 2px 4px 16px rgba(16, 185, 129, 0.2);
}
.side-rail--right .side-rail-handle--history:hover,
.side-rail--right .side-rail-handle--history.side-rail-handle--active {
  box-shadow: -3px 4px 14px rgba(16, 185, 129, 0.22);
}
.side-rail-handle--reason:hover,
.side-rail-handle--reason.side-rail-handle--active {
  border-color: #a5b4fc;
  background: #eef2ff;
  color: #4338ca;
  box-shadow: 2px 4px 16px rgba(99, 102, 241, 0.2);
}
.side-rail--right .side-rail-handle--reason:hover,
.side-rail--right .side-rail-handle--reason.side-rail-handle--active {
  box-shadow: -3px 4px 14px rgba(99, 102, 241, 0.22);
}
.side-rail-handle--default:hover,
.side-rail-handle--default.side-rail-handle--active {
  border-color: #c7d2fe;
  background: #eef2ff;
  color: #4338ca;
  box-shadow: 2px 4px 16px rgba(99, 102, 241, 0.18);
}
.side-rail--right .side-rail-handle--default:hover,
.side-rail--right .side-rail-handle--default.side-rail-handle--active {
  box-shadow: -3px 4px 14px rgba(99, 102, 241, 0.18);
}
.side-rail-panel {
  width: var(--side-rail-width, 280px);
  max-width: min(var(--side-rail-width, 280px), calc(100vw - 80px));
  flex-shrink: 0;
  position: sticky;
  top: calc(var(--home-topbar-h, 56px) + 12px);
  height: var(--side-rail-panel-h, min(680px, calc(100vh - var(--home-topbar-h, 56px) - 32px)));
  max-height: var(--side-rail-panel-h, min(680px, calc(100vh - var(--home-topbar-h, 56px) - 32px)));
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
}
.side-rail-panel--filter {
  --side-rail-panel-h: var(--side-rail-panel-h-filter);
}
.side-rail--left .side-rail-panel {
  border-radius: 16px;
}
.side-rail--right .side-rail-panel {
  border-radius: 16px;
  box-shadow: -8px 0 28px rgba(15, 23, 42, 0.08);
}
.side-rail-panel--profile {
  border-color: #bae6fd;
  background: linear-gradient(180deg, #f0f9ff 0%, #fff 100%);
}
.side-rail-panel--filter {
  border-color: #ddd6fe;
  background: linear-gradient(180deg, #faf5ff 0%, #fff 100%);
}
.side-rail-panel--history {
  border-color: #a7f3d0;
  background: linear-gradient(180deg, #f0fdf9 0%, #fff 100%);
}
.side-rail-panel--reason {
  border-color: #c7d2fe;
  background: linear-gradient(180deg, #fafbff 0%, #fff 100%);
}
@media (max-width: 1100px) {
  .side-rail {
    flex-direction: column;
    padding-left: 0;
    padding-right: 0;
  }
  .side-rail-handle {
    position: static;
    width: auto;
    writing-mode: horizontal-tb;
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 8px;
    box-shadow: 0 2px 12px rgba(15, 23, 42, 0.08);
  }
  .side-rail-panel {
    position: static;
    height: auto;
    max-height: none;
    width: 100%;
    max-width: 100%;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
  }
  .rail-slot {
    max-height: min(70vh, 560px);
  }
}
</style>
