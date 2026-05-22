import { ref } from "vue";

/** @type {Set<(payload: Record<string, unknown>) => void>} */
const subscribers = new Set();

/** 简历页未打开时暂存，进入 ResumeCreateView 后自动消费 */
export const pendingResumeRenderRef = ref(null);

/**
 * 分发 resume_render 载荷；已挂载的简历编辑器会立即合并。
 * @param {Record<string, unknown> | null | undefined} payload
 */
export function dispatchResumeRender(payload) {
  if (!payload || typeof payload !== "object") return;
  const snap = { ...payload };
  let delivered = false;
  for (const fn of subscribers) {
    try {
      fn(snap);
      delivered = true;
    } catch (e) {
      console.warn("resume_render subscriber failed", e);
    }
  }
  if (!delivered) {
    pendingResumeRenderRef.value = snap;
  } else {
    pendingResumeRenderRef.value = null;
  }
}

/**
 * 简历创建页订阅：返回取消函数。
 * @param {(payload: Record<string, unknown>) => void} handler
 */
export function subscribeResumeRender(handler) {
  subscribers.add(handler);
  const pending = pendingResumeRenderRef.value;
  if (pending) {
    handler(pending);
    pendingResumeRenderRef.value = null;
  }
  return () => subscribers.delete(handler);
}
