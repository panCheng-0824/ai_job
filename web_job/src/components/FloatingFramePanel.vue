<script setup>
import { watch } from "vue";
import { FLOATING_RESIZE_HANDLES, useFloatingPanel } from "../composables/useFloatingPanel";

const props = defineProps({
  open: { type: Boolean, default: false },
  fullscreen: { type: Boolean, default: false },
  title: { type: String, default: "" },
  zIndex: { type: Number, default: 13100 }
});

defineEmits(["backdrop-click"]);

const { panelStyle, interacting, resetPanel, onDragPointerDown, onResizePointerDown } =
  useFloatingPanel(() => props.fullscreen);

watch(
  () => props.open,
  (open) => {
    if (open) resetPanel();
  }
);
</script>

<template>
  <div
    v-show="open"
    class="ffd-backdrop"
    :style="{ zIndex: zIndex }"
    @click="$emit('backdrop-click')"
  />
  <div
    v-show="open"
    class="ffd-panel"
    :class="{
      'ffd-panel--fullscreen': fullscreen,
      'ffd-panel--interacting': interacting
    }"
    :style="{ ...panelStyle, zIndex: zIndex + 1 }"
    role="dialog"
    aria-modal="true"
    @click.stop
  >
    <template v-if="!fullscreen">
      <div
        v-for="dir in FLOATING_RESIZE_HANDLES"
        :key="dir"
        class="ffd-resize"
        :class="`ffd-resize--${dir}`"
        aria-hidden="true"
        @pointerdown="onResizePointerDown($event, dir)"
      />
    </template>
    <div
      class="ffd-head"
      :class="{ 'ffd-head--draggable': !fullscreen }"
      :title="fullscreen ? undefined : '拖动标题栏移动窗口'"
      @pointerdown="onDragPointerDown"
    >
      <span class="ffd-title">{{ title }}</span>
      <div class="ffd-actions" @click.stop @pointerdown.stop>
        <slot name="actions" />
      </div>
    </div>
    <div class="ffd-body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.ffd-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
}
.ffd-panel {
  position: fixed;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}
.ffd-panel--fullscreen {
  left: 0 !important;
  top: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  max-width: none;
  max-height: none;
  border-radius: 0;
  transform: none !important;
}
.ffd-panel--interacting {
  user-select: none;
}
.ffd-panel--interacting .ffd-body :deep(iframe) {
  pointer-events: none;
}
.ffd-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid #eceff3;
  background: linear-gradient(90deg, #fafbff, #fff);
}
.ffd-head--draggable {
  cursor: grab;
  touch-action: none;
}
.ffd-panel--interacting .ffd-head--draggable {
  cursor: grabbing;
}
.ffd-title {
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}
.ffd-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.ffd-actions :deep(button) {
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 10px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  color: #374151;
}
.ffd-actions :deep(button.danger) {
  color: #b91c1c;
  border-color: #fecaca;
}
.ffd-body {
  flex: 1;
  min-height: 0;
  background: #f8fafc;
}
.ffd-body :deep(iframe) {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
  background: #fff;
}
.ffd-resize {
  position: absolute;
  z-index: 2;
  touch-action: none;
}
.ffd-resize--n,
.ffd-resize--s {
  left: 10px;
  right: 10px;
  height: 8px;
}
.ffd-resize--n {
  top: 0;
  cursor: n-resize;
}
.ffd-resize--s {
  bottom: 0;
  cursor: s-resize;
}
.ffd-resize--e,
.ffd-resize--w {
  top: 10px;
  bottom: 10px;
  width: 8px;
}
.ffd-resize--e {
  right: 0;
  cursor: e-resize;
}
.ffd-resize--w {
  left: 0;
  cursor: w-resize;
}
.ffd-resize--ne,
.ffd-resize--nw,
.ffd-resize--se,
.ffd-resize--sw {
  width: 14px;
  height: 14px;
}
.ffd-resize--ne {
  top: 0;
  right: 0;
  cursor: ne-resize;
}
.ffd-resize--nw {
  top: 0;
  left: 0;
  cursor: nw-resize;
}
.ffd-resize--se {
  bottom: 0;
  right: 0;
  cursor: se-resize;
}
.ffd-resize--sw {
  bottom: 0;
  left: 0;
  cursor: sw-resize;
}
</style>
