<script setup>
/**
 * 头像圆形裁切弹窗：拖拽平移 + 滑块缩放，确认后输出 JPEG data URL。
 */
import { computed, ref, watch } from "vue";
import {
  VIEWPORT_SIZE,
  computeAvatarCoverScale,
  exportCircularAvatarCrop,
  loadImageFromDataUrl
} from "../../utils/avatarImage";
import { cancelAvatarCrop, confirmAvatarCrop, useAvatarCrop } from "../../composables/useAvatarCrop";

const { cropOpen, cropImageSrc } = useAvatarCrop();

const imgRef = ref(null);
const panX = ref(0);
const panY = ref(0);
const zoom = ref(1);
const busy = ref(false);
const loadError = ref("");

const imageStyle = computed(() => {
  if (!imgRef.value) return {};
  const cover = computeAvatarCoverScale(imgRef.value, VIEWPORT_SIZE);
  const s = cover * zoom.value;
  return {
    width: `${imgRef.value.width * s}px`,
    height: `${imgRef.value.height * s}px`,
    transform: `translate(calc(-50% + ${panX.value}px), calc(-50% + ${panY.value}px))`
  };
});

/** @type {{ dragging: boolean; startX: number; startY: number; origPanX: number; origPanY: number } | null} */
let drag = null;

async function resetForSrc(src) {
  panX.value = 0;
  panY.value = 0;
  zoom.value = 1;
  loadError.value = "";
  imgRef.value = null;
  if (!src) return;
  try {
    imgRef.value = await loadImageFromDataUrl(src);
  } catch (e) {
    loadError.value = e?.message || "图片加载失败";
  }
}

watch(cropImageSrc, (src) => {
  if (cropOpen.value && src) void resetForSrc(src);
});

watch(cropOpen, (open) => {
  if (open && cropImageSrc.value) void resetForSrc(cropImageSrc.value);
  if (!open) drag = null;
});

function onPointerDown(ev) {
  if (!imgRef.value || busy.value) return;
  drag = {
    dragging: true,
    startX: ev.clientX,
    startY: ev.clientY,
    origPanX: panX.value,
    origPanY: panY.value
  };
  ev.currentTarget?.setPointerCapture?.(ev.pointerId);
}

function onPointerMove(ev) {
  if (!drag?.dragging) return;
  panX.value = drag.origPanX + (ev.clientX - drag.startX);
  panY.value = drag.origPanY + (ev.clientY - drag.startY);
}

function onPointerUp(ev) {
  if (!drag) return;
  drag.dragging = false;
  ev.currentTarget?.releasePointerCapture?.(ev.pointerId);
}

function onBackdropClick() {
  if (!busy.value) cancelAvatarCrop();
}

async function onConfirm() {
  if (!imgRef.value || busy.value) return;
  busy.value = true;
  try {
    const dataUrl = exportCircularAvatarCrop(imgRef.value, {
      panX: panX.value,
      panY: panY.value,
      scale: zoom.value
    });
    confirmAvatarCrop(dataUrl);
  } catch (e) {
    loadError.value = e?.message || "裁切失败";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="crop-fade">
      <div v-if="cropOpen" class="crop-root" role="presentation">
        <button type="button" class="crop-backdrop" aria-label="关闭裁切" @click="onBackdropClick" />
        <div class="crop-dialog" role="dialog" aria-modal="true" aria-label="裁切头像">
          <header class="crop-head">
            <h3>裁切头像</h3>
            <p>拖动图片调整位置，滑块缩放后确认</p>
          </header>

          <p v-if="loadError" class="crop-error">{{ loadError }}</p>

          <div
            v-else
            class="crop-stage"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointercancel="onPointerUp"
          >
            <div class="crop-ring" aria-hidden="true" />
            <div v-if="imgRef" class="crop-image-wrap">
              <img :src="cropImageSrc" alt="" class="crop-image" :style="imageStyle" draggable="false" />
            </div>
            <p v-else class="crop-loading">加载中…</p>
          </div>

          <label class="crop-zoom">
            <span>缩放</span>
            <input v-model.number="zoom" type="range" min="1" max="3" step="0.01" :disabled="!imgRef || busy" />
          </label>

          <footer class="crop-actions">
            <button type="button" class="crop-btn crop-btn--ghost" :disabled="busy" @click="cancelAvatarCrop">
              取消
            </button>
            <button type="button" class="crop-btn crop-btn--primary" :disabled="!imgRef || busy" @click="onConfirm">
              {{ busy ? "处理中…" : "确认" }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.crop-root {
  position: fixed;
  inset: 0;
  z-index: 14000;
  display: grid;
  place-items: center;
  padding: 20px;
}
.crop-backdrop {
  position: absolute;
  inset: 0;
  border: none;
  background: rgba(15, 23, 42, 0.52);
  cursor: pointer;
}
.crop-dialog {
  position: relative;
  width: min(100%, 360px);
  padding: 18px 18px 16px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.22);
}
.crop-head h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
}
.crop-head p {
  margin: 6px 0 0;
  font-size: 0.78rem;
  color: #64748b;
}
.crop-error {
  margin: 14px 0 0;
  text-align: center;
  color: #dc2626;
  font-size: 0.84rem;
}
.crop-stage {
  position: relative;
  width: 240px;
  height: 240px;
  margin: 16px auto 12px;
  border-radius: 50%;
  overflow: hidden;
  background: #e2e8f0;
  touch-action: none;
  cursor: grab;
  user-select: none;
}
.crop-stage:active {
  cursor: grabbing;
}
.crop-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.95), 0 0 0 1px rgba(15, 23, 42, 0.08);
  pointer-events: none;
  z-index: 2;
}
.crop-image-wrap {
  position: absolute;
  inset: 0;
}
.crop-image {
  position: absolute;
  left: 50%;
  top: 50%;
  max-width: none;
  pointer-events: none;
}
.crop-loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  color: #64748b;
  font-size: 0.84rem;
}
.crop-zoom {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.78rem;
  color: #475569;
  margin-bottom: 14px;
}
.crop-zoom input {
  flex: 1;
}
.crop-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.crop-btn {
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}
.crop-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.crop-btn--ghost {
  background: #f8fafc;
  border-color: #e2e8f0;
  color: #475569;
}
.crop-btn--primary {
  background: var(--home-primary, #5b6adf);
  color: #fff;
}
.crop-fade-enter-active,
.crop-fade-leave-active {
  transition: opacity 0.2s ease;
}
.crop-fade-enter-from,
.crop-fade-leave-to {
  opacity: 0;
}
</style>
