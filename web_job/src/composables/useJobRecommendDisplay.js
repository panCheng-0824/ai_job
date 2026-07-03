import { computed, ref, watch } from "vue";
import { resolveJobMatchReasonDisplay } from "../utils/jobMatchReason";
import { normalizeJobId, sameJobId } from "../utils/jobId";

export { normalizeJobId, sameJobId };

const EMPTY_REASON = Object.freeze({
  reason: "",
  sections: [],
  charCount: 0,
  score: null
});

export function findJobById(list, id) {
  const target = normalizeJobId(id);
  if (!target) return null;
  return (list || []).find((j) => sameJobId(j.job_id, target)) || null;
}

/**
 * 岗位列表 + 推荐理由联动（StudentView / JobRecommendPanel 共用）。
 * @param {() => Array} getJobs
 * @param {() => object|null} getRecommendation
 * @param {{ autoSync?: boolean }} [options]
 */
export function useJobRecommendDisplay(getJobs, getRecommendation, options = {}) {
  const { autoSync = true } = options;
  const displayJobId = ref(null);
  const hoverJobId = ref(null);

  function pinJobForReason(job) {
    const id = normalizeJobId(job?.job_id);
    if (!id) return;
    displayJobId.value = id;
  }

  function onJobCardHover(job, options = {}) {
    const { previewOnly = false } = options;
    const id = normalizeJobId(job?.job_id);
    hoverJobId.value = id || null;
    if (!previewOnly) {
      pinJobForReason(job);
    }
  }

  function onJobCardLeave() {
    hoverJobId.value = null;
  }

  function syncDisplayJobFromList(list) {
    const jobs = list || [];
    if (!jobs.length) {
      displayJobId.value = null;
      return;
    }
    const current = displayJobId.value;
    if (current && jobs.some((j) => sameJobId(j.job_id, current))) {
      displayJobId.value = normalizeJobId(current);
      return;
    }
    pinJobForReason(jobs[0]);
  }

  function resetDisplayJob() {
    displayJobId.value = null;
    hoverJobId.value = null;
  }

  const previewJob = computed(() => findJobById(getJobs(), displayJobId.value));

  const selectedReasonMeta = computed(() => {
    const job = previewJob.value;
    if (!job) return EMPTY_REASON;
    const rec = getRecommendation()?.recommended_jobs || [];
    const hit = rec.find((x) => sameJobId(x.job_id, job.job_id));
    return resolveJobMatchReasonDisplay(hit, job);
  });

  const reasonReady = computed(
    () =>
      Boolean(previewJob.value) &&
      Boolean(selectedReasonMeta.value.reason || selectedReasonMeta.value.sections?.length)
  );

  if (autoSync) {
    watch(
      () => getJobs(),
      (list) => syncDisplayJobFromList(list),
      { deep: true, immediate: true }
    );
  }

  return {
    displayJobId,
    hoverJobId,
    previewJob,
    selectedReasonMeta,
    reasonReady,
    pinJobForReason,
    onJobCardHover,
    onJobCardLeave,
    syncDisplayJobFromList,
    resetDisplayJob,
    sameJobId,
    normalizeJobId
  };
}
