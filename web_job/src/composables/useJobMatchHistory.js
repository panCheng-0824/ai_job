/**
 * 学生智能匹配历史：从 server_job 分页加载/保存，切换历史记录恢复展示态。
 */
import { ref } from "vue";
import { apiGet, apiPost, invalidateCache } from "../api/client";
import { cloneDefaultScoreDimensions } from "../constants/jobScoreRubric";
import { normalizeMatchApiResponse } from "../utils/jobDedupe";

export const HISTORY_PAGE_SIZE = 8;

export function useJobMatchHistory() {
  const historyItems = ref([]);
  const activeHistoryId = ref(null);
  const historyLoading = ref(false);
  const historyLoadingMore = ref(false);
  const historyPage = ref(1);
  const historyTotal = ref(0);
  const historyHasMore = ref(false);

  function getStudentId() {
    if (typeof window === "undefined") return "";
    return (localStorage.getItem("student_id") || "").trim();
  }

  function applyPaginationMeta(data, page) {
    historyPage.value = Number(data?.page) || page;
    historyTotal.value = Number(data?.total) || 0;
    historyHasMore.value = Boolean(data?.has_more);
  }

  /** 将历史记录中的 settings 写回表单 refs */
  function applySettingsToForm(record, form) {
    const settings = record?.settings || {};
    if (settings.query != null) form.query.value = String(settings.query);
    if (settings.use_student_profile != null) {
      form.useStudentProfile.value = Boolean(settings.use_student_profile);
    }
    if (settings.use_semantic_cache != null) {
      form.useSemanticCache.value = Boolean(settings.use_semantic_cache);
    }
    if (settings.score_baseline != null) {
      form.scoreBaseline.value = Number(settings.score_baseline);
    }
    if (settings.min_recommend_score != null) {
      form.minRecommendScore.value = Number(settings.min_recommend_score);
    }
    if (settings.top_n_jobs != null) {
      form.topNJobs.value = Number(settings.top_n_jobs);
    }
    if (settings.score_dimensions && typeof settings.score_dimensions === "object") {
      form.scoreDimensions.value = {
        ...cloneDefaultScoreDimensions(),
        ...settings.score_dimensions
      };
    }
  }

  /** 将历史记录应用到岗位展示 refs */
  function applyRecordToView(record, view) {
    if (!record) return false;
    const normalized = normalizeMatchApiResponse({
      jobs: Array.isArray(record.jobs) ? record.jobs : [],
      recommendation: record.recommendation || null
    });
    view.jobs.value = normalized.jobs || [];
    view.recommendation.value = normalized.recommendation || null;
    if (view.companies) view.companies.value = [];
    if (view.ragInfo) view.ragInfo.value = null;
    if (view.matchCacheMeta) view.matchCacheMeta.value = null;
    if (view.recommendSearched) view.recommendSearched.value = true;
    activeHistoryId.value = record.id ?? null;
    return true;
  }

  function buildSettingsPayload(form) {
    return {
      query: form.query.value.trim(),
      use_student_profile: form.useStudentProfile.value,
      use_semantic_cache: form.useSemanticCache.value,
      score_baseline: form.scoreBaseline.value,
      min_recommend_score: form.minRecommendScore.value,
      top_n_jobs: form.topNJobs.value,
      score_dimensions: form.buildScoreDimensionsPayload()
    };
  }

  async function fetchHistoryPage(page) {
    const sid = getStudentId();
    if (!sid) return null;
    const q = new URLSearchParams({
      student_id: sid,
      page: String(page),
      page_size: String(HISTORY_PAGE_SIZE)
    });
    return apiGet(`/api/me/job-match-history?${q}`);
  }

  /** 加载第一页（重置列表） */
  async function loadHistory() {
    const sid = getStudentId();
    if (!sid) {
      historyItems.value = [];
      historyTotal.value = 0;
      historyHasMore.value = false;
      historyPage.value = 1;
      return [];
    }
    historyLoading.value = true;
    try {
      const data = await fetchHistoryPage(1);
      historyItems.value = data?.items || [];
      applyPaginationMeta(data, 1);
      return historyItems.value;
    } catch {
      historyItems.value = [];
      historyTotal.value = 0;
      historyHasMore.value = false;
      historyPage.value = 1;
      return [];
    } finally {
      historyLoading.value = false;
    }
  }

  /** 滚动触底加载下一页 */
  async function loadMoreHistory() {
    if (historyLoading.value || historyLoadingMore.value || !historyHasMore.value) {
      return [];
    }
    historyLoadingMore.value = true;
    try {
      const nextPage = historyPage.value + 1;
      const data = await fetchHistoryPage(nextPage);
      const batch = data?.items || [];
      if (batch.length) {
        const seen = new Set(historyItems.value.map((item) => String(item.id)));
        historyItems.value = [
          ...historyItems.value,
          ...batch.filter((item) => !seen.has(String(item.id)))
        ];
      }
      applyPaginationMeta(data, nextPage);
      return batch;
    } catch {
      return [];
    } finally {
      historyLoadingMore.value = false;
    }
  }

  async function saveHistory({ query, settings, jobs, recommendation }) {
    const sid = getStudentId();
    if (!sid || !Array.isArray(jobs) || jobs.length === 0) return null;
    try {
      const data = await apiPost("/api/me/job-match-history", {
        student_id: sid,
        query: String(query || "").trim(),
        settings: settings || {},
        jobs,
        recommendation: recommendation || null
      });
      invalidateCache("/api/me/job-match-history");
      historyItems.value = data?.items || [];
      applyPaginationMeta(data, 1);
      const saved = data?.record;
      if (saved?.id != null) {
        activeHistoryId.value = saved.id;
      }
      return saved;
    } catch {
      return null;
    }
  }

  function selectHistory(record, form, view) {
    if (!record) return;
    applySettingsToForm(record, form);
    applyRecordToView(record, view);
  }

  return {
    historyItems,
    activeHistoryId,
    historyLoading,
    historyLoadingMore,
    historyTotal,
    historyHasMore,
    loadHistory,
    loadMoreHistory,
    saveHistory,
    selectHistory,
    applySettingsToForm,
    applyRecordToView,
    buildSettingsPayload
  };
}
