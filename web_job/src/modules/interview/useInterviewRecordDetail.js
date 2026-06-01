/**
 * 面试记录详情页数据加载与派生状态。
 */
import { computed, ref, watch } from "vue";
import { getStudentId } from "../../api/client";
import { fetchInterviewRecordAnswers, fetchInterviewRecordDetail } from "./api";
import { formatProgressPercent } from "./formatters";

/**
 * @param {import('vue').Ref<string|undefined>} recordIdRef 路由 recordId
 */
export function useInterviewRecordDetail(recordIdRef) {
  const detail = ref(null);
  const answers = ref([]);
  const loadError = ref("");
  const loading = ref(false);

  const progressPercent = computed(() =>
    formatProgressPercent(detail.value?.question_answered, detail.value?.question_total)
  );

  const answeredCount = computed(() => {
    const n = Number(detail.value?.question_answered);
    if (!Number.isNaN(n) && n >= 0) return n;
    return answers.value.filter((a) => a.answer_status && a.answer_status !== "pending").length;
  });

  async function load() {
    const sid = getStudentId();
    const recordId = recordIdRef.value;
    if (!sid || !recordId) {
      detail.value = null;
      answers.value = [];
      loadError.value = "请先登录";
      return;
    }
    loading.value = true;
    loadError.value = "";
    try {
      const [d, a] = await Promise.all([
        fetchInterviewRecordDetail(sid, recordId),
        fetchInterviewRecordAnswers(sid, recordId)
      ]);
      detail.value = d;
      answers.value = a.items || [];
    } catch (e) {
      detail.value = null;
      answers.value = [];
      loadError.value = e.message || "加载失败";
    } finally {
      loading.value = false;
    }
  }

  watch(recordIdRef, load, { immediate: true });

  return {
    detail,
    answers,
    loadError,
    loading,
    progressPercent,
    answeredCount,
    reload: load
  };
}
