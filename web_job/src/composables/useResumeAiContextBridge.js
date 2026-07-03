import { ref } from "vue";

/** @type {Set<(item: Record<string, unknown>) => void>} */
const subscribers = new Set();

/** 简历页 AI 栏未挂载时暂存，进入 ResumeAiOptimizeRail 后自动消费 */
export const pendingResumeAiContextRef = ref(null);

/**
 * 将岗位/企业素材送入优化素材篮。
 * @param {Record<string, unknown> | null | undefined} item
 */
export function dispatchResumeAiContext(item) {
  if (!item || typeof item !== "object" || !item.kind || !item.refId) return;
  const snap = { ...item };
  let delivered = false;
  for (const fn of subscribers) {
    try {
      fn(snap);
      delivered = true;
    } catch (e) {
      console.warn("resume_ai_context subscriber failed", e);
    }
  }
  if (!delivered) {
    pendingResumeAiContextRef.value = snap;
  } else {
    pendingResumeAiContextRef.value = null;
  }
}

/**
 * AI 优化栏订阅素材带入；返回取消函数。
 * @param {(item: Record<string, unknown>) => void} handler
 */
export function subscribeResumeAiContext(handler) {
  subscribers.add(handler);
  const pending = pendingResumeAiContextRef.value;
  if (pending) {
    handler(pending);
    pendingResumeAiContextRef.value = null;
  }
  return () => subscribers.delete(handler);
}
