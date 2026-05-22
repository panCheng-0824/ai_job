import { computed, ref, watch } from "vue";

const PAD = 12;
const MIN_W = 380;
const MIN_H = 260;
const DEFAULT_W = 1120;
const MAX_H = 900;

export const FLOATING_RESIZE_HANDLES = ["n", "s", "e", "w", "ne", "nw", "se", "sw"];

/**
 * 弹窗几何：每次打开 reset，不持久化；全屏时暂存几何，退出全屏后恢复。
 * @param {() => boolean} isFullscreen
 */
export function useFloatingPanel(isFullscreen, options = {}) {
  const { useDefaultCenter = true } = options;
  const left = ref(0);
  const top = ref(0);
  const width = ref(800);
  const height = ref(600);
  const interacting = ref(false);

  /** @type {{ left: number; top: number; width: number; height: number } | null} */
  let geomBeforeFullscreen = null;
  /** @type {{ type: string; dir?: string; startX: number; startY: number; origL: number; origT: number; origW: number; origH: number } | null} */
  let gesture = null;

  function defaultSize() {
    const w = Math.min(DEFAULT_W, Math.round(window.innerWidth * 0.94));
    const h = Math.min(Math.round(window.innerHeight * 0.82), MAX_H);
    return { w, h };
  }

  function resetPanel() {
    if (!useDefaultCenter) return;
    const { w, h } = defaultSize();
    width.value = w;
    height.value = h;
    left.value = Math.max(PAD, Math.round((window.innerWidth - w) / 2));
    top.value = Math.max(PAD, Math.round((window.innerHeight - h) / 2));
    geomBeforeFullscreen = null;
  }

  function clampGeom() {
    const maxW = Math.max(MIN_W, window.innerWidth - PAD * 2);
    const maxH = Math.max(MIN_H, window.innerHeight - PAD * 2);
    width.value = Math.min(Math.max(width.value, MIN_W), maxW);
    height.value = Math.min(Math.max(height.value, MIN_H), maxH);
    left.value = Math.min(Math.max(left.value, PAD), window.innerWidth - width.value - PAD);
    top.value = Math.min(Math.max(top.value, PAD), window.innerHeight - height.value - PAD);
  }

  const panelStyle = computed(() => {
    if (isFullscreen()) return {};
    return {
      left: `${left.value}px`,
      top: `${top.value}px`,
      width: `${width.value}px`,
      height: `${height.value}px`,
      transform: "none"
    };
  });

  function teardownGesture() {
    gesture = null;
    interacting.value = false;
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerUp);
    window.removeEventListener("pointercancel", onPointerUp);
  }

  function onPointerMove(e) {
    if (!gesture || isFullscreen()) return;
    const dx = e.clientX - gesture.startX;
    const dy = e.clientY - gesture.startY;
    if (gesture.type === "move") {
      left.value = gesture.origL + dx;
      top.value = gesture.origT + dy;
    } else if (gesture.type === "resize" && gesture.dir) {
      let l = gesture.origL;
      let t = gesture.origT;
      let w = gesture.origW;
      let h = gesture.origH;
      const dir = gesture.dir;
      if (dir.includes("e")) w = gesture.origW + dx;
      if (dir.includes("w")) {
        w = gesture.origW - dx;
        l = gesture.origL + dx;
      }
      if (dir.includes("s")) h = gesture.origH + dy;
      if (dir.includes("n")) {
        h = gesture.origH - dy;
        t = gesture.origT + dy;
      }
      left.value = l;
      top.value = t;
      width.value = w;
      height.value = h;
    }
    clampGeom();
  }

  function onPointerUp() {
    teardownGesture();
  }

  function bindGesture(next) {
    gesture = next;
    interacting.value = true;
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
  }

  function onDragPointerDown(e) {
    if (isFullscreen()) return;
    if (e.button !== 0) return;
    if (e.target.closest("button")) return;
    e.preventDefault();
    bindGesture({
      type: "move",
      startX: e.clientX,
      startY: e.clientY,
      origL: left.value,
      origT: top.value,
      origW: width.value,
      origH: height.value
    });
    e.currentTarget.setPointerCapture?.(e.pointerId);
  }

  function onResizePointerDown(e, dir) {
    if (isFullscreen()) return;
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    bindGesture({
      type: "resize",
      dir,
      startX: e.clientX,
      startY: e.clientY,
      origL: left.value,
      origT: top.value,
      origW: width.value,
      origH: height.value
    });
    e.currentTarget.setPointerCapture?.(e.pointerId);
  }

  watch(isFullscreen, (fs, wasFs) => {
    if (fs && !wasFs) {
      geomBeforeFullscreen = {
        left: left.value,
        top: top.value,
        width: width.value,
        height: height.value
      };
      return;
    }
    if (!fs && wasFs && geomBeforeFullscreen) {
      left.value = geomBeforeFullscreen.left;
      top.value = geomBeforeFullscreen.top;
      width.value = geomBeforeFullscreen.width;
      height.value = geomBeforeFullscreen.height;
      clampGeom();
    }
  });

  return {
    left,
    top,
    width,
    height,
    panelStyle,
    interacting,
    resetPanel,
    clampGeom,
    onDragPointerDown,
    onResizePointerDown
  };
}
