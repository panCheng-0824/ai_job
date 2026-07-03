<script setup>
/**
 * 登录后首页：智能匹配职位 + 边框折叠侧栏（画像速览 / 右侧双抽屉：推荐理由·匹配记录）。
 * 「学生画像」tab 展示完整档案明细。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiPost } from "../api/client";
import FloatingFramePanel from "../components/FloatingFramePanel.vue";
import JobMatchReasonBlocks from "../components/JobMatchReasonBlocks.vue";
import CollapsibleSideRail from "../components/layout/CollapsibleSideRail.vue";
import HomeRightDualRail from "../components/home/HomeRightDualRail.vue";
import JobCompareBar from "../components/jobs/JobCompareBar.vue";
import JobCompareModal from "../components/jobs/JobCompareModal.vue";
import JobsMatchSettingsPanel from "../components/jobs/JobsMatchSettingsPanel.vue";
import HomeMatchHistoryTimeline from "../components/home/HomeMatchHistoryTimeline.vue";
import HomeMatchedJobsSection from "../components/home/HomeMatchedJobsSection.vue";
import HomeProfileOverview from "../components/home/HomeProfileOverview.vue";
import HomeTopBar from "../components/home/HomeTopBar.vue";
import StudentProfileDetailPanel from "../components/home/StudentProfileDetailPanel.vue";
import { embedUrl, fullPageUrl } from "../utils/embedFrame";
import {
  SCORE_DIMENSION_DEFS,
  clampDimensionScore,
  cloneDefaultScoreDimensions
} from "../constants/jobScoreRubric";
import { useJobMatchWaitTimer } from "../composables/useJobMatchWaitTimer";
import { useJobCompare } from "../composables/useJobCompare";
import { useJobMatchHistory } from "../composables/useJobMatchHistory";
import { useJobApplication } from "../composables/useJobApplication";
import { useJobInterviewBooking } from "../composables/useJobInterviewBooking";
import { openResumeWithJobContext } from "../composables/openResumeWithJobContext";
import { openInterviewCenterWithJob } from "../composables/openInterviewCenterWithJob";
import { pickJobsForCompare } from "../utils/jobCompareDisplay";
import { normalizeMatchApiResponse } from "../utils/jobDedupe";
import { PROFILE_SEC, useStudentProfile as useStudentProfileApi } from "../composables/useStudentProfile";
import { maskName, maskOrgText, maskEducation } from "../utils/studentDesensitize";

const route = useRoute();
const router = useRouter();
const {
  profile: studentPortrait,
  saving: profileSaving,
  error: profileError,
  studentInfo,
  awardInfoList,
  jobIntent,
  abilityTags,
  suggestedTags,
  radarValues,
  intentDisplayText,
  loadProfile,
  saveContact,
  saveJobIntent,
  saveAbility,
  uploadAvatar,
  contactToForm,
  jobIntentToForm,
  abilityToForm
} = useStudentProfileApi();
const { applyToJob, loadAppliedJobIds } = useJobApplication();
const { loadBookedJobIds } = useJobInterviewBooking();
const profileDetailRef = ref(null);
const summary = ref(null);
const favorites = ref({ jobs: [] });
const applyNotice = ref("");
const interviewNotice = ref("");

const { compareList, compareCount, clearCompare, maxCompare, removeCompare } = useJobCompare();
const {
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
} = useJobMatchHistory();
const compareOpen = ref(false);
const compareJobs = ref([]);
const profilePanelOpen = ref(true);
/** null | 'reason' | 'history'，互斥仅展开一个 */
const rightPanelActive = ref(null);
const matchedSectionRef = ref(null);

function openCompare() {
  compareJobs.value = pickJobsForCompare(jobs.value, compareList.value, recommendation.value);
  compareOpen.value = true;
}

const comparePreviewJobs = computed(() =>
  pickJobsForCompare(jobs.value, compareList.value, recommendation.value)
);

function onCompareRemove(jobId) {
  removeCompare(jobId);
  compareJobs.value = pickJobsForCompare(jobs.value, compareList.value, recommendation.value);
  if (compareJobs.value.length < 2) {
    compareOpen.value = false;
  }
}

const regionFilter = ref("");
const salaryFilter = ref("");
const sortFilter = ref("score");
const error = ref("");
const query = ref("");
const jobs = ref([]);
const companies = ref([]);
const loading = ref(false);
const matchWait = useJobMatchWaitTimer();
const { elapsedMs: matchElapsedMs, start: startMatchWait, stop: stopMatchWait } = matchWait;
const lastMatchDurationMs = ref(null);
const historyBootstrapped = ref(false);
const recommendSearched = ref(false);
const ragInfo = ref(null);
const recommendation = ref(null);
const useSemanticCache = ref(true);
const useStudentProfile = ref(true);
const scoreBaseline = ref(85);
const minRecommendScore = ref(85);
const topNJobs = ref(9);
const scoreDimensions = ref(cloneDefaultScoreDimensions());
const scoreDimensionDefs = SCORE_DIMENSION_DEFS;
const matchCacheMeta = ref(null);
const cacheBannerDismissed = ref(false);

function clampScore(value, fallback = 85) {
  const n = Number.parseInt(String(value), 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.min(100, n));
}

function clampTopN(value, fallback = 5) {
  const n = Number.parseInt(String(value), 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(1, Math.min(20, n));
}

function buildScoreDimensionsPayload() {
  const out = {};
  for (const dim of scoreDimensionDefs) {
    out[dim.key] = clampDimensionScore(
      scoreDimensions.value[dim.key],
      cloneDefaultScoreDimensions()[dim.key]
    );
  }
  return out;
}

function buildStudentContextFromPortrait() {
  const s = studentInfo.value || {};
  return [
    s["专业名称"] && `专业：${s["专业名称"]}`,
    s["学历"] && `学历：${s["学历"]}`,
    s["毕业年度"] && `毕业届别：${s["毕业年度"]}`,
    s["学校名称"] && `学校：${s["学校名称"]}`,
    s["院系名称"] && `院系：${s["院系名称"]}`
  ]
    .filter(Boolean)
    .join("；");
}

const cacheHitActive = computed(() => Boolean(matchCacheMeta.value?.hit));

const cacheHitTitle = computed(() => {
  const c = matchCacheMeta.value;
  if (!c?.hit) return "";
  if (c.type === "exact") return "缓存命中 · 精确匹配";
  if (c.type === "semantic") return "缓存命中 · 语义相似";
  return "缓存命中";
});

const cacheHitDetail = computed(() => {
  const c = matchCacheMeta.value;
  if (!c?.hit) return "";
  const parts = [];
  if (c.type === "semantic" && c.similarity != null) {
    const pct = (Number(c.similarity) * 100).toFixed(1);
    const th = c.threshold != null ? (Number(c.threshold) * 100).toFixed(0) : null;
    parts.push(`相似度 ${pct}%${th != null ? `（阈值 ≥ ${th}%）` : ""}`);
  } else if (c.type === "exact") {
    parts.push("改写检索句与历史请求完全一致");
  }
  if (c.cached_rag_q) {
    parts.push(`历史检索句：${c.cached_rag_q}`);
  }
  if (c.scope) {
    parts.push(`分区 ${c.scope}`);
  }
  return parts.join(" · ");
});

const jobDetailFrameOpen = ref(false);
const jobDetailFrameFullscreen = ref(false);
const jobDetailFrameTitle = ref("");
const jobDetailIframeSrc = ref("");

function closeJobDetailFrame() {
  jobDetailFrameOpen.value = false;
  jobDetailFrameFullscreen.value = false;
  jobDetailFrameTitle.value = "";
  jobDetailIframeSrc.value = "";
}

function openJobDetailFrame(job) {
  if (!job?.job_id) return;
  const id = encodeURIComponent(String(job.job_id).trim());
  jobDetailFrameTitle.value = job.job_title || job.job_name || job.job_id || "岗位详情";
  jobDetailIframeSrc.value = embedUrl(`/jobs/${id}`);
  jobDetailFrameOpen.value = true;
  jobDetailFrameFullscreen.value = false;
}

function toggleJobDetailFullscreen() {
  jobDetailFrameFullscreen.value = !jobDetailFrameFullscreen.value;
}

function openJobDetailFullWindow() {
  if (!jobDetailIframeSrc.value) return;
  window.open(fullPageUrl(jobDetailIframeSrc.value), "_blank", "noopener,noreferrer");
}

function onJobDetailDocKey(ev) {
  if (ev.key === "Escape" && jobDetailFrameOpen.value) {
    closeJobDetailFrame();
  }
}

const SEC = PROFILE_SEC;

const isProfileTab = computed(() => route.query.tab === "profile");
const pageTitle = computed(() => (isProfileTab.value ? "学生画像" : "首页"));
const pageSubtitle = computed(() => {
  if (isProfileTab.value) {
    const major = maskOrgText(studentInfo.value["专业名称"]);
    return major
      ? `查看与维护 ${major} 方向的完整档案`
      : "查看与维护你的完整学生档案";
  }
  return intentText.value ? `当前意向：${intentText.value}` : "";
});
const studentDisplayName = computed(() => maskName(studentInfo.value["姓名"]) || "");
const intentText = intentDisplayText;

const applicationCount = computed(() => {
  const n = summary.value?.application_count;
  return Number.isFinite(Number(n)) ? Number(n) : 0;
});

function buildDefaultQuery() {
  const s = studentInfo.value || {};
  const major = s["专业名称"] || "对口";
  const edu = s["学历"] || "";
  return `想找${major}${edu ? `（${edu}）` : ""}相关岗位，薪资合理、发展稳定`;
}

const fullPortraitJson = computed(() => {
  if (!studentPortrait.value) return "";
  return JSON.stringify(studentPortrait.value, null, 2);
});

const baseFields = computed(() => {
  const s = studentInfo.value;
  return [
    { label: "学号", value: s["学号"] },
    { label: "姓名", value: s["姓名"] },
    { label: "性别", value: s["性别"] },
    { label: "民族", value: s["民族"] },
    { label: "出生日期", value: s["出生日期"] },
    { label: "证件号", value: s["证件号"] },
    { label: "学校名称", value: s["学校名称"] },
    { label: "院系名称", value: s["院系名称"] },
    { label: "专业名称", value: s["专业名称"] },
    { label: "班级名称", value: s["班级名称"] },
    { label: "学历", value: s["学历"] },
    { label: "毕业年度", value: s["毕业年度"] },
    { label: "毕业季节", value: s["毕业季节"] },
    { label: "平均绩点", value: s["平均绩点"] },
    { label: "体测成绩", value: s["体测成绩"] },
    { label: "手机", value: s["手机"] },
    { label: "邮箱", value: s["邮箱"] }
  ];
});

function getStudentIdFromRoute() {
  return route.query.student_id || localStorage.getItem("student_id") || "";
}

async function loadStudent() {
  const sid = getStudentIdFromRoute();
  if (!sid) return;
  try {
    error.value = "";
    await loadProfile(sid);
    if (profileError.value) {
      error.value = profileError.value;
    }
  } catch (err) {
    error.value = err.message;
  }
}

async function loadSummary() {
  const sid = getStudentIdFromRoute();
  if (!sid) return;
  try {
    const q = new URLSearchParams({ student_id: sid });
    const [sum, fav] = await Promise.all([
      apiGet(`/api/me/summary?${q}`),
      apiGet(`/api/me/favorites?${q}`)
    ]);
    summary.value = sum;
    favorites.value = fav || { jobs: [] };
    await loadAppliedJobIds(sid);
    await loadBookedJobIds(sid);
  } catch {
    summary.value = null;
    favorites.value = { jobs: [] };
  }
}

function onSemCacheCleared() {
  matchCacheMeta.value = null;
  cacheBannerDismissed.value = true;
}

async function runRecommend(customQuery) {
  const qText = String(customQuery ?? query.value).trim();
  if (!qText) {
    error.value = "请输入岗位诉求后再查询";
    return;
  }
  query.value = qText;
  loading.value = true;
  lastMatchDurationMs.value = null;
  matchCacheMeta.value = null;
  cacheBannerDismissed.value = false;
  ragInfo.value = null;
  recommendation.value = null;
  startMatchWait();
  try {
    error.value = "";
    const studentContext = useStudentProfile.value ? buildStudentContextFromPortrait() : "";
    const data = normalizeMatchApiResponse(
      await apiPost("/api/skills/job-info-query", {
      query: query.value.trim(),
      top_n_jobs: clampTopN(topNJobs.value),
      top_n_companies: 5,
      use_rag: true,
      use_semantic_cache: useSemanticCache.value,
      use_student_profile: useStudentProfile.value,
      student_context: studentContext,
      score_baseline: clampScore(scoreBaseline.value),
      min_recommend_score: clampScore(minRecommendScore.value),
      score_dimensions: buildScoreDimensionsPayload()
      })
    );
    jobs.value = data.jobs || [];
    companies.value = data.companies || [];
    ragInfo.value = data.rag || null;
    recommendation.value = data.recommendation || null;
    matchCacheMeta.value = data.cache && typeof data.cache === "object" ? data.cache : null;
    recommendSearched.value = true;

    if (jobs.value.length > 0) {
      const settings = buildSettingsPayload({
        query,
        useStudentProfile,
        useSemanticCache,
        scoreBaseline,
        minRecommendScore,
        topNJobs,
        buildScoreDimensionsPayload
      });
      await saveHistory({
        query: query.value.trim(),
        settings,
        jobs: jobs.value,
        recommendation: recommendation.value
      });
    }
  } catch (err) {
    error.value = err.message;
    matchCacheMeta.value = null;
    recommendSearched.value = true;
  } finally {
    stopMatchWait();
    lastMatchDurationMs.value = matchElapsedMs.value;
    loading.value = false;
  }
}

const matchFormRefs = {
  query,
  useStudentProfile,
  useSemanticCache,
  scoreBaseline,
  minRecommendScore,
  topNJobs,
  scoreDimensions
};

const matchViewRefs = {
  jobs,
  recommendation,
  companies,
  ragInfo,
  matchCacheMeta,
  recommendSearched
};

function handleHistorySelect(record) {
  selectHistory(record, matchFormRefs, matchViewRefs);
}

async function bootstrapMatchHistory() {
  if (isProfileTab.value) {
    historyBootstrapped.value = true;
    return;
  }
  const items = await loadHistory();
  historyBootstrapped.value = true;
  if (items.length > 0) {
    const latest = items[0];
    applySettingsToForm(latest, matchFormRefs);
    applyRecordToView(latest, matchViewRefs);
    activeHistoryId.value = latest.id ?? null;
    return;
  }
  if (!query.value.trim()) {
    query.value = buildDefaultQuery();
  }
  recommendSearched.value = false;
}

onBeforeUnmount(() => {
  matchWait.reset();
  document.removeEventListener("keydown", onJobDetailDocKey);
});

async function copyJson() {
  if (!studentPortrait.value || !fullPortraitJson.value) return;
  try {
    await navigator.clipboard.writeText(fullPortraitJson.value);
  } catch (_) {
    error.value = "复制失败，请手动复制";
  }
}

async function handleSaveContact(payload) {
  try {
    await saveContact(payload);
    profileDetailRef.value?.closeDrawersOnSaved?.();
  } catch {
    error.value = profileError.value || "保存失败";
  }
}

async function handleSaveJobIntent(payload) {
  try {
    await saveJobIntent(payload);
    profileDetailRef.value?.closeDrawersOnSaved?.();
  } catch {
    error.value = profileError.value || "保存失败";
  }
}

async function handleSaveAbility(payload) {
  try {
    await saveAbility(payload);
    profileDetailRef.value?.closeDrawersOnSaved?.();
  } catch {
    error.value = profileError.value || "保存失败";
  }
}

async function handleAvatarUpload(file) {
  const sid = getStudentIdFromRoute();
  return uploadAvatar(file, sid);
}

function handleJobViewDetail(job) {
  if (!job?.job_id) return;
  openJobDetailFrame(job);
}

async function handleJobApply(job) {
  if (!job?.job_id && !job?.id) return;
  applyNotice.value = "";
  const result = await applyToJob(job, { studentId: getStudentIdFromRoute() });
  if (result.needLogin) {
    router.push("/login");
    return;
  }
  applyNotice.value = result.message;
  if (result.ok) {
    await loadSummary();
  }
}

function handleJobResume(job) {
  openResumeWithJobContext(job, router);
}

async function handleJobInterview(job) {
  if (!job?.job_id && !job?.id) return;
  interviewNotice.value = "";
  const result = await openInterviewCenterWithJob(job, router, {
    studentId: getStudentIdFromRoute()
  });
  if (result.needLogin) {
    router.push("/login");
    return;
  }
  if (!result.ok) {
    interviewNotice.value = result.message;
  }
}

async function bootstrapHome() {
  await Promise.all([loadStudent(), loadSummary()]);
  await bootstrapMatchHistory();
}

watch(
  () => route.query.tab,
  async (tab) => {
    if (tab === "profile") return;
    if (!historyBootstrapped.value) {
      await bootstrapMatchHistory();
    }
  }
);

onMounted(() => {
  bootstrapHome();
  document.addEventListener("keydown", onJobDetailDocKey);
});
</script>

<template>
  <div class="home-main" :class="{ 'home-main--dashboard': !isProfileTab }">
    <HomeTopBar
      :title="pageTitle"
      :subtitle="pageSubtitle"
      :student-name="studentDisplayName"
    />

    <StudentProfileDetailPanel
      v-if="isProfileTab"
      ref="profileDetailRef"
      :student-info="studentInfo"
      :base-fields="baseFields"
      :award-info-list="awardInfoList"
      :job-intent="jobIntent"
      :ability-tags="abilityTags"
      :suggested-tags="suggestedTags"
      :radar-values="radarValues"
      :contact-form="contactToForm()"
      :job-intent-form="jobIntentToForm()"
      :ability-form="abilityToForm()"
      :saving="profileSaving"
      :avatar-upload-handler="handleAvatarUpload"
      :summary="summary"
      :favorites="favorites.jobs || []"
      :intent-text="intentText"
      :error="error || profileError"
      @copy-json="copyJson"
      @view-job="handleJobViewDetail"
      @view-more="router.push('/jobs')"
      @save-contact="handleSaveContact"
      @save-job-intent="handleSaveJobIntent"
      @save-ability="handleSaveAbility"
    />

    <template v-else>
      <div class="home-dashboard home-dashboard--contain">
        <CollapsibleSideRail
          v-model:open="profilePanelOpen"
          side="left"
          title="画像速览"
          theme="profile"
          panel-width="292px"
        >
          <div class="rail-slot rail-slot--profile home-dual-slot--profile">
            <div class="rail-slot__scroll">
            <HomeProfileOverview
            :student-info="studentInfo"
            :award-list="awardInfoList"
            :application-count="applicationCount"
            :intent-text="intentText"
            :ability-tags="abilityTags"
            :radar-values="radarValues"
          />
            </div>
          </div>
        </CollapsibleSideRail>

        <main class="home-main-panel">
          <p v-if="error" class="home-error">{{ error }}</p>
          <p v-if="applyNotice" class="home-apply-notice">{{ applyNotice }}</p>
          <p v-if="interviewNotice" class="home-apply-notice home-interview-notice">{{ interviewNotice }}</p>

          <div
            v-if="recommendSearched && cacheHitActive && !loading && !cacheBannerDismissed"
            class="cache-hit-banner"
            role="status"
          >
            <span class="cache-hit-badge">{{ cacheHitTitle }}</span>
            <span v-if="cacheHitDetail" class="cache-hit-detail">{{ cacheHitDetail }}</span>
            <button type="button" class="cache-hit-close" aria-label="关闭" @click="cacheBannerDismissed = true">✕</button>
          </div>

          <section class="home-match-top">
            <JobsMatchSettingsPanel
              v-model:query="query"
              v-model:use-student-profile="useStudentProfile"
              v-model:use-semantic-cache="useSemanticCache"
              v-model:score-baseline="scoreBaseline"
              v-model:min-recommend-score="minRecommendScore"
              v-model:top-n-jobs="topNJobs"
              v-model:score-dimensions="scoreDimensions"
              :loading="loading"
              hint="拖动滑块调整参数后，点击「重新匹配」刷新首页推荐结果。"
              @run="runRecommend()"
              @cache-cleared="onSemCacheCleared"
            />
          </section>

          <div class="sort-tabs">
            <span class="sort-tabs-label">排序：</span>
            <button :class="{ active: sortFilter === 'score' }" @click="sortFilter = 'score'">评分优先</button>
            <button :class="{ active: sortFilter === 'salary' }" @click="sortFilter = 'salary'">薪资优先</button>
            <button :class="{ active: sortFilter === 'date' }" @click="sortFilter = 'date'">最新发布</button>
          </div>

          <div class="home-jobs-host">
            <HomeMatchedJobsSection
              ref="matchedSectionRef"
              v-model:region-filter="regionFilter"
              v-model:salary-filter="salaryFilter"
              v-model:sort-filter="sortFilter"
              :jobs="jobs"
              :recommendation="recommendation"
              :loading="loading"
              :history-loading="historyLoading && !historyBootstrapped"
              :searched="recommendSearched"
              :has-history="historyItems.length > 0"
              :show-reason-rail="false"
              :min-score="minRecommendScore"
              :match-elapsed-ms="matchElapsedMs"
              :last-match-duration-ms="lastMatchDurationMs"
              @view-detail="handleJobViewDetail"
              @apply="handleJobApply"
              @resume="handleJobResume"
              @interview="handleJobInterview"
              @refresh="runRecommend()"
              @view-more="router.push('/jobs')"
            />
          </div>
        </main>

        <HomeRightDualRail v-model:active="rightPanelActive" panel-width="300px">
          <template #reason>
            <section class="home-reason-panel rail-slot">
              <header class="home-reason-head rail-slot__head">
                <p class="home-reason-label">推荐理由</p>
                <h3>{{ matchedSectionRef?.reasonPanelTitle || "选择岗位查看理由" }}</h3>
                <p v-if="matchedSectionRef?.reasonCompany" class="home-reason-meta">
                  {{ matchedSectionRef.reasonCompany }}
                </p>
              </header>
              <div class="rail-slot__scroll">
                <JobMatchReasonBlocks
                  v-if="matchedSectionRef?.previewJob && matchedSectionRef?.reasonReady"
                  :reason="matchedSectionRef?.selectedReasonMeta?.reason"
                  :sections="matchedSectionRef?.selectedReasonMeta?.sections"
                  :score="matchedSectionRef?.selectedReasonMeta?.score"
                  :char-count="matchedSectionRef?.selectedReasonMeta?.charCount"
                />
                <div v-else-if="matchedSectionRef?.previewJob" class="home-reason-empty">
                  该岗位暂无结构化推荐理由，可查看岗位详情了解更多。
                </div>
                <div v-else class="home-reason-empty">
                  将鼠标移到岗位卡片上，或点击卡片选择岗位后查看推荐理由。
                </div>
                <p v-if="matchedSectionRef?.interactionHint" class="home-reason-hint">
                  {{ matchedSectionRef.interactionHint }}
                </p>
              </div>
              <div v-if="matchedSectionRef?.previewJob" class="rail-slot__foot">
                <button
                  type="button"
                  class="home-reason-detail-btn"
                  @click="handleJobViewDetail(matchedSectionRef.previewJob)"
                >
                  查看岗位详情
                </button>
              </div>
            </section>
          </template>
          <template #history>
            <div class="rail-slot home-dual-slot--history">
              <HomeMatchHistoryTimeline
                fill-height
                :items="historyItems"
                :active-id="activeHistoryId"
                :loading="historyLoading"
                :loading-more="historyLoadingMore"
                :total="historyTotal"
                :has-more="historyHasMore"
                @select="handleHistorySelect"
                @load-more="loadMoreHistory"
              />
            </div>
          </template>
        </HomeRightDualRail>
      </div>
    </template>
  </div>

  <button
    type="button"
    class="ai-assistant"
    title="AI 就业助手"
    aria-label="打开 AI 就业助手"
    @click="router.push('/student-chat')"
  >
    <span class="ai-assistant-glow" aria-hidden="true" />
    <svg viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <rect x="14" y="18" width="36" height="28" rx="10" fill="#5b6adf" />
      <circle cx="26" cy="32" r="4" fill="#fff" />
      <circle cx="38" cy="32" r="4" fill="#fff" />
      <path d="M24 40c3 3 13 3 16 0" stroke="#fff" stroke-width="2" stroke-linecap="round" />
      <path d="M32 10v8M20 14l4 6M44 14l-4 6" stroke="#818cf8" stroke-width="2" stroke-linecap="round" />
    </svg>
  </button>

  <Teleport to="body">
    <FloatingFramePanel
      :open="jobDetailFrameOpen"
      :fullscreen="jobDetailFrameFullscreen"
      :title="jobDetailFrameTitle"
      :z-index="13100"
      @backdrop-click="closeJobDetailFrame"
    >
      <template #actions>
        <button type="button" @click="toggleJobDetailFullscreen">
          {{ jobDetailFrameFullscreen ? "缩小" : "放大" }}
        </button>
        <button type="button" @click="openJobDetailFullWindow">完整页面</button>
        <button type="button" class="danger" @click="closeJobDetailFrame">关闭</button>
      </template>
      <iframe v-if="jobDetailIframeSrc" :title="jobDetailFrameTitle" :src="jobDetailIframeSrc" />
    </FloatingFramePanel>
  </Teleport>

  <JobCompareBar
    :count="compareCount"
    :max="maxCompare"
    :preview-jobs="comparePreviewJobs"
    @open="openCompare"
    @clear="clearCompare"
  />
  <JobCompareModal
    :open="compareOpen"
    :jobs="compareJobs"
    @close="compareOpen = false"
    @remove="onCompareRemove"
  />
</template>

<style scoped>
.home-dashboard {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 4px;
  align-items: start;
  width: 100%;
}
.home-main--dashboard {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-height: 100dvh;
  overflow: hidden;
  padding-bottom: 16px;
  box-sizing: border-box;
}
.home-dashboard--contain {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  align-items: start;
}
.home-main--dashboard .home-main-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.home-jobs-host {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.home-main-panel {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
  padding-top: 14px;
  box-sizing: border-box;
}
.home-match-top {
  margin-bottom: 10px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.92);
  flex-shrink: 0;
}
.home-dual-slot--history,
.home-dual-slot--profile {
  padding: 0;
  min-height: 0;
}
.home-dual-slot--history :deep(.history-timeline.card-panel) {
  border: none;
  box-shadow: none;
  background: transparent;
  padding: 0;
}
.home-dual-slot--profile :deep(.profile-card) {
  border: none;
  box-shadow: none;
  background: transparent;
}
.home-reason-panel {
  gap: 0;
}
.home-reason-head h3 {
  margin: 4px 0 0;
  font-size: 0.92rem;
  font-weight: 800;
  color: #0f172a;
}
.home-reason-label {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 700;
  color: #6366f1;
  letter-spacing: 0.04em;
}
.home-reason-meta {
  margin: 4px 0 0;
  font-size: 0.76rem;
  color: #64748b;
}
.home-reason-empty {
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.55;
}
.home-reason-hint {
  margin: 0;
  font-size: 0.74rem;
  color: #94a3b8;
}
.home-reason-detail-btn {
  align-self: flex-start;
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  color: #4338ca;
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}
.home-error {
  margin: 0 0 12px;
  color: var(--danger);
  font-size: 0.88rem;
  font-weight: 600;
  flex-shrink: 0;
}
.home-apply-notice {
  margin: 0 0 12px;
  color: #047857;
  font-size: 0.88rem;
  font-weight: 600;
  flex-shrink: 0;
}
.sort-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  flex-shrink: 0;
}
.sort-tabs-label {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 600;
  margin-right: 2px;
}
.sort-tabs button {
  padding: 4px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.sort-tabs button:hover {
  border-color: #c7d2fe;
  color: #4338ca;
}
.sort-tabs button.active {
  border-color: #6366f1;
  background: #eef2ff;
  color: #4338ca;
}
.cache-hit-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #a7f3d0;
  background: linear-gradient(180deg, #ecfdf5, #f0fdf4);
  font-size: 0.84rem;
  flex-shrink: 0;
}
.cache-hit-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: #059669;
  color: #fff;
  font-weight: 700;
  font-size: 0.78rem;
}
.cache-hit-detail {
  color: #047857;
  font-weight: 600;
}
.cache-hit-close {
  margin-left: auto;
  padding: 2px 6px;
  border: none;
  background: none;
  color: #9ca3af;
  font-size: 0.8rem;
  cursor: pointer;
  line-height: 1;
}
.cache-hit-close:hover {
  color: #475569;
}
.ai-assistant {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 58px;
  height: 58px;
  border: none;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  z-index: 200;
  padding: 0;
}
.ai-assistant svg {
  width: 58px;
  height: 58px;
  filter: drop-shadow(0 8px 20px rgba(91, 106, 223, 0.35));
}
.ai-assistant-glow {
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(129, 140, 248, 0.35), transparent 70%);
  animation: ai-pulse 2.4s ease-in-out infinite;
}
@keyframes ai-pulse {
  0%, 100% { opacity: 0.55; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.06); }
}
@media (max-width: 1100px) {
  .home-dashboard {
    grid-template-columns: 1fr;
  }
  .home-main--dashboard {
    height: auto;
    max-height: none;
    overflow: visible;
  }
  .home-dashboard--contain {
    overflow: visible;
  }
  .home-main--dashboard .home-main-panel {
    overflow: visible;
  }
  .home-jobs-host {
    overflow: visible;
    flex: none;
  }
}
@media (max-width: 900px) {
  .home-main {
    max-width: 100vw;
  }
}
@media (max-width: 720px) {
  .home-main {
    padding: 0 10px 76px;
  }
}
</style>
