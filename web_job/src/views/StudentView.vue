<script setup>
/**
 * 登录后首页：侧栏 + 画像速览 + 智能匹配职位 + 热招职位（对齐设计稿）。
 * 「学生画像」tab 展示完整档案明细。
 */
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiPost } from "../api/client";
import FloatingFramePanel from "../components/FloatingFramePanel.vue";
import JobCompareBar from "../components/jobs/JobCompareBar.vue";
import JobCompareModal from "../components/jobs/JobCompareModal.vue";
import HomeMatchHistoryTimeline from "../components/home/HomeMatchHistoryTimeline.vue";
import HomeHotJobsSection from "../components/home/HomeHotJobsSection.vue";
import HomeMatchedJobsSection from "../components/home/HomeMatchedJobsSection.vue";
import HomeProfileOverview from "../components/home/HomeProfileOverview.vue";
import HomeTopBar from "../components/home/HomeTopBar.vue";
import StudentProfileDetailPanel from "../components/home/StudentProfileDetailPanel.vue";

const JobDetailView = defineAsyncComponent(() => import("../views/JobDetailView.vue"));
const CompanyDetailView = defineAsyncComponent(() => import("../views/CompanyDetailView.vue"));
import {
  SCORE_DIMENSION_DEFS,
  clampDimensionScore,
  cloneDefaultScoreDimensions,
  sumScoreDimensions
} from "../constants/jobScoreRubric";
import { MATCH_PRESETS } from "../config/matchPresets";
import {
  formatJobMatchElapsed,
  useJobMatchWaitTimer
} from "../composables/useJobMatchWaitTimer";
import { useJobCompare } from "../composables/useJobCompare";
import { useJobMatchHistory } from "../composables/useJobMatchHistory";

const route = useRoute();
const router = useRouter();
const studentPortrait = ref(null);
const summary = ref(null);
const favorites = ref({ jobs: [] });
const hotJobs = ref([]);
const hotJobsLoading = ref(false);

const { compareList, compareCount, isSelected, toggleCompare, clearCompare, maxCompare } = useJobCompare();
const {
  historyItems,
  activeHistoryId,
  historyLoading,
  loadHistory,
  saveHistory,
  selectHistory,
  applySettingsToForm,
  applyRecordToView,
  buildSettingsPayload
} = useJobMatchHistory();
const compareOpen = ref(false);
const compareJobs = ref([]);

function openCompare() {
  const allJobs = [...jobs.value, ...hotJobs.value];
  const idSet = new Set(compareList.value);
  compareJobs.value = allJobs.filter((j) => idSet.has(j.job_id || j.id));
  compareOpen.value = true;
}
const regionFilter = ref("");
const salaryFilter = ref("");
const sortFilter = ref("score");
const error = ref("");
const query = ref("");
const jobs = ref([]);
const companies = ref([]);
const loading = ref(false);
/** 岗位推荐等待计时（网格区展示已等待时长与阶段） */
const matchWait = useJobMatchWaitTimer();
const { elapsedMs: matchElapsedMs, start: startMatchWait, stop: stopMatchWait } = matchWait;
/** 最近一次「开始匹配」请求耗时（毫秒），用于展示匹配时长 */
const lastMatchDurationMs = ref(null);
/** 是否已从服务端加载过匹配历史 */
const historyBootstrapped = ref(false);
const copyBtnText = ref("复制 JSON");
/** 是否已执行过至少一次「开始匹配」或已加载历史（用于区分初始态与「暂无数据」） */
const recommendSearched = ref(false);
/** LightRAG 检索摘要（与岗位同步知识库） */
const ragInfo = ref(null);
/** 与 `/api/skills/job-info-query` 返回的 `recommendation` 对齐：无匹配原因等（列表仍用 `jobs`） */
const recommendation = ref(null);

/** 是否使用语义相似缓存（需服务端 JOB_INFO_SEM_CACHE_ENABLED=1） */
const useSemanticCache = ref(true);
/** 岗位推荐配置（默认折叠隐藏） */
const useStudentProfile = ref(true);
const scoreBaseline = ref(85);
const minRecommendScore = ref(85);
const topNJobs = ref(9);
const scoreDimensions = ref(cloneDefaultScoreDimensions());
const scoreDimensionDefs = SCORE_DIMENSION_DEFS;
const scoreDimensionsTotal = computed(() => sumScoreDimensions(scoreDimensions.value));
const scoreDimensionsValid = computed(() => scoreDimensionsTotal.value === 100);
/** 最近一次匹配返回的 cache 元信息（命中时 API 顶层 cache.hit=true） */
const matchCacheMeta = ref(null);
const cacheBannerDismissed = ref(false);

const activePreset = ref(null);

function applyPreset(preset) {
  activePreset.value = preset.key;
  scoreDimensions.value = { ...preset.weights };
}

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

function onScoreDimensionChange(key) {
  const dim = scoreDimensionDefs.find((d) => d.key === key);
  const fallback = dim ? cloneDefaultScoreDimensions()[key] : 0;
  scoreDimensions.value = {
    ...scoreDimensions.value,
    [key]: clampDimensionScore(scoreDimensions.value[key], fallback)
  };
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

/** 岗位详情弹层（组件渲染替代 iframe） */
const jobDetailFrameOpen = ref(false);
const jobDetailFrameFullscreen = ref(false);
const jobDetailFrameTitle = ref("");
const selectedJobId = ref("");
const selectedCreditCode = ref("");
const detailMode = ref("job"); // "job" | "company"

function closeJobDetailFrame() {
  jobDetailFrameOpen.value = false;
  jobDetailFrameFullscreen.value = false;
  jobDetailFrameTitle.value = "";
  selectedJobId.value = "";
  selectedCreditCode.value = "";
}

function openJobDetailFrame(job) {
  if (!job?.job_id) return;
  const id = String(job.job_id).trim();
  selectedJobId.value = id;
  selectedCreditCode.value = "";
  detailMode.value = "job";
  jobDetailFrameTitle.value = job.job_title || job.job_name || job.job_id || "岗位详情";
  jobDetailFrameOpen.value = true;
  jobDetailFrameFullscreen.value = false;
}

function toggleJobDetailFullscreen() {
  jobDetailFrameFullscreen.value = !jobDetailFrameFullscreen.value;
}

function openJobDetailFullWindow() {
  if (detailMode.value === "job" && selectedJobId.value) {
    window.open(`/jobs/${encodeURIComponent(selectedJobId.value)}`, "_blank", "noopener,noreferrer");
  } else if (detailMode.value === "company" && selectedCreditCode.value) {
    window.open(`/companies/${encodeURIComponent(selectedCreditCode.value)}`, "_blank", "noopener,noreferrer");
  }
}

function onJobDetailDocKey(ev) {
  if (ev.key === "Escape" && jobDetailFrameOpen.value) {
    closeJobDetailFrame();
  }
}

/** 与后端 StudentPortraitChineseJsonTranslator 顶层段落 key 一致（Redis / GET /api/students 相同） */
const SEC = Object.freeze({
  student: "学生基本信息",
  family: "家庭信息",
  award: "奖励信息",
  counseling: "心理咨询申请",
  counselor: "心理咨询概要",
  tracking: "心理咨询归档"
});

const studentInfo = computed(() => studentPortrait.value?.[SEC.student] || {});
const familyInfoList = computed(() => studentPortrait.value?.[SEC.family] || []);
const awardInfoList = computed(() => studentPortrait.value?.[SEC.award] || []);
const counselingRecordList = computed(() => studentPortrait.value?.[SEC.counseling] || []);
const counselorRecordList = computed(() => studentPortrait.value?.[SEC.counselor] || []);
const trackingRecordList = computed(() => studentPortrait.value?.[SEC.tracking] || []);

const majorText = computed(() => studentInfo.value["专业名称"] || "-");

const isProfileTab = computed(() => route.query.tab === "profile");

const pageTitle = computed(() => (isProfileTab.value ? "学生画像" : "首页"));

const pageSubtitle = computed(() => {
  if (isProfileTab.value) {
    return studentInfo.value["专业名称"]
      ? `查看与维护 ${studentInfo.value["专业名称"]} 方向的完整档案`
      : "查看与维护你的完整学生档案";
  }
  return intentText.value ? `当前意向：${intentText.value}` : "";
});

const studentDisplayName = computed(() => studentInfo.value["姓名"] || "");

const intentText = computed(() => {
  const major = studentInfo.value["专业名称"] || "";
  const edu = studentInfo.value["学历"] || "";
  const parts = [];
  if (major) parts.push(major);
  if (edu) parts.push(`${edu}岗位`);
  return parts.join(" · ") || query.value.trim() || "待设置求职意向";
});

const applicationCount = computed(() => {
  const n = summary.value?.favorite_job_count;
  return Number.isFinite(Number(n)) ? Number(n) : 0;
});

function buildDefaultQuery() {
  const s = studentInfo.value || {};
  const major = s["专业名称"] || "对口";
  const city = s["学校名称"] ? "" : "";
  const edu = s["学历"] || "";
  return `想找${city}${major}${edu ? `（${edu}）` : ""}相关岗位，薪资合理、发展稳定`;
}

/** 后端已输出完整中文 key + null 占位，与写入 Redis 的结构一致 */
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
    { label: "体测成绩", value: s["体测成绩"] }
  ];
});

function getStudentIdFromRoute() {
  return route.query.student_id || localStorage.getItem("student_id") || "";
}

async function loadStudent() {
  const sid = getStudentIdFromRoute();
  if (!sid) return;
  try {
    studentPortrait.value = await apiGet(`/api/students/${encodeURIComponent(sid)}`);
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
  } catch {
    summary.value = null;
    favorites.value = { jobs: [] };
  }
}

async function loadHotJobs() {
  hotJobsLoading.value = true;
  try {
    const data = await apiGet("/api/jobs/paged?page=1&pageSize=8&syncedOnly=true");
    hotJobs.value = data?.items || [];
  } catch {
    hotJobs.value = [];
  } finally {
    hotJobsLoading.value = false;
  }
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
    const data = await apiPost("/api/skills/job-info-query", {
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
    });
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

/** 从服务端加载历史：默认展示最新一条，不调用匹配 API */
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
    copyBtnText.value = "已复制";
    setTimeout(() => {
      copyBtnText.value = "复制 JSON";
    }, 1200);
  } catch (_) {
    error.value = "复制失败，请手动复制";
  }
}

function handleJobViewDetail(job) {
  if (!job?.job_id) return;
  openJobDetailFrame(job);
}

function handleJobApply(job) {
  if (!job?.job_id) return;
  openJobDetailFrame(job);
}

function handleJobResume() {
  router.push("/resume/create");
}

function handleJobInterview() {
  router.push("/interview/industry");
}

function handleHotJobDetail(job) {
  if (!job?.job_id) return;
  openJobDetailFrame({
    job_id: job.job_id,
    job_title: job.job_title,
    job_name: job.job_title
  });
}

async function bootstrapHome() {
  const hotJobsLoaded = sessionStorage.getItem("home_hot_jobs_loaded");
  await Promise.all([loadStudent(), loadSummary()]);
  if (!hotJobsLoaded) {
    await loadHotJobs();
    sessionStorage.setItem("home_hot_jobs_loaded", "1");
  }
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
  <div class="home-main">
      <HomeTopBar
        :title="pageTitle"
        :subtitle="pageSubtitle"
        :student-name="studentDisplayName"
      />

      <StudentProfileDetailPanel
        v-if="isProfileTab"
        :student-info="studentInfo"
        :base-fields="baseFields"
        :award-info-list="awardInfoList"
        :summary="summary"
        :favorites="favorites.jobs || []"
        :recent-jobs="hotJobs"
        :intent-text="intentText"
        :error="error"
        @copy-json="copyJson"
        @view-job="handleHotJobDetail"
        @view-more="router.push('/jobs')"
      />

      <template v-else>
        <div class="home-dashboard">
          <aside class="home-left">
            <HomeProfileOverview
              :student-info="studentInfo"
              :award-list="awardInfoList"
              :application-count="applicationCount"
              :intent-text="intentText"
            />
            <HomeMatchHistoryTimeline
              v-if="!isProfileTab"
              :items="historyItems"
              :active-id="activeHistoryId"
              :loading="historyLoading"
              @select="handleHistorySelect"
            />
          </aside>

          <main class="home-right">
            <p v-if="error" class="home-error">{{ error }}</p>

            <div
              v-if="recommendSearched && cacheHitActive && !loading && !cacheBannerDismissed"
              class="cache-hit-banner"
              role="status"
            >
              <span class="cache-hit-badge">{{ cacheHitTitle }}</span>
              <span v-if="cacheHitDetail" class="cache-hit-detail">{{ cacheHitDetail }}</span>
              <button type="button" class="cache-hit-close" aria-label="关闭" @click="cacheBannerDismissed = true">✕</button>
            </div>

            <div class="sort-tabs">
              <span class="sort-tabs-label">排序：</span>
              <button :class="{ active: sortFilter === 'score' }" @click="sortFilter = 'score'">评分优先</button>
              <button :class="{ active: sortFilter === 'salary' }" @click="sortFilter = 'salary'">薪资优先</button>
              <button :class="{ active: sortFilter === 'date' }" @click="sortFilter = 'date'">最新发布</button>
            </div>

            <HomeMatchedJobsSection
              v-model:region-filter="regionFilter"
              v-model:salary-filter="salaryFilter"
              v-model:sort-filter="sortFilter"
              :jobs="jobs"
              :recommendation="recommendation"
              :loading="loading"
              :history-loading="historyLoading && !historyBootstrapped"
              :searched="recommendSearched"
              :has-history="historyItems.length > 0"
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

            <HomeHotJobsSection
              :jobs="hotJobs"
              :loading="hotJobsLoading"
              @view-detail="handleHotJobDetail"
              @view-more="router.push('/jobs')"
            />

            <div class="preset-bar">
              <button
                v-for="p in MATCH_PRESETS"
                :key="p.key"
                type="button"
                class="preset-chip"
                :class="{ active: activePreset === p.key }"
                :title="p.desc"
                @click="applyPreset(p)"
              >
                <span class="preset-chip-icon">{{ p.icon }}</span>
                <span class="preset-chip-label">{{ p.label }}</span>
              </button>
            </div>

            <details class="advanced-wrap">
              <summary>高级匹配设置</summary>
              <div class="advanced-body">
                <div class="line">
                  <input
                    v-model="query"
                    placeholder="例如：想找杭州前端、双休、成长空间好的岗位"
                    @keydown.enter.prevent="runRecommend()"
                  />
                  <button class="match-btn" :disabled="loading" @click="runRecommend()">
                    {{ loading ? "匹配中…" : "重新匹配" }}
                  </button>
                </div>
                <label class="switch-line">
                  <input v-model="useStudentProfile" type="checkbox" />
                  关联本人信息参与匹配
                </label>
                <label class="switch-line">
                  <input v-model="useSemanticCache" type="checkbox" />
                  使用语义缓存
                </label>

                <div class="recommend-config-grid">
                  <label class="field">
                    <span>评分基准（良好匹配参考线）</span>
                    <input
                      v-model.number="scoreBaseline"
                      type="number"
                      min="0"
                      max="100"
                      step="1"
                      @change="scoreBaseline = clampScore(scoreBaseline)"
                    />
                  </label>
                  <label class="field">
                    <span>最低推荐分数</span>
                    <input
                      v-model.number="minRecommendScore"
                      type="number"
                      min="0"
                      max="100"
                      step="1"
                      @change="minRecommendScore = clampScore(minRecommendScore)"
                    />
                  </label>
                  <label class="field">
                    <span>推荐岗位数量</span>
                    <input
                      v-model.number="topNJobs"
                      type="number"
                      min="1"
                      max="20"
                      step="1"
                      @change="topNJobs = clampTopN(topNJobs)"
                    />
                  </label>
                </div>

                <div class="score-dimensions-section">
                  <p class="score-dimensions-title">五维评分权重（各项为得分上限，合计应为 100 分）</p>
                  <div class="score-dimensions-grid">
                    <label v-for="dim in scoreDimensionDefs" :key="dim.key" class="field score-dim-field">
                      <span>{{ dim.label }}（0–100）</span>
                      <input
                        v-model.number="scoreDimensions[dim.key]"
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        @change="onScoreDimensionChange(dim.key)"
                      />
                      <small class="field-hint">{{ dim.desc }}</small>
                    </label>
                  </div>
                  <p
                    class="score-dimensions-summary"
                    :class="{ 'score-dimensions-summary--warn': !scoreDimensionsValid }"
                  >
                    维度合计 <strong>{{ scoreDimensionsTotal }}</strong> / 100 分
                    <template v-if="!scoreDimensionsValid"> · 建议调整为合计 100 分，以便与模型评分体系一致</template>
                  </p>
                  <table class="score-rubric-table" aria-label="当前评分维度配置">
                    <thead>
                      <tr>
                        <th>维度</th>
                        <th>上限</th>
                        <th>说明</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="dim in scoreDimensionDefs" :key="'row-' + dim.key">
                        <td>{{ dim.label }}</td>
                        <td>{{ scoreDimensions[dim.key] ?? 0 }}</td>
                        <td>{{ dim.desc }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <p class="recommend-config-hint">
                  良好匹配基准 {{ scoreBaseline }} 分；仅返回 score ≥ {{ minRecommendScore }} 分的岗位，最多 {{ topNJobs }} 条。
                  模型将在【评分依据】中按上表五维逐条写出「维度名 X/Y 分 + 依据」。
                </p>

                <p v-if="loading" class="match-duration match-duration--live">
                  已匹配时长 {{ formatJobMatchElapsed(matchElapsedMs) }}
                </p>
                <p v-else-if="recommendSearched && lastMatchDurationMs != null" class="match-duration">
                  本次匹配用时 {{ formatJobMatchElapsed(lastMatchDurationMs) }}
                  <span v-if="cacheHitActive" class="match-duration-cache-tag">（缓存）</span>
                </p>
              </div>
            </details>
          </main>
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
        <JobDetailView v-if="detailMode === 'job' && selectedJobId" :key="selectedJobId" :embedded-job-id="selectedJobId" />
        <CompanyDetailView v-else-if="detailMode === 'company' && selectedCreditCode" :key="selectedCreditCode" :embedded-credit-code="selectedCreditCode" />
      </FloatingFramePanel>
    </Teleport>

    <JobCompareBar :count="compareCount" :max="maxCompare" @open="openCompare" @clear="clearCompare" />
    <JobCompareModal :open="compareOpen" :jobs="compareJobs" @close="compareOpen = false" />
</template>

<style scoped>
.home-dashboard {
  display: grid;
  grid-template-columns: minmax(272px, 300px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  width: 100%;
}
.home-right {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
}
.home-left {
  position: sticky;
  top: calc(var(--home-topbar-h, 56px) + 12px);
  overflow: visible;
  z-index: 2;
}
.home-error {
  margin: 0 0 12px;
  color: var(--danger);
  font-size: 0.88rem;
  font-weight: 600;
}
.sort-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
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
.advanced-wrap {
  margin-top: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  padding: 8px 12px;
}
.advanced-wrap > summary {
  cursor: pointer;
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 600;
}
.advanced-body {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.line {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}
.line input {
  border: 1px solid #dbe1ea;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.86rem;
}
.match-btn {
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  background: var(--primary-color);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}
.match-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.switch-line {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 0.86rem;
}
.recommend-config-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 4px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field span {
  font-size: 0.78rem;
  color: var(--text-muted);
}
.field input {
  width: 100%;
  border: 1px solid #dbe1ea;
  border-radius: 10px;
  padding: 9px 10px;
  background: #f8fafc;
  color: #111827;
  font-size: 0.86rem;
}
.score-dimensions-section {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px;
  background: #fcfcff;
}
.score-dimensions-title {
  margin: 0 0 8px;
  font-size: 0.84rem;
  font-weight: 700;
  color: #374151;
}
.score-dimensions-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.score-dim-field .field-hint {
  font-size: 0.74rem;
  color: #94a3b8;
  line-height: 1.4;
}
.score-dimensions-summary {
  margin: 10px 0 0;
  font-size: 0.82rem;
  color: #4338ca;
}
.score-dimensions-summary--warn {
  color: #b45309;
}
.score-rubric-table {
  width: 100%;
  margin-top: 10px;
  border-collapse: collapse;
  font-size: 0.78rem;
}
.score-rubric-table th,
.score-rubric-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}
.score-rubric-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}
.score-rubric-table td:nth-child(2) {
  width: 56px;
  text-align: center;
  font-weight: 700;
  color: #4338ca;
}
.recommend-config-hint {
  margin: 0;
  font-size: 0.82rem;
  color: var(--text-muted);
  line-height: 1.5;
}
.match-duration {
  margin: 0;
  font-size: 0.82rem;
  color: #4338ca;
  font-weight: 600;
}
.match-duration-cache-tag {
  margin-left: 6px;
  color: #059669;
  font-weight: 700;
}
.match-duration--live {
  animation: match-duration-pulse 1.5s ease-in-out infinite;
}
@keyframes match-duration-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.72; }
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
  .home-left {
    position: static;
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
  .recommend-config-grid,
  .score-dimensions-grid {
    grid-template-columns: 1fr;
  }
  .preset-bar { gap: 6px; }
  .preset-chip { font-size: 0.76rem; padding: 6px 10px; }
}
.preset-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.preset-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}
.preset-chip:hover {
  border-color: #c7d2fe;
  background: #f8faff;
}
.preset-chip.active {
  border-color: #6366f1;
  background: #eef2ff;
  color: #4338ca;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}
.preset-chip-icon { font-size: 1rem; }
.preset-chip-label { white-space: nowrap; }
</style>
