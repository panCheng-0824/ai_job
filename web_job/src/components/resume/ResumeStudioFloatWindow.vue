<script setup>
/**
 * 创建简历页专用浮窗：无遮罩、可拖拽缩放。
 */
import { computed, watch } from "vue";
import { FLOATING_RESIZE_HANDLES, useFloatingPanel } from "../../composables/useFloatingPanel";
import { applyResumeStudioFloatPreset } from "../../composables/useResumeStudioFloatPreset";

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: "" },
  /** @type {'version' | 'ai'} */
  preset: { type: String, default: "version" }
});

const emit = defineEmits(["close"]);

const panelZIndex = computed(() => (props.preset === "ai" ? 12610 : 12600));

const fullscreen = defineModel("fullscreen", { type: Boolean, default: false });

const { panelStyle, interacting, left, top, width, height, clampGeom, onDragPointerDown, onResizePointerDown } =
  useFloatingPanel(() => fullscreen.value, { useDefaultCenter: false });

function applyPreset() {
  applyResumeStudioFloatPreset(props.preset, { left, top, width, height });
  clampGeom();
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      applyPreset();
    }
  }
);

watch(
  () => props.preset,
  () => {
    if (props.open) applyPreset();
  }
);
</script>

<template>
  <Teleport to="body">
    <div
      v-show="open"
      class="rs-float"
      :class="{
        'rs-float--interacting': interacting,
        'rs-float--fullscreen': fullscreen,
        'rs-float--ai': preset === 'ai'
      }"
      :style="{ ...panelStyle, zIndex: panelZIndex }"
      role="dialog"
      :aria-label="title"
    >
      <template v-if="!fullscreen">
        <div
          v-for="dir in FLOATING_RESIZE_HANDLES"
          :key="dir"
          class="rs-float-resize"
          :class="`rs-float-resize--${dir}`"
          aria-hidden="true"
          @pointerdown="onResizePointerDown($event, dir)"
        />
      </template>
      <div
        class="rs-float-head"
        :class="{ 'rs-float-head--draggable': !fullscreen }"
        :title="fullscreen ? undefined : '拖动标题栏移动窗口'"
        @pointerdown="onDragPointerDown"
      >
        <span class="rs-float-title">{{ title }}</span>
        <div class="rs-float-actions" @click.stop @pointerdown.stop>
          <slot name="actions">
            <button type="button" class="rs-float-btn" @click="fullscreen = !fullscreen">
              {{ fullscreen ? "还原" : "最大化" }}
            </button>
            <button type="button" class="rs-float-btn rs-float-btn--close" @click="emit('close')">关闭</button>
          </slot>
        </div>
      </div>
      <div class="rs-float-body">
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.rs-float {
  position: fixed;
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.14);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}
.rs-float--ai .rs-float-head {
  background: linear-gradient(90deg, #faf5ff, #fff);
  border-bottom-color: #ede9fe;
}
.rs-float--ai .rs-float-title {
  color: #6b21a8;
}
.rs-float--ai .rs-float-body {
  padding: 0;
  background: #f8fafc;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.rs-float--ai .rs-float-body :deep(.ai-rail) {
  flex: 1;
  min-height: 0;
}
.rs-float--fullscreen {
  left: 0 !important;
  top: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  max-width: none;
  max-height: none;
  border-radius: 0;
  transform: none !important;
}
.rs-float--interacting {
  user-select: none;
}
.rs-float-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid #eceff3;
  background: linear-gradient(90deg, #fafbff, #fff);
}
.rs-float-head--draggable {
  cursor: grab;
  touch-action: none;
}
.rs-float--interacting .rs-float-head--draggable {
  cursor: grabbing;
}
.rs-float-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}
.rs-float-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.rs-float-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  color: #374151;
}
.rs-float-btn:hover {
  border-color: #c7d2fe;
  color: #4338ca;
}
.rs-float-btn--close:hover {
  border-color: #fecaca;
  color: #b91c1c;
}
.rs-float-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  background: #f8fafc;
}
.rs-float-resize {
  position: absolute;
  z-index: 2;
  touch-action: none;
}
.rs-float-resize--n,
.rs-float-resize--s {
  left: 10px;
  right: 10px;
  height: 8px;
}
.rs-float-resize--n {
  top: 0;
  cursor: n-resize;
}
.rs-float-resize--s {
  bottom: 0;
  cursor: s-resize;
}
.rs-float-resize--e,
.rs-float-resize--w {
  top: 10px;
  bottom: 10px;
  width: 8px;
}
.rs-float-resize--e {
  right: 0;
  cursor: e-resize;
}
.rs-float-resize--w {
  left: 0;
  cursor: w-resize;
}
.rs-float-resize--ne,
.rs-float-resize--nw,
.rs-float-resize--se,
.rs-float-resize--sw {
  width: 14px;
  height: 14px;
}
.rs-float-resize--ne {
  top: 0;
  right: 0;
  cursor: ne-resize;
}
.rs-float-resize--nw {
  top: 0;
  left: 0;
  cursor: nw-resize;
}
.rs-float-resize--se {
  bottom: 0;
  right: 0;
  cursor: se-resize;
}
.rs-float-resize--sw {
  bottom: 0;
  left: 0;
  cursor: sw-resize;
}
</style>
