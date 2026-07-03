/**
 * 岗位推荐等待计时：匹配请求进行中实时刷新已等待时长。
 */
import { computed, onBeforeUnmount, ref } from "vue";

/** 等待阶段文案（按已等待毫秒递进展示） */
export const JOB_MATCH_WAIT_STEPS = [
  { beforeMs: 0, label: "正在理解您的岗位诉求" },
  { beforeMs: 2000, label: "正在改写检索查询" },
  { beforeMs: 5000, label: "正在检索知识库素材" },
  { beforeMs: 12000, label: "大模型正在分析匹配度" },
  { beforeMs: 25000, label: "正在整理推荐结果" }
];

/** 将毫秒格式化为展示文案 */
export function formatJobMatchElapsed(ms) {
  if (!Number.isFinite(ms) || ms < 0) return "0 秒";
  if (ms < 1000) return `${Math.max(1, Math.round(ms))} 毫秒`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} 秒`;
  const m = Math.floor(ms / 60000);
  const s = ((ms % 60000) / 1000).toFixed(1);
  return `${m} 分 ${s} 秒`;
}

/** 根据已等待毫秒解析当前阶段索引 */
export function resolveJobMatchStepIndex(elapsedMs) {
  const ms = Math.max(0, Number(elapsedMs) || 0);
  let idx = 0;
  for (let i = 0; i < JOB_MATCH_WAIT_STEPS.length; i += 1) {
    if (ms >= JOB_MATCH_WAIT_STEPS[i].beforeMs) idx = i;
  }
  return idx;
}

export function useJobMatchWaitTimer() {
  const elapsedMs = ref(0);
  let timerId = null;
  let startedAt = 0;

  const isRunning = computed(() => timerId != null);

  const elapsedLabel = computed(() => formatJobMatchElapsed(elapsedMs.value));

  const stepIndex = computed(() => resolveJobMatchStepIndex(elapsedMs.value));

  const stepLabel = computed(() => JOB_MATCH_WAIT_STEPS[stepIndex.value]?.label || "正在匹配");

  function start() {
    stop();
    startedAt = performance.now();
    elapsedMs.value = 0;
    timerId = setInterval(() => {
      elapsedMs.value = performance.now() - startedAt;
    }, 100);
  }

  function stop() {
    if (timerId != null) {
      clearInterval(timerId);
      timerId = null;
    }
    if (startedAt) {
      elapsedMs.value = performance.now() - startedAt;
    }
  }

  function reset() {
    stop();
    elapsedMs.value = 0;
    startedAt = 0;
  }

  onBeforeUnmount(() => {
    if (timerId != null) clearInterval(timerId);
  });

  return { elapsedMs, elapsedLabel, stepIndex, stepLabel, isRunning, start, stop, reset };
}
