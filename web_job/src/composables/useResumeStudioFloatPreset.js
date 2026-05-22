const PAD = 16;
const HEADER_TOP = 72;
const MIN_W = 320;
const MIN_H = 260;

/**
 * 按浮窗类型设置初始位置与尺寸（靠右错落排布）。
 * @param {'version' | 'ai'} preset
 */
export function applyResumeStudioFloatPreset(preset, geom) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  if (preset === "version") {
    const w = Math.min(400, Math.max(MIN_W, Math.round(vw * 0.34)));
    const h = Math.min(Math.round(vh * 0.86), 840);
    geom.width.value = w;
    geom.height.value = h;
    geom.left.value = vw - w - PAD;
    geom.top.value = HEADER_TOP;
    return;
  }

  if (preset === "ai") {
    const w = Math.min(460, Math.max(MIN_W, Math.round(vw * 0.38)));
    const h = Math.min(Math.round(vh * 0.92), 900);
    geom.width.value = w;
    geom.height.value = h;
    const versionOffset = Math.min(420, vw * 0.36);
    geom.left.value = Math.max(PAD, vw - w - PAD - versionOffset);
    geom.top.value = HEADER_TOP + 12;
  }
}

export { PAD, MIN_W, MIN_H };
