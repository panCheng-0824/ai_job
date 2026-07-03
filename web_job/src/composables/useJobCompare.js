import { computed, ref } from "vue";
import { normalizeJobId } from "../utils/jobId";

const MAX_COMPARE = 3;
const compareIds = ref(new Set());

export function useJobCompare() {
  const compareList = computed(() => [...compareIds.value]);
  const compareCount = computed(() => compareIds.value.size);

  function isSelected(jobId) {
    return compareIds.value.has(normalizeJobId(jobId));
  }

  function toggleCompare(jobId) {
    const id = normalizeJobId(jobId);
    if (!id) return;
    const next = new Set(compareIds.value);
    if (next.has(id)) {
      next.delete(id);
    } else if (next.size < MAX_COMPARE) {
      next.add(id);
    }
    compareIds.value = next;
  }

  function clearCompare() {
    compareIds.value = new Set();
  }

  function removeCompare(jobId) {
    const next = new Set(compareIds.value);
    next.delete(normalizeJobId(jobId));
    compareIds.value = next;
  }

  return { compareList, compareCount, isSelected, toggleCompare, clearCompare, removeCompare, maxCompare: MAX_COMPARE };
}
