/**
 * 列表分页切片 — 题目卡片等大数据量场景的下翻分页。
 */
import { computed, ref, unref, watch } from "vue";

/**
 * @param {import('vue').Ref<Array>|import('vue').ComputedRef<Array>} itemsSource
 * @param {number} pageSize
 */
export function usePaginatedSlice(itemsSource, pageSize = 12) {
  const page = ref(1);
  const size = pageSize;

  const total = computed(() => (unref(itemsSource) || []).length);
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size)));

  const slice = computed(() => {
    const items = unref(itemsSource) || [];
    const start = (page.value - 1) * size;
    return items.slice(start, start + size);
  });

  const rangeLabel = computed(() => {
    if (!total.value) return "0 条";
    const start = (page.value - 1) * size + 1;
    const end = Math.min(page.value * size, total.value);
    return `${start}–${end} / ${total.value}`;
  });

  watch(total, () => {
    if (page.value > totalPages.value) page.value = totalPages.value;
  });

  function goTo(p) {
    page.value = Math.min(totalPages.value, Math.max(1, p));
  }

  function resetPage() {
    page.value = 1;
  }

  return { page, totalPages, slice, rangeLabel, goTo, resetPage, pageSize: size };
}
