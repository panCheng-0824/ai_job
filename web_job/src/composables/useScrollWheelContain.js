import { onBeforeUnmount, toValue, watch } from "vue";

/**
 * 将滚轮滚动限制在容器内，避免滚动链传递到页面或其他模块。
 * @param {import('vue').Ref<HTMLElement|null>} scrollRef
 * @param {import('vue').MaybeRefOrGetter<boolean>} enabled
 */
export function useScrollWheelContain(scrollRef, enabled = () => true) {
  let boundEl = null;

  function isEnabled() {
    return Boolean(toValue(enabled));
  }

  function onWheel(e) {
    if (!isEnabled()) return;
    const el = scrollRef.value;
    if (!el || el !== boundEl) return;

    const { scrollTop, scrollHeight, clientHeight } = el;
    const maxScroll = scrollHeight - clientHeight;
    if (maxScroll <= 1) return;

    const delta = e.deltaY;
    if (delta === 0) return;

    const scrollingDown = delta > 0;
    const scrollingUp = delta < 0;

    if (scrollingDown && scrollTop < maxScroll - 1) {
      e.stopPropagation();
      return;
    }
    if (scrollingUp && scrollTop > 0) {
      e.stopPropagation();
      return;
    }

    e.preventDefault();
    e.stopPropagation();
  }

  function bind(el) {
    if (!el || boundEl === el) return;
    unbind();
    boundEl = el;
    boundEl.addEventListener("wheel", onWheel, { passive: false });
  }

  function unbind() {
    if (!boundEl) return;
    boundEl.removeEventListener("wheel", onWheel);
    boundEl = null;
  }

  watch(
    scrollRef,
    (el) => {
      unbind();
      if (el) bind(el);
    },
    { immediate: true, flush: "post" }
  );

  onBeforeUnmount(unbind);

  return { bind, unbind };
}
