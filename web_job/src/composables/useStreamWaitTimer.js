/**
 * 对话流式等待计时 — 从发送问题到收到首条助手内容（thinking/delta）的实时时长。
 */
import { computed, onBeforeUnmount, ref } from "vue";

/** @param {import('vue').Ref<boolean>} isActive 是否处于等待中 */
export function useStreamWaitTimer() {
  const startedAt = ref(null);
  const elapsedSec = ref(0);
  let timerId = null;

  const isRunning = computed(() => startedAt.value != null);

  const elapsedLabel = computed(() => {
    const s = elapsedSec.value;
    if (s <= 0) return "0s";
    const m = Math.floor(s / 60);
    const sec = s % 60;
    if (m > 0) return `${m}:${String(sec).padStart(2, "0")}`;
    return `${s}s`;
  });

  function tick() {
    if (!startedAt.value) return;
    elapsedSec.value = Math.floor((Date.now() - startedAt.value) / 1000);
  }

  function start() {
    startedAt.value = Date.now();
    elapsedSec.value = 0;
    if (timerId) clearInterval(timerId);
    timerId = setInterval(tick, 250);
  }

  function stop() {
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
    startedAt.value = null;
    elapsedSec.value = 0;
  }

  onBeforeUnmount(stop);

  return { elapsedSec, elapsedLabel, isRunning, start, stop };
}
