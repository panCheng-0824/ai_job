import { computed, onUnmounted, ref } from "vue";

/** 单条岗位同步预估耗时（秒） */
export const RAG_SYNC_SECONDS_PER_JOB = 50;

/** 格式化为 HH:MM:SS */
export function formatRagSyncHms(totalSeconds) {
  const sec = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

function resolveRemainingJobs(ragLive, syncRunning) {
  if (!syncRunning) {
    return Math.max(0, Number(ragLive?.unsynced ?? 0));
  }
  const batchTotal = Number(ragLive?.batchTotal ?? 0);
  const batchIndex = Number(ragLive?.batchIndex ?? 0);
  if (batchTotal > 0) {
    return Math.max(0, batchTotal - batchIndex);
  }
  return Math.max(0, Number(ragLive?.unsynced ?? 0));
}

function estimateSeconds(remainingJobs, accelerate, maxParallel) {
  const jobs = Math.max(0, Number(remainingJobs) || 0);
  if (jobs <= 0) return 0;
  if (accelerate) {
    const parallel = Math.max(1, Number(maxParallel) || 1);
    return Math.ceil(jobs / parallel) * RAG_SYNC_SECONDS_PER_JOB;
  }
  return jobs * RAG_SYNC_SECONDS_PER_JOB;
}

/**
 * 同步岗位 ETA 倒计时：按未同步条数 × 50 秒估算，SSE 推进时重新校准。
 */
export function useRagSyncEtaCountdown() {
  const displaySeconds = ref(0);
  const endAtMs = ref(0);
  const paused = ref(false);
  let pausedRemainingMs = 0;
  let ticker = null;

  function clearTicker() {
    if (ticker) {
      clearInterval(ticker);
      ticker = null;
    }
  }

  function tick() {
    if (paused.value) return;
    const leftMs = Math.max(0, endAtMs.value - Date.now());
    displaySeconds.value = Math.ceil(leftMs / 1000);
    if (leftMs <= 0) {
      clearTicker();
    }
  }

  function syncAnchor({ ragLive, syncRunning, accelerate = false, maxParallel = 1 }) {
    const jobs = resolveRemainingJobs(ragLive, syncRunning);
    const seconds = estimateSeconds(jobs, accelerate, maxParallel);
    const targetMs = seconds * 1000;

    if (paused.value) {
      pausedRemainingMs = targetMs;
      displaySeconds.value = seconds;
      return;
    }

    endAtMs.value = Date.now() + targetMs;
    displaySeconds.value = seconds;
    if (syncRunning && !ticker) {
      startTicker();
    }
    tick();
  }

  function startTicker() {
    clearTicker();
    ticker = window.setInterval(tick, 1000);
  }

  function pause() {
    if (paused.value) return;
    paused.value = true;
    pausedRemainingMs = Math.max(0, endAtMs.value - Date.now());
    displaySeconds.value = Math.ceil(pausedRemainingMs / 1000);
    clearTicker();
  }

  function resume() {
    if (!paused.value) return;
    paused.value = false;
    endAtMs.value = Date.now() + pausedRemainingMs;
    startTicker();
    tick();
  }

  function stop() {
    clearTicker();
    paused.value = false;
    pausedRemainingMs = 0;
    endAtMs.value = 0;
    displaySeconds.value = 0;
  }

  onUnmounted(stop);

  const displayHms = computed(() => formatRagSyncHms(displaySeconds.value));

  return {
    displaySeconds,
    displayHms,
    paused,
    syncAnchor,
    startTicker,
    pause,
    resume,
    stop,
    estimateSeconds,
    formatRagSyncHms,
  };
}
