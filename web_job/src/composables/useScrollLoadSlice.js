/**
 * 下滑递增切片 — 首屏展示 batchSize 条，滚至底部 sentinel 再加载下一批（客户端分页）。
 */
import { computed, onBeforeUnmount, onMounted, ref, unref, watch } from "vue";

/**
 * @param {import('vue').Ref<Array>|import('vue').ComputedRef<Array>} itemsSource
 * @param {number} batchSize 每批加载条数
 */
export function useScrollLoadSlice(itemsSource, batchSize = 12) {
  const visibleCount = ref(batchSize);

  const total = computed(() => (unref(itemsSource) || []).length);
  const slice = computed(() => (unref(itemsSource) || []).slice(0, visibleCount.value));
  const hasMore = computed(() => visibleCount.value < total.value);
  const progressLabel = computed(() => {
    const t = total.value;
    if (!t) return "0 题";
    const shown = Math.min(visibleCount.value, t);
    return `已展示 ${shown} / ${t} 题`;
  });

  watch(total, (t) => {
    if (t === 0) {
      visibleCount.value = batchSize;
      return;
    }
    if (visibleCount.value > t) {
      visibleCount.value = Math.min(batchSize, t);
    }
  });

  function loadMore() {
    if (!hasMore.value) return;
    visibleCount.value = Math.min(total.value, visibleCount.value + batchSize);
  }

  /** 新增题目后确保最后一题可见 */
  function revealAll() {
    visibleCount.value = Math.max(batchSize, total.value);
  }

  function resetVisible() {
    visibleCount.value = batchSize;
  }

  return {
    slice,
    hasMore,
    progressLabel,
    loadMore,
    revealAll,
    resetVisible,
    batchSize
  };
}

/**
 * 绑定 IntersectionObserver：滚动容器内 sentinel 进入视口时触发 loadMore。
 *
 * @param {import('vue').Ref<HTMLElement|null>} rootRef 可滚动容器；null 时用视口
 * @param {import('vue').Ref<HTMLElement|null>} sentinelRef 底部哨兵元素
 * @param {{ hasMore: import('vue').Ref<boolean>|import('vue').ComputedRef<boolean>, loadMore: () => void }} opts
 */
export function useScrollLoadSentinel(rootRef, sentinelRef, { hasMore, loadMore }) {
  let observer = null;

  function disconnect() {
    observer?.disconnect();
    observer = null;
  }

  function connect() {
    disconnect();
    const sentinel = sentinelRef.value;
    if (!sentinel) return;
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting) && unref(hasMore)) {
          loadMore();
        }
      },
      { root: rootRef.value || null, rootMargin: "100px 0px", threshold: 0.01 }
    );
    observer.observe(sentinel);
  }

  onMounted(connect);
  onBeforeUnmount(disconnect);
  watch([rootRef, sentinelRef], connect);
}
