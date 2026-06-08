import { computed, onUnmounted, ref } from "vue";

/** 详情页/单条同步：固定 3 分钟刻度进度条 */
export const RAG_SYNC_THREE_MINUTE_MS = 3 * 60_000;

export function formatRagSyncDuration(ms) {
  const totalSec = Math.max(0, Math.floor(Number(ms) / 1000));
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  if (m > 0) return `${m}分${String(s).padStart(2, "0")}秒`;
  return `${s}秒`;
}

export function ragSyncFillColorClass(ms) {
  const elapsed = Math.max(0, Number(ms) || 0);
  if (elapsed >= 2 * 60_000) return "rag3-fill--m3";
  if (elapsed >= 60_000) return "rag3-fill--m2";
  return "rag3-fill--m1";
}

export function useRagSyncThreeMinuteProgress(scaleMs = RAG_SYNC_THREE_MINUTE_MS) {
  const running = ref(false);
  const elapsedMs = ref(0);
  let startedAt = 0;
  let ticker = null;

  function clearTicker() {
    if (ticker) {
      clearInterval(ticker);
      ticker = null;
    }
  }

  function tick() {
    if (!running.value || !startedAt) return;
    elapsedMs.value = Date.now() - startedAt;
  }

  function start() {
    clearTicker();
    running.value = true;
    startedAt = Date.now();
    elapsedMs.value = 0;
    ticker = window.setInterval(tick, 200);
  }

  function stop() {
    clearTicker();
    if (startedAt) {
      elapsedMs.value = Date.now() - startedAt;
    }
    running.value = false;
    startedAt = 0;
  }

  function reset() {
    clearTicker();
    running.value = false;
    startedAt = 0;
    elapsedMs.value = 0;
  }

  onUnmounted(clearTicker);

  const fillPct = computed(() => {
    if (scaleMs <= 0) return 0;
    return Math.min(100, (elapsedMs.value / scaleMs) * 100);
  });

  const fillPctRounded = computed(() => Math.round(fillPct.value));

  const overScale = computed(() => elapsedMs.value > scaleMs);

  const progressLabel = computed(() => {
    const elapsed = formatRagSyncDuration(elapsedMs.value);
    const scale = formatRagSyncDuration(scaleMs);
    if (overScale.value) {
      return `已用 ${elapsed} · 超过 ${scale} 刻度（同步仍在进行）`;
    }
    return `已用 ${elapsed} · 总刻度 ${scale}`;
  });

  const fillColorClass = computed(() => ragSyncFillColorClass(elapsedMs.value));

  return {
    running,
    elapsedMs,
    fillPct,
    fillPctRounded,
    overScale,
    progressLabel,
    fillColorClass,
    start,
    stop,
    reset,
    formatRagSyncDuration,
  };
}
