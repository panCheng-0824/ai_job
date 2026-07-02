<script setup>
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { apiGet, apiPost, apiPostSse, getStudentId } from "../api/client";
import FloatingFramePanel from "../components/FloatingFramePanel.vue";
import HomeTopBar from "../components/home/HomeTopBar.vue";
import JobsCenterCompanyGrid from "../components/jobs/JobsCenterCompanyGrid.vue";
import JobsCenterJobGrid from "../components/jobs/JobsCenterJobGrid.vue";
import JobsFilterPanel from "../components/jobs/JobsFilterPanel.vue";
import JobsMatchSettingsPanel from "../components/jobs/JobsMatchSettingsPanel.vue";
import JobCompareBar from "../components/jobs/JobCompareBar.vue";
import JobCompareModal from "../components/jobs/JobCompareModal.vue";
import RagSyncThreeMinuteProgress from "../components/rag/RagSyncThreeMinuteProgress.vue";
import {
  SCORE_DIMENSION_DEFS,
  clampDimensionScore,
  cloneDefaultScoreDimensions
} from "../constants/jobScoreRubric";
import { useJobMatchWaitTimer } from "../composables/useJobMatchWaitTimer";
import { useJobCompare } from "../composables/useJobCompare";
import { useRagSyncThreeMinuteProgress } from "../composables/useRagSyncThreeMinuteProgress";
import {
  RAG_SYNC_SECONDS_PER_JOB,
  formatRagSyncHms,
  useRagSyncEtaCountdown,
} from "../composables/useRagSyncEtaCountdown";

const AsyncJobDetail = defineAsyncComponent(() => import("../views/JobDetailView.vue"));
const AsyncCompanyDetail = defineAsyncComponent(() => import("../views/CompanyDetailView.vue"));

const router = useRouter();
const activeTab = ref("match");
const sortMode = ref("score");
const { compareList, compareCount, isSelected, toggleCompare, clearCompare, maxCompare } = useJobCompare();
const compareOpen = ref(false);
const compareJobs = ref([]);

function openCompare() {
  const allJobs = [...matchedJobs.value, ...jobs.value];
  const idSet = new Set(compareList.value);
  compareJobs.value = allJobs.filter((j) => idSet.has(j.job_id || j.id));
  compareOpen.value = true;
}
const matchedJobs = ref([]);
const recommendation = ref(null);
const matchLoading = ref(false);
const matchWait = useJobMatchWaitTimer();
const { elapsedMs: matchElapsedMs, start: startMatchWait, stop: stopMatchWait } = matchWait;
const lastMatchDurationMs = ref(null);
const matchQuery = ref("");
const useStudentProfile = ref(true);
const useSemanticCache = ref(true);
const scoreBaseline = ref(85);
const minRecommendScore = ref(85);
const topNJobs = ref(9);
const scoreDimensions = ref(cloneDefaultScoreDimensions());
const companiesLoading = ref(false);
const companySearchInput = ref("");
const companyRemoteKeyword = ref("");
const companiesList = ref([]);
const companyPage = ref(1);
const companyPageSize = 20;
const companyTotal = ref(0);
const companyHasMore = ref(false);
const companyLoadingMore = ref(false);
const studentPortrait = ref(null);
const filterProvince = ref("");
const filterCity = ref("");
const filterSalaryMin = ref("");
const filterSalaryMax = ref("");
const filterEducation = ref([]);
const filterCompanySize = ref([]);
const filterJobNature = ref([]);
const filterPublishTime = ref("");
const jobDetailFrameOpen = ref(false);
const jobDetailFrameFullscreen = ref(false);
const jobDetailFrameTitle = ref("");
const selectedJobId = ref("");
const selectedCreditCode = ref("");
const detailMode = ref("job");
const jobs = ref([]);
const page = ref(1);
const pageSize = 20;
const total = ref(0);
const hasMore = ref(false);
const loadingMore = ref(false);
/** 输入框内容：未按回车时仅参与本地过滤；按回车后写入 remoteKeyword 并走接口分页 */
const searchInput = ref("");
/** 最近一次「回车」提交给后端的检索词；空表示全量分页 */
const remoteKeyword = ref("");
/** 为 true 时仅查询已同步知识库（synRag=1）的岗位 */
const syncedOnly = ref(true);
/** 筛选：公司类型（单位性质 job_dwxz）与行业（job_hylb） */
const filterFacets = ref({ companyTypes: [], industries: [] });
const filterFacetsLoading = ref(false);
const filterPanelOpen = ref(true);
const filterRefreshing = ref(false);
const selectedCompanyType = ref("");
const selectedIndustry = ref("");
const error = ref("");
const favoriteJobIds = ref(new Set());
const sentinelRef = ref(null);
let observer;
const normalizedJobs = computed(() =>
  (jobs.value || []).map((item) => ({
    job_id: item.id,
    job_title: item.jobName,
    job_name: item.jobName,
    city: item.address,
    district: item.area,
    salary_range_month: item.salaryRange,
    salary_months: "-",
    xlyqText: item.xlyqText,
    createTime: item.createTime,
    create_time: item.createTime,
    company_name: item.companyName,
    company_relation: {
      company_name: item.companyName,
      credit_code: item.companyWid || item.companyId
    }
  }))
);

const studentInfo = computed(() => studentPortrait.value?.["学生基本信息"] || {});
const studentDisplayName = computed(() => studentInfo.value["姓名"] || "");

const cityOptions = computed(() => {
  const set = new Set();
  for (const j of jobs.value || []) {
    if (j.address) set.add(String(j.address));
    if (j.area) set.add(String(j.area));
  }
  for (const j of matchedJobs.value || []) {
    if (j.city) set.add(String(j.city));
  }
  return [...set].sort((a, b) => a.localeCompare(b, "zh-CN"));
});

function parseSalaryK(text) {
  const raw = String(text || "");
  const nums = raw.match(/\d+/g);
  if (!nums?.length) return null;
  return nums.map((n) => Number(n)).filter((n) => Number.isFinite(n));
}

function passesClientFilters(item) {
  if (filterCity.value && item.city !== filterCity.value && item.district !== filterCity.value) {
    return false;
  }
  if (filterSalaryMin.value || filterSalaryMax.value) {
    const nums = parseSalaryK(item.salary_range_month);
    if (!nums?.length) return false;
    const val = Math.max(...nums);
    const min = Number(filterSalaryMin.value);
    const max = Number(filterSalaryMax.value);
    if (Number.isFinite(min) && val < min) return false;
    if (Number.isFinite(max) && val > max) return false;
  }
  if (filterEducation.value.length && !filterEducation.value.includes("any")) {
    const edu = String(item.xlyqText || "").toLowerCase();
    const needBachelor = filterEducation.value.includes("bachelor");
    const needMaster = filterEducation.value.includes("master");
    const needDoctor = filterEducation.value.includes("doctor");
    if (needDoctor && !edu.includes("博")) return false;
    if (needMaster && !edu.includes("硕") && !edu.includes("研")) return false;
    if (needBachelor && !edu.includes("本") && !edu.includes("本科")) return false;
  }
  if (filterPublishTime.value) {
    const ts = Number(item.createTime || item.create_time || 0);
    if (!ts) return false;
    const days = { "3d": 3, "7d": 7, "30d": 30 }[filterPublishTime.value] || 0;
    if (days > 0 && Date.now() - ts > days * 86400000) return false;
  }
  return true;
}

const clientFilteredJobs = computed(() => normalizedJobs.value.filter(passesClientFilters));

const filtered = computed(() => {
  const q = searchInput.value.trim().toLowerCase();
  const base = clientFilteredJobs.value;
  if (!q) return base;
  return base.filter((item) => {
    const text = `${item.job_title || ""} ${item.city || ""} ${item.company_relation?.company_name || ""}`.toLowerCase();
    return text.includes(q);
  });
});

const gridJobs = computed(() => {
  if (activeTab.value === "match") return matchedJobs.value.filter(passesClientFilters);
  if (activeTab.value === "hot") return filtered.value;
  return [];
});

const gridLoading = computed(() => {
  if (activeTab.value === "match") return matchLoading.value;
  if (activeTab.value === "hot") return loadingMore.value && !jobs.value.length;
  return false;
});

const centerTabs = [
  { key: "match", label: "智能匹配职位" },
  { key: "hot", label: "热招职位" },
  { key: "companies", label: "热门企业" }
];

const gridEmptyText = computed(() => {
  if (activeTab.value === "match") return "暂无智能匹配岗位，请调整匹配设置或左侧筛选";
  if (activeTab.value === "hot") return "没有匹配的岗位，请调整搜索或筛选";
  return "暂无岗位";
});

const searchDisabled = computed(() => activeTab.value === "match");

const searchPlaceholder = computed(() => {
  if (activeTab.value === "match") return "智能匹配模式下请使用下方「匹配设置」调整诉求";
  if (activeTab.value === "companies") return "搜索企业名称 / 行业 / 地区，回车查库";
  return "搜索职位名 / 工作地点 / 用人单位，回车查库";
});

const toolbarSearchValue = computed({
  get() {
    return activeTab.value === "companies" ? companySearchInput.value : searchInput.value;
  },
  set(value) {
    if (activeTab.value === "companies") companySearchInput.value = value;
    else searchInput.value = value;
  }
});

const normalizedCompanies = computed(() =>
  (companiesList.value || []).map((item) => ({
    credit_code: item.id,
    company_name: item.companyName,
    industry: item.area,
    company_size: item.companySize,
    job_count: Number(item.jobCount ?? 0)
  }))
);

const filteredCompanies = computed(() => {
  const q = companySearchInput.value.trim().toLowerCase();
  if (!q) return normalizedCompanies.value;
  return normalizedCompanies.value.filter((item) => {
    const text = `${item.company_name || ""} ${item.credit_code || ""} ${item.industry || ""} ${item.company_size || ""}`.toLowerCase();
    return text.includes(q);
  });
});

const companyTotalText = computed(() => {
  const draft = companySearchInput.value.trim();
  const remote = companyRemoteKeyword.value.trim();
  if (remote) {
    return `检索「${remote}」：库内共 ${companyTotal.value} 家（已加载 ${filteredCompanies.value.length} 家）`;
  }
  if (draft) {
    return `本地筛选 ${filteredCompanies.value.length} 家（回车可向库内检索）`;
  }
  return `共 ${companyTotal.value} 家企业`;
});

const totalText = computed(() => {
  const draft = searchInput.value.trim();
  const remote = remoteKeyword.value.trim();
  if (remote) {
    return `检索「${remote}」：库内共 ${total.value} 条（当前已加载 ${filtered.value.length} 条）`;
  }
  if (draft) {
    return `本地筛选 ${filtered.value.length} 条（回车可向库内检索）`;
  }
  return `共 ${total.value} 个岗位`;
});

const pageSubtitle = computed(() => {
  if (activeTab.value === "match") return "基于画像与诉求的智能匹配结果 · 使用下方匹配设置调整";
  if (activeTab.value === "hot") return totalText.value;
  return companyTotalText.value;
});
/** 仅输入未回车：本地过滤已加载列表，不展示服务端分页文案 */
const isLocalFilterOnly = computed(() => {
  const draft = searchInput.value.trim();
  const remote = remoteKeyword.value.trim();
  return Boolean(draft) && !remote;
});
const loadedPage = computed(() => Math.max(0, page.value - 1));
const totalPages = computed(() => (total.value > 0 ? Math.ceil(total.value / pageSize) : 0));
const showPageText = computed(() => !isLocalFilterOnly.value && total.value > 0 && totalPages.value > 0);
const pageText = computed(() => {
  const loaded = Math.min(loadedPage.value, totalPages.value);
  return `已加载 ${loaded} / 共 ${totalPages.value} 页`;
});

async function loadFavorites() {
  const sid = getStudentId();
  if (!sid) {
    favoriteJobIds.value = new Set();
    return;
  }
  try {
    const f = await apiGet(`/api/me/favorites?student_id=${encodeURIComponent(sid)}`);
    favoriteJobIds.value = new Set(f.job_ids || []);
  } catch {
    favoriteJobIds.value = new Set();
  }
}

async function toggleFavorite(jobId, ev) {
  ev?.preventDefault();
  ev?.stopPropagation();
  const sid = getStudentId();
  if (!sid) {
    window.alert("请先登录");
    return;
  }
  try {
    const resp = await apiPost("/api/me/favorites/toggle", { student_id: sid, job_id: jobId });
    favoriteJobIds.value = new Set(resp.favorite_jobs || []);
  } catch (err) {
    window.alert(err.message || "操作失败");
  }
}

function isFavorite(jobId) {
  return favoriteJobIds.value.has(jobId);
}

async function loadNextPage() {
  if (loadingMore.value || !hasMore.value) return;
  loadingMore.value = true;
  try {
    const rk = remoteKeyword.value.trim();
    const kw = rk ? `&keyword=${encodeURIComponent(rk)}` : "";
    const sync = `&syncedOnly=${syncedOnly.value}`;
    const ct = selectedCompanyType.value
      ? `&companyType=${encodeURIComponent(selectedCompanyType.value)}`
      : "";
    const ind = selectedIndustry.value ? `&industry=${encodeURIComponent(selectedIndustry.value)}` : "";
    const data = await apiGet(
      `/api/jobs/paged?page=${page.value}&pageSize=${pageSize}${kw}${sync}${ct}${ind}`
    );
    const items = data?.items || [];
    jobs.value.push(...items);
    total.value = Number(data?.total || 0);
    hasMore.value = Boolean(data?.hasMore);
    page.value += 1;
  } catch (err) {
    error.value = err.message;
  } finally {
    loadingMore.value = false;
  }
}

async function loadFilterFacets() {
  filterFacetsLoading.value = true;
  try {
    const data = await apiGet(`/api/jobs/filter-facets${buildJobScopeQueryParams()}`);
    filterFacets.value = {
      companyTypes: data?.companyTypes || [],
      industries: data?.industries || []
    };
  } catch {
    filterFacets.value = { companyTypes: [], industries: [] };
  } finally {
    filterFacetsLoading.value = false;
  }
}

/** 与岗位列表、RAG 同步统计共用的查询范围参数 */
function buildJobScopeQueryParams() {
  const params = new URLSearchParams();
  const rk = remoteKeyword.value.trim();
  if (rk) params.set("keyword", rk);
  if (selectedCompanyType.value) params.set("companyType", selectedCompanyType.value);
  if (selectedIndustry.value) params.set("industry", selectedIndustry.value);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

async function applyFilterScope() {
  resetPagedList();
  await Promise.all([loadFilterFacets(), loadRagStats()]);
  await loadNextPage();
}

async function refreshFilterData() {
  if (filterRefreshing.value) return;
  filterRefreshing.value = true;
  try {
    await Promise.all([loadFilterFacets(), loadRagStats()]);
  } finally {
    filterRefreshing.value = false;
  }
}

function toggleFilterPanel() {
  filterPanelOpen.value = !filterPanelOpen.value;
}

function toggleCompanyType(code) {
  selectedCompanyType.value = selectedCompanyType.value === code ? "" : code;
}

function toggleIndustry(code) {
  selectedIndustry.value = selectedIndustry.value === code ? "" : code;
}

function clearCompanyTypeFilter() {
  if (!selectedCompanyType.value) return;
  selectedCompanyType.value = "";
  void applyFilterScope();
}

function clearIndustryFilter() {
  if (!selectedIndustry.value) return;
  selectedIndustry.value = "";
  void applyFilterScope();
}

function clearFacetFilters() {
  if (!selectedCompanyType.value && !selectedIndustry.value) return;
  selectedCompanyType.value = "";
  selectedIndustry.value = "";
  void applyFilterScope();
}

function onSearchEnter() {
  if (activeTab.value === "match") return;
  if (activeTab.value === "companies") {
    companyRemoteKeyword.value = companySearchInput.value.trim();
    resetCompanyPagedList();
    void loadNextCompanyPage();
    return;
  }
  remoteKeyword.value = searchInput.value.trim();
  resetPagedList();
  void Promise.all([loadFilterFacets(), loadRagStats()]).then(() => loadNextPage());
}

function resetCompanyPagedList() {
  companiesList.value = [];
  companyPage.value = 1;
  companyHasMore.value = true;
  companyTotal.value = 0;
}

async function loadNextCompanyPage() {
  if (companyLoadingMore.value || !companyHasMore.value) return;
  companyLoadingMore.value = true;
  companiesLoading.value = companyPage.value === 1;
  try {
    const rk = companyRemoteKeyword.value.trim();
    const kw = rk ? `&keyword=${encodeURIComponent(rk)}` : "";
    const data = await apiGet(
      `/api/companies/paged?page=${companyPage.value}&pageSize=${companyPageSize}${kw}`
    );
    const items = data?.items || [];
    companiesList.value.push(...items);
    companyTotal.value = Number(data?.total || 0);
    companyHasMore.value = Boolean(data?.hasMore);
    companyPage.value += 1;
  } catch (err) {
    error.value = err.message;
  } finally {
    companyLoadingMore.value = false;
    companiesLoading.value = false;
  }
}

function buildScoreDimensionsPayload() {
  const out = {};
  for (const dim of SCORE_DIMENSION_DEFS) {
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

function clampScore(value, fallback = 85) {
  const n = Number.parseInt(String(value), 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.min(100, n));
}

function clampTopN(value, fallback = 9) {
  const n = Number.parseInt(String(value), 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(1, Math.min(20, n));
}

/** 回车：用当前输入向服务端检索并重置无限滚动 */
function resetPagedList() {
  jobs.value = [];
  page.value = 1;
  hasMore.value = true;
  total.value = 0;
  error.value = "";
}

const hasFacetFilter = computed(
  () => Boolean(selectedCompanyType.value || selectedIndustry.value)
);

const selectedFilterSummary = computed(() => {
  const parts = [];
  if (selectedCompanyType.value) {
    const item = (filterFacets.value.companyTypes || []).find((i) => i.code === selectedCompanyType.value);
    parts.push(`公司类型：${item?.label || selectedCompanyType.value}`);
  }
  if (selectedIndustry.value) {
    const item = (filterFacets.value.industries || []).find((i) => i.code === selectedIndustry.value);
    parts.push(`行业：${item?.label || selectedIndustry.value}`);
  }
  return parts.join(" · ");
});

watch(syncedOnly, () => {
  resetPagedList();
  void loadNextPage();
});

async function applyJobsFilters() {
  if (activeTab.value === "companies") return;
  await applyFilterScope();
  if (activeTab.value === "match") await loadMatchedJobs();
}

function resetJobsFilters() {
  filterProvince.value = "";
  filterCity.value = "";
  filterSalaryMin.value = "";
  filterSalaryMax.value = "";
  filterEducation.value = [];
  filterCompanySize.value = [];
  filterJobNature.value = [];
  filterPublishTime.value = "";
  selectedCompanyType.value = "";
  selectedIndustry.value = "";
  searchInput.value = "";
  remoteKeyword.value = "";
  companySearchInput.value = "";
  companyRemoteKeyword.value = "";
  void applyJobsFilters();
}

async function loadStudentPortrait() {
  const sid = getStudentId();
  if (!sid) return;
  try {
    studentPortrait.value = await apiGet(`/api/students/${encodeURIComponent(sid)}`);
  } catch {
    studentPortrait.value = null;
  }
}

function buildDefaultMatchQuery() {
  const s = studentInfo.value || {};
  const major = s["专业名称"] || "对口";
  const edu = s["学历"] || "";
  return `想找${major}${edu ? `（${edu}）` : ""}相关岗位，薪资合理、发展稳定`;
}

async function loadMatchedJobs() {
  const qText = String(matchQuery.value || buildDefaultMatchQuery()).trim();
  if (!qText) {
    error.value = "请在匹配设置中输入岗位诉求";
    return;
  }
  matchQuery.value = qText;
  matchLoading.value = true;
  lastMatchDurationMs.value = null;
  error.value = "";
  startMatchWait();
  try {
    const studentContext = useStudentProfile.value ? buildStudentContextFromPortrait() : "";
    const data = await apiPost("/api/skills/job-info-query", {
      query: qText,
      top_n_jobs: clampTopN(topNJobs.value),
      top_n_companies: 9,
      use_rag: true,
      use_semantic_cache: useSemanticCache.value,
      use_student_profile: useStudentProfile.value,
      student_context: studentContext,
      score_baseline: clampScore(scoreBaseline.value),
      min_recommend_score: clampScore(minRecommendScore.value),
      score_dimensions: buildScoreDimensionsPayload()
    });
    matchedJobs.value = data.jobs || [];
    recommendation.value = data.recommendation || null;
  } catch (err) {
    error.value = err.message;
    matchedJobs.value = [];
    recommendation.value = null;
  } finally {
    stopMatchWait();
    lastMatchDurationMs.value = matchElapsedMs.value;
    matchLoading.value = false;
  }
}

function openJobDetailFrame(job) {
  if (!job?.job_id) return;
  selectedJobId.value = String(job.job_id).trim();
  selectedCreditCode.value = "";
  detailMode.value = "job";
  jobDetailFrameTitle.value = job.job_title || job.job_name || job.job_id || "岗位详情";
  jobDetailFrameOpen.value = true;
  jobDetailFrameFullscreen.value = false;
}

function openCompanyDetailFrame(company) {
  const code = String(
    company?.credit_code || company?.id || company?.company_id || company?.companyId || ""
  ).trim();
  if (!code) return;
  selectedCreditCode.value = code;
  selectedJobId.value = "";
  detailMode.value = "company";
  jobDetailFrameTitle.value = company?.company_name || company?.companyName || code || "企业详情";
  jobDetailFrameOpen.value = true;
  jobDetailFrameFullscreen.value = false;
}

function closeDetailFrame() {
  jobDetailFrameOpen.value = false;
  jobDetailFrameFullscreen.value = false;
  jobDetailFrameTitle.value = "";
  selectedJobId.value = "";
  selectedCreditCode.value = "";
}

function toggleDetailFrameFullscreen() {
  jobDetailFrameFullscreen.value = !jobDetailFrameFullscreen.value;
}

function openDetailFullWindow() {
  if (detailMode.value === "job" && selectedJobId.value) {
    window.open(`/jobs/${encodeURIComponent(selectedJobId.value)}`, "_blank", "noopener,noreferrer");
  } else if (detailMode.value === "company" && selectedCreditCode.value) {
    window.open(`/companies/${encodeURIComponent(selectedCreditCode.value)}`, "_blank", "noopener,noreferrer");
  }
}

function onJobDetailDocKey(ev) {
  if (ev.key === "Escape" && jobDetailFrameOpen.value) closeDetailFrame();
}

function handleJobViewDetail(job) {
  openJobDetailFrame(job);
}

function handleCompanyViewDetail(company) {
  openCompanyDetailFrame(company);
}

function handleJobApply(job) {
  openJobDetailFrame(job);
}

function handleJobResume() {
  router.push("/resume/create");
}

function handleJobInterview() {
  router.push("/interview/industry");
}

watch(activeTab, async (tab) => {
  if (tab === "companies" && !companiesList.value.length) {
    resetCompanyPagedList();
    await loadNextCompanyPage();
  }
  await nextTick();
  setupInfiniteScrollObserver();
  maybeLoadMoreForActiveTab();
});

function maybeLoadMoreForActiveTab() {
  if (activeTab.value === "hot") {
    if (hasMore.value && !loadingMore.value) void loadNextPage();
    return;
  }
  if (activeTab.value === "companies") {
    if (companyHasMore.value && !companyLoadingMore.value) void loadNextCompanyPage();
  }
}

function setupInfiniteScrollObserver() {
  if (observer) observer.disconnect();
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) maybeLoadMoreForActiveTab();
    },
    { root: null, rootMargin: "320px 0px", threshold: 0.01 }
  );
  if (sentinelRef.value) observer.observe(sentinelRef.value);
}

function onHotConfigToggle(event) {
  if (event.target?.open && activeTab.value === "hot") {
    void refreshRagPanelStats();
  }
}

watch(remoteKeyword, () => {
  void loadFilterFacets();
  if (activeTab.value === "hot") void loadRagStats();
});

onMounted(async () => {
  document.addEventListener("keydown", onJobDetailDocKey);
  await loadFavorites();
  await loadStudentPortrait();
  matchQuery.value = buildDefaultMatchQuery();
  await loadFilterFacets();

  const alreadyLoaded = sessionStorage.getItem("jobs_data_loaded");
  if (!alreadyLoaded) {
    await Promise.all([loadNextPage(), loadMatchedJobs()]);
    sessionStorage.setItem("jobs_data_loaded", "1");
  }

  await nextTick();
  setupInfiniteScrollObserver();
});

onBeforeUnmount(() => {
  matchWait.reset();
  document.removeEventListener("keydown", onJobDetailDocKey);
  window.clearTimeout(ragStatsDebounceTimer);
  if (observer) observer.disconnect();
  if (syncRunning.value) {
    void ragFireCancel();
    ragAbort.value?.abort();
  }
});

/** ---------- 知识库 RAG 批量同步 ---------- */
const ragPanelTab = ref("sync");
const ragStats = ref({ total: 0, synced: 0, unsynced: 0, keyword: "" });
const ragBacklog = ref({
  pending: 0,
  processing: 0,
  failed: 0,
  backlogTotal: 0,
  processed: 0,
  loaded: false,
  error: ""
});
const backlogLoading = ref(false);
const ragLive = ref({ total: 0, synced: 0, unsynced: 0, batchIndex: 0, batchTotal: 0 });
const syncRunning = ref(false);
const syncLog = ref([]);
const ragAbort = ref(null);
const syncDoneSummary = ref(null);
const ragPaused = ref(false);
/** 加速同步：默认关闭（串行）；开启后按服务端配置并行处理多条岗位 */
const ragAccelerate = ref(false);
/** 同步开始前清理 LightRAG 积压（pending/processing/failed），默认开启 */
const ragPurgeBeforeSync = ref(true);
/** 单独清理积压（不触发同步） */
const purgeRunning = ref(false);
const purgeLog = ref([]);
const purgeDoneSummary = ref(null);

/** ---------- 串行同步：3 分钟刻度进度条 + 当前岗位名 ---------- */
const currentSyncJobName = ref("");
/** 加速模式下并行同步中的岗位 id -> 名称 */
const activeSyncJobs = ref(new Map());

/** 加速模式下服务端并行度（来自 SSE stats） */
const ragMaxParallel = ref(1);

const ragEta = useRagSyncEtaCountdown();
const {
  displayHms: ragEtaDisplayHms,
  syncAnchor: syncRagEtaAnchor,
  startTicker: startRagEtaTicker,
  pause: pauseRagEtaCountdown,
  resume: resumeRagEtaCountdown,
  stop: stopRagEtaCountdown,
  estimateSeconds: estimateRagSyncSeconds,
} = ragEta;

const ragIdleEtaHms = computed(() => {
  const jobs = Math.max(0, Number(ragStats.value.unsynced || 0));
  if (jobs <= 0) return "00:00:00";
  const sec = estimateRagSyncSeconds(jobs, ragAccelerate.value, ragMaxParallel.value);
  return formatRagSyncHms(sec);
});

function refreshRagEtaAnchor(syncRunningFlag = syncRunning.value) {
  syncRagEtaAnchor({
    ragLive: ragLive.value,
    syncRunning: syncRunningFlag,
    accelerate: ragAccelerate.value,
    maxParallel: ragMaxParallel.value,
  });
}

const ragSerialProgress = useRagSyncThreeMinuteProgress();
const {
  elapsedMs: ragSerialElapsedMs,
  fillPct: ragSerialFillPct,
  fillPctRounded: ragSerialFillPctRounded,
  fillColorClass: ragSerialFillColorClass,
  progressLabel: ragSerialProgressLabel,
  overScale: ragSerialOverScale,
  start: startRagSerialProgress,
  stop: stopRagSerialProgress,
  reset: resetRagSerialProgress,
} = ragSerialProgress;

function resolveJobName(data) {
  const name = String(data?.jobName || data?.job_name || "").trim();
  if (name) return name;
  const id = String(data?.jobId || data?.job_id || "").trim();
  return id || "未知岗位";
}

function onJobSyncing(data) {
  const id = String(data?.jobId || data?.job_id || "").trim();
  const name = resolveJobName(data);
  if (ragAccelerate.value) {
    if (!id) return;
    const next = new Map(activeSyncJobs.value);
    next.set(id, name);
    activeSyncJobs.value = next;
    return;
  }
  currentSyncJobName.value = name;
  startRagSerialProgress();
}

function onJobProgressDone(item) {
  const id = String(item?.jobId || item?.job_id || "").trim();
  if (ragAccelerate.value) {
    if (id && activeSyncJobs.value.has(id)) {
      const next = new Map(activeSyncJobs.value);
      next.delete(id);
      activeSyncJobs.value = next;
    }
    return;
  }
  stopRagSerialProgress();
  currentSyncJobName.value = "";
}

function resetSyncJobDisplay() {
  currentSyncJobName.value = "";
  activeSyncJobs.value = new Map();
  resetRagSerialProgress();
}

const showSerialTimeProgress = computed(() => syncRunning.value && !ragAccelerate.value);

const activeSyncJobLabel = computed(() => {
  if (!syncRunning.value) return "";
  if (ragAccelerate.value) {
    const names = [...activeSyncJobs.value.values()];
    if (!names.length) return "等待岗位开始同步…";
    if (names.length === 1) return `正在同步：${names[0]}`;
    return `正在同步 ${names.length} 条：${names.join("、")}`;
  }
  return currentSyncJobName.value ? `正在同步：${currentSyncJobName.value}` : "等待岗位开始同步…";
});

async function ragFireCancel() {
  try {
    await apiPost("/api/jobs/sync-rag/cancel", {});
  } catch {
    /* 忽略：连接可能已断开 */
  }
}

/** 同步进行中且拿到本批总数时，用「本批条数」驱动进度条，避免全库已同步 99% 时条几乎不动、像没进度 */
const progressPct = computed(() => {
  const bt = Number(ragLive.value.batchTotal || 0);
  const bi = Number(ragLive.value.batchIndex || 0);
  if (syncRunning.value && bt > 0) {
    return Math.min(100, Math.round((bi / bt) * 100));
  }
  const t = Number(ragLive.value.total || 0);
  if (t <= 0) return 0;
  const s = Number(ragLive.value.synced || 0);
  return Math.min(100, Math.round((s / t) * 100));
});

const progressIndeterminate = computed(() => {
  if (!syncRunning.value) return false;
  const bt = Number(ragLive.value.batchTotal || 0);
  const bi = Number(ragLive.value.batchIndex || 0);
  const t = Number(ragLive.value.total || 0);
  if (bt > 0 && bi === 0) return true;
  if (bt === 0 && t > 0) return true;
  return false;
});

const progressLabel = computed(() => {
  if (progressIndeterminate.value) {
    const bt = Number(ragLive.value.batchTotal || 0);
    if (bt > 0) return `本批 0 / ${bt}（首条完成后显示百分比）`;
    return "已连接，等待服务端推送统计…";
  }
  const bt = Number(ragLive.value.batchTotal || 0);
  const bi = Number(ragLive.value.batchIndex || 0);
  if (syncRunning.value && bt > 0) {
    return `${progressPct.value}%（本批 ${bi} / ${bt}）`;
  }
  return `${progressPct.value}%（当前范围内已同步 / 总岗位）`;
});

function applyStatsToLive(s) {
  ragLive.value = {
    total: Number(s?.total ?? 0),
    synced: Number(s?.synced ?? 0),
    unsynced: Number(s?.unsynced ?? 0),
    batchIndex: Number(s?.batchIndex ?? ragLive.value.batchIndex ?? 0),
    batchTotal: Number(s?.batchTotal ?? ragLive.value.batchTotal ?? 0)
  };
  if (s?.maxParallel != null) {
    ragMaxParallel.value = Math.max(1, Number(s.maxParallel) || 1);
  }
  refreshRagEtaAnchor();
}

async function loadRagStats() {
  try {
    const s = await apiGet(`/api/jobs/rag-sync/stats${buildJobScopeQueryParams()}`);
    ragStats.value = {
      total: Number(s?.total ?? 0),
      synced: Number(s?.synced ?? 0),
      unsynced: Number(s?.unsynced ?? 0),
      keyword: String(s?.keyword ?? remoteKeyword.value.trim() ?? "")
    };
    ragLive.value = {
      total: ragStats.value.total,
      synced: ragStats.value.synced,
      unsynced: ragStats.value.unsynced,
      batchIndex: 0,
      batchTotal: 0
    };
    refreshRagEtaAnchor(false);
  } catch {
    ragStats.value = { total: 0, synced: 0, unsynced: 0, keyword: "" };
    ragLive.value = { total: 0, synced: 0, unsynced: 0, batchIndex: 0, batchTotal: 0 };
  }
}

async function loadRagBacklogStats() {
  if (backlogLoading.value) return;
  backlogLoading.value = true;
  try {
    const b = await apiGet("/api/jobs/rag-sync/backlog-stats");
    if (b?.success === false) {
      ragBacklog.value = {
        pending: 0,
        processing: 0,
        failed: 0,
        backlogTotal: 0,
        processed: 0,
        loaded: false,
        error: String(b?.message || "无法读取 LightRAG 积压")
      };
      return;
    }
    ragBacklog.value = {
      pending: Number(b?.pending ?? 0),
      processing: Number(b?.processing ?? 0),
      failed: Number(b?.failed ?? 0),
      backlogTotal: Number(b?.backlog_total ?? 0),
      processed: Number(b?.processed ?? 0),
      loaded: true,
      error: ""
    };
  } catch (e) {
    ragBacklog.value = {
      pending: 0,
      processing: 0,
      failed: 0,
      backlogTotal: 0,
      processed: 0,
      loaded: false,
      error: e?.message || "无法连接 ai_job"
    };
  } finally {
    backlogLoading.value = false;
  }
}

async function refreshRagPanelStats() {
  await Promise.all([loadRagStats(), loadRagBacklogStats()]);
}

let ragStatsDebounceTimer;
watch(searchInput, () => {
  if (activeTab.value !== "hot") return;
  window.clearTimeout(ragStatsDebounceTimer);
  ragStatsDebounceTimer = window.setTimeout(() => {
    void refreshRagPanelStats();
  }, 400);
});

watch(ragAccelerate, () => {
  if (syncRunning.value) {
    refreshRagEtaAnchor(true);
  }
});

function switchRagPanelTab(tab) {
  if (tab !== "sync" && tab !== "purge") return;
  ragPanelTab.value = tab;
  if (tab === "purge" && !ragBacklog.value.loaded && !backlogLoading.value) {
    void loadRagBacklogStats();
  }
}

function pushLog(line) {
  const next = [...syncLog.value, line];
  if (next.length > 40) next.splice(0, next.length - 40);
  syncLog.value = next;
}

function pushPurgeLog(line) {
  const next = [...purgeLog.value, line];
  if (next.length > 60) next.splice(0, next.length - 60);
  purgeLog.value = next;
}

function appendPurgeDetailLines(data, pushFn) {
  if (!data || data.success !== true) {
    pushFn(`清理失败：${data?.message || data?.detail || "未知错误"}`);
    return;
  }
  const candidate = Number(data.candidate_count ?? 0);
  const successCnt = Number(data.success_count ?? 0);
  const notFound = Number(data.not_found_count ?? 0);
  const failure = Number(data.failure_count ?? 0);
  const exception = Number(data.exception_count ?? 0);
  pushFn(
    `统计：候选 ${candidate}，成功 ${successCnt}，未找到 ${notFound}，失败 ${failure}，异常 ${exception}。`
  );
  if (candidate === 0) {
    pushFn("结论：当前无 pending/processing/failed 积压。");
  } else if (data.fullyCleared === true || data.deepDeleteFullyCleared === true) {
    pushFn("结论：积压已全部清理（含 Neo4j/Milvus 深删）。");
  } else if (data.queueCleared === true || data.queue_cleared === true) {
    pushFn(
      "结论：任务队列已清空（doc_status 无积压）；部分 dup/failed 记录在 Neo4j 深删失败，一般不影响后续同步。"
    );
  } else {
    pushFn("结论：清理不完整；请重试或查看 ai_job 日志。");
  }
  const remaining = Number(data.remaining_non_processed_count ?? NaN);
  if (Number.isFinite(remaining)) {
    pushFn(`清理后 doc_status 剩余非 processed 条目：${remaining}。`);
  }
  const strip = data.disk_strip;
  if (strip && (strip.doc_status_entries_removed || strip.doc_status_files_rewritten)) {
    pushFn(
      `磁盘 doc_status 兜底：改写 ${strip.doc_status_files_rewritten ?? 0} 个文件，移除 ${strip.doc_status_entries_removed ?? 0} 条非 processed 记录。`
    );
  }
  const failures = Array.isArray(data.failures) ? data.failures : [];
  const errors = Array.isArray(data.errors) ? data.errors : [];
  const sample = [...failures.slice(0, 5), ...errors.slice(0, 3)];
  for (const item of sample) {
    const id = item.doc_id || "?";
    const msg = item.message || item.error || item.status || "未知原因";
    pushFn(`  · ${id}：${msg}`);
  }
  const hidden = failures.length + errors.length - sample.length;
  if (hidden > 0) {
    pushFn(`  … 另有 ${hidden} 条失败/异常未展示`);
  }
}

async function purgeLightRagBacklog() {
  if (purgeRunning.value || syncRunning.value) return;
  ragPanelTab.value = "purge";
  purgeLog.value = [];
  purgeDoneSummary.value = null;
  purgeRunning.value = true;
  pushPurgeLog("开始清理 LightRAG 积压（pending / processing / failed）…");
  pushPurgeLog("说明：仅清理 LightRAG 任务队列，不会修改岗位 synRag 状态。");
  try {
    const data = await apiPost("/api/jobs/rag-sync/purge-backlog", {});
    appendPurgeDetailLines(data, pushPurgeLog);
    purgeDoneSummary.value = {
      candidate: Number(data?.candidate_count ?? 0),
      success: Number(data?.success_count ?? 0),
      failure: Number(data?.failure_count ?? 0),
      fullyCleared: data?.fullyCleared === true,
      queueCleared: data?.queueCleared === true || data?.queue_cleared === true
    };
  } catch (e) {
    pushPurgeLog(`错误：${e?.message || e}`);
  } finally {
    purgeRunning.value = false;
    await loadRagBacklogStats();
  }
}

async function startRagSync() {
  if (syncRunning.value) return;
  ragPanelTab.value = "sync";
  syncDoneSummary.value = null;
  syncLog.value = [];
  ragPaused.value = false;
  await loadRagStats();
  await loadRagBacklogStats();
  if (Number(ragStats.value.unsynced || 0) <= 0) {
    const scopeHint = [
      remoteKeyword.value.trim() ? `关键词「${remoteKeyword.value.trim()}」` : "",
      selectedFilterSummary.value
    ]
      .filter(Boolean)
      .join(" · ");
    pushLog(
      scopeHint
        ? `当前范围内没有待同步岗位（${scopeHint} 下 synRag≠1 的条数为 0）。`
        : "当前没有待同步岗位（synRag≠1）。"
    );
    return;
  }
  syncRunning.value = true;
  resetSyncJobDisplay();
  startRagEtaTicker();
  refreshRagEtaAnchor(true);
  const ac = new AbortController();
  ragAbort.value = ac;
  const ragBody = {
    keyword: remoteKeyword.value.trim(),
    companyType: selectedCompanyType.value,
    industry: selectedIndustry.value,
    accelerate: ragAccelerate.value,
    purgeBeforeSync: ragPurgeBeforeSync.value
  };
  if (ragPurgeBeforeSync.value) {
    pushLog("已开启同步前清理：将删除 LightRAG 中 pending/processing/failed 积压。");
  }
  if (ragAccelerate.value) {
    pushLog("已开启加速：本批将并行同步（并行度由服务端配置）。");
  } else {
    pushLog("未开启加速：本批将串行同步（一次 1 条，更稳定）。");
  }
  try {
    await apiPostSse(
      "/api/jobs/sync-rag/pending",
      ragBody,
      {
        signal: ac.signal,
        onEvent: (name, data) => {
          if (name === "stats") {
            applyStatsToLive(data);
            pushLog(
              `统计：总数 ${data.total}，已同步 ${data.synced}，未同步 ${data.unsynced}，本批 ${data.batchTotal ?? 0} 条${
                data.keyword ? `（关键词「${data.keyword}」）` : "（全库）"
              }${data.accelerate ? ` · 加速并行×${data.maxParallel ?? "?"}` : " · 串行"}。`
            );
          } else if (name === "purge") {
            appendPurgeDetailLines(data, pushLog);
          } else if (name === "error") {
            pushLog(`无法开始：${data.detail || JSON.stringify(data)}`);
          } else if (name === "syncing") {
            onJobSyncing(data);
          } else if (name === "progress") {
            applyStatsToLive(data);
            const it = data.item || {};
            const ok = it.success === true;
            const skip = it.skipped === true;
            onJobProgressDone(it);
            pushLog(
              `[${data.batchIndex}/${data.batchTotal}] ${resolveJobName(it)} — ${
                skip ? "跳过" : ok ? "成功" : "失败"
              }${it.message ? `：${it.message}` : ""}`
            );
          } else if (name === "done") {
            syncDoneSummary.value = data;
            ragPaused.value = false;
            pushLog(
              `结束：成功 ${data.succeeded ?? 0}，失败 ${data.failed ?? 0}，跳过 ${data.skipped ?? 0}${
                data.cancelled ? "（已取消）" : ""
              }。`
            );
          }
        }
      }
    );
  } catch (e) {
    if (e?.name !== "AbortError") {
      pushLog(`错误：${e?.message || e}`);
    }
  } finally {
    syncRunning.value = false;
    ragPaused.value = false;
    ragAbort.value = null;
    resetSyncJobDisplay();
    stopRagEtaCountdown();
    await refreshRagPanelStats();
  }
}

async function pauseRagSync() {
  if (!syncRunning.value || ragPaused.value) return;
  try {
    await apiPost("/api/jobs/sync-rag/pause", {});
    ragPaused.value = true;
    pauseRagEtaCountdown();
    pushLog("已暂停：未开始的岗位会排队等待；进行中的会跑完。");
  } catch (e) {
    pushLog(`暂停失败：${e?.message || e}`);
  }
}

async function resumeRagSync() {
  if (!syncRunning.value || !ragPaused.value) return;
  try {
    await apiPost("/api/jobs/sync-rag/resume", {});
    ragPaused.value = false;
    resumeRagEtaCountdown();
    refreshRagEtaAnchor(true);
    pushLog("已继续同步。");
  } catch (e) {
    pushLog(`继续失败：${e?.message || e}`);
  }
}

async function cancelRagSync() {
  ragAbort.value?.abort();
  await ragFireCancel();
  ragPaused.value = false;
}
</script>

<template>
  <div class="home-main">
      <HomeTopBar
        title="岗位中心"
        :subtitle="pageSubtitle"
        :student-name="studentDisplayName"
      />

      <div class="jobs-center-layout">
        <JobsFilterPanel
          v-model:province="filterProvince"
          v-model:city="filterCity"
          v-model:salary-min="filterSalaryMin"
          v-model:salary-max="filterSalaryMax"
          v-model:education="filterEducation"
          v-model:company-size="filterCompanySize"
          v-model:job-nature="filterJobNature"
          v-model:publish-time="filterPublishTime"
          v-model:selected-company-type="selectedCompanyType"
          :cities="cityOptions"
          :provinces="[]"
          :company-types="filterFacets.companyTypes"
          :loading="filterFacetsLoading"
          :disabled="activeTab === 'companies'"
          @apply="applyJobsFilters"
          @reset="resetJobsFilters"
        />

        <div class="jobs-center-main">
          <div class="jobs-toolbar" :class="{ 'jobs-toolbar--match': searchDisabled }">
            <div class="jobs-search-wrap">
              <input
              v-model="toolbarSearchValue"
              class="jobs-search"
              :class="{ 'jobs-search--disabled': searchDisabled }"
              :disabled="searchDisabled"
              :placeholder="searchPlaceholder"
              :aria-label="searchPlaceholder"
              @keydown.enter.prevent="onSearchEnter"
            />
              <span v-if="searchDisabled" class="search-lock-hint">匹配模式下不可用</span>
            </div>
            <div v-if="activeTab === 'hot'" class="jobs-toolbar-meta">
              <span v-if="showPageText" class="count">{{ pageText }}</span>
              <span class="count">{{ totalText }}</span>
              <label class="switch-line jobs-sync-toggle">
                <input v-model="syncedOnly" type="checkbox" />
                仅已同步知识库
              </label>
            </div>
            <div v-else-if="activeTab === 'companies'" class="jobs-toolbar-meta">
              <span class="count">{{ companyTotalText }}</span>
            </div>
          </div>

          <header class="jobs-panel-tabs">
            <nav class="jobs-tabs" aria-label="岗位中心分类">
              <button
                v-for="tab in centerTabs"
                :key="tab.key"
                type="button"
                class="jobs-tab"
                :class="{ active: activeTab === tab.key }"
                @click="activeTab = tab.key"
              >
                {{ tab.label }}
              </button>
            </nav>
          </header>

          <div v-if="activeTab !== 'companies'" class="sort-tabs">
            <span class="sort-tabs-label">排序：</span>
            <button :class="{ active: sortMode === 'score' }" @click="sortMode = 'score'">评分优先</button>
            <button :class="{ active: sortMode === 'salary' }" @click="sortMode = 'salary'">薪资优先</button>
            <button :class="{ active: sortMode === 'date' }" @click="sortMode = 'date'">最新发布</button>
          </div>

          <JobsCenterJobGrid
            v-if="activeTab !== 'companies'"
            v-model:sort-mode="sortMode"
            :jobs="gridJobs"
            :recommendation="recommendation"
            :loading="gridLoading"
            :empty-text="gridEmptyText"
            :pad-placeholders="activeTab === 'match'"
            :expand-all="activeTab === 'hot'"
            :match-elapsed-ms="matchElapsedMs"
            :last-match-duration-ms="activeTab === 'match' ? lastMatchDurationMs : null"
            @view-detail="handleJobViewDetail"
            @apply="handleJobApply"
            @resume="handleJobResume"
            @interview="handleJobInterview"
          >
            <template v-if="activeTab === 'hot'" #after-grid>
              <div ref="sentinelRef" class="load-state">
                <span v-if="loadingMore">加载岗位中…</span>
                <span v-else-if="!hasMore && jobs.length">已加载全部岗位</span>
                <span v-else-if="hasMore">继续下滑加载更多岗位</span>
              </div>
            </template>
          </JobsCenterJobGrid>

          <JobsCenterCompanyGrid
            v-else
            :companies="filteredCompanies"
            :loading="companiesLoading && !companiesList.length"
            :loading-more="companyLoadingMore"
            @view-detail="handleCompanyViewDetail"
          >
            <template #after-grid>
              <div ref="sentinelRef" class="load-state">
                <span v-if="companyLoadingMore">加载企业中…</span>
                <span v-else-if="!companyHasMore && companiesList.length">已加载全部企业</span>
                <span v-else-if="companyHasMore">继续下滑加载更多企业</span>
              </div>
            </template>
          </JobsCenterCompanyGrid>

          <details v-if="activeTab === 'match'" class="jobs-tab-config" open>
            <summary>匹配设置</summary>
            <JobsMatchSettingsPanel
              v-model:query="matchQuery"
              v-model:use-student-profile="useStudentProfile"
              v-model:use-semantic-cache="useSemanticCache"
              v-model:score-baseline="scoreBaseline"
              v-model:min-recommend-score="minRecommendScore"
              v-model:top-n-jobs="topNJobs"
              v-model:score-dimensions="scoreDimensions"
              :loading="matchLoading"
              @run="loadMatchedJobs"
            />
          </details>

          <details v-else-if="activeTab === 'hot'" class="jobs-tab-config" @toggle="onHotConfigToggle">
            <summary>知识库同步与管理</summary>
            <div class="rag-config-body">
        <section class="rag-sync-panel" aria-label="知识库同步">
          <div class="rag-sync-head">
            <h2 class="rag-sync-title">知识库 RAG</h2>
            <nav class="rag-tab-bar" role="tablist" aria-label="RAG 操作">
              <button
                type="button"
                role="tab"
                class="rag-tab"
                :class="{ active: ragPanelTab === 'sync' }"
                :aria-selected="ragPanelTab === 'sync'"
                @click="switchRagPanelTab('sync')"
              >
                同步岗位
                <span v-if="syncRunning" class="rag-tab-badge rag-tab-badge--live">进行中</span>
              </button>
              <button
                type="button"
                role="tab"
                class="rag-tab"
                :class="{ active: ragPanelTab === 'purge' }"
                :aria-selected="ragPanelTab === 'purge'"
                @click="switchRagPanelTab('purge')"
              >
                清理积压
                <span v-if="ragBacklog.backlogTotal > 0" class="rag-tab-badge">{{ ragBacklog.backlogTotal }}</span>
              </button>
            </nav>
          </div>

          <!-- Tab：同步岗位 -->
          <div v-show="ragPanelTab === 'sync'" class="rag-tab-panel" role="tabpanel">
            <p class="rag-sync-desc muted">
              <template v-if="remoteKeyword.trim() || hasFacetFilter">
                统计与<strong>同步范围</strong>与上方筛选一致<template v-if="remoteKeyword.trim()">（关键词「<strong>{{ remoteKeyword.trim() }}</strong>」）</template><template v-if="selectedFilterSummary">（{{ selectedFilterSummary }}）</template>。仅处理该范围内尚未写入 RAG 的岗位。
              </template>
              <template v-else>
                统计与同步范围为<strong>全库</strong>未入库岗位；筛选或输入关键词后数字会更新，点「开始同步」仅同步当前范围内未写入 RAG 的条目。
              </template>
            </p>
            <div class="rag-stats-row">
              <div class="rag-stat"><span class="lbl">总岗位</span><strong>{{ ragLive.total }}</strong></div>
              <div class="rag-stat"><span class="lbl">已同步</span><strong class="ok">{{ ragLive.synced }}</strong></div>
              <div class="rag-stat"><span class="lbl">未同步</span><strong class="warn">{{ ragLive.unsynced }}</strong></div>
            </div>
            <div v-if="syncRunning || ragStats.unsynced > 0" class="rag-eta-block" aria-live="polite">
              <div class="rag-eta-main">
                <span class="lbl">{{ syncRunning ? "剩余时间" : "预计耗时" }}</span>
                <strong class="rag-eta-time">{{ syncRunning ? ragEtaDisplayHms : ragIdleEtaHms }}</strong>
              </div>
              <p class="rag-eta-hint muted">
                按每岗约 {{ RAG_SYNC_SECONDS_PER_JOB }} 秒估算
                <template v-if="syncRunning">
                  · 未同步 {{ ragLive.unsynced }} 条
                  <template v-if="ragLive.batchTotal > 0">（本批剩余 {{ Math.max(0, ragLive.batchTotal - ragLive.batchIndex) }} 条）</template>
                  <template v-if="ragPaused"> · 已暂停</template>
                </template>
                <template v-else-if="ragAccelerate"> · 加速模式已开启（按并行度折算）</template>
              </p>
            </div>
            <RagSyncThreeMinuteProgress
              v-if="showSerialTimeProgress"
              :running="true"
              :elapsed-ms="ragSerialElapsedMs"
              :fill-pct="ragSerialFillPct"
              :fill-pct-rounded="ragSerialFillPctRounded"
              :fill-color-class="ragSerialFillColorClass"
              :progress-label="ragSerialProgressLabel"
              :over-scale="ragSerialOverScale"
              :job-name="currentSyncJobName"
              title="单条同步耗时"
            />
            <div
              v-else-if="syncRunning && ragAccelerate"
              class="rag-progress-wrap"
              role="progressbar"
              :aria-valuenow="progressIndeterminate ? undefined : progressPct"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="progressLabel"
            >
              <p v-if="activeSyncJobLabel" class="rag-sync-job-name" :title="activeSyncJobLabel">
                {{ activeSyncJobLabel }}
              </p>
              <div class="rag-progress-track rag-progress-track--minute-zones" :class="{ 'rag-progress-track--busy': progressIndeterminate }">
                <div
                  class="rag-progress-fill rag-batch-fill"
                  :class="{ 'rag-progress-fill--pulse': progressIndeterminate }"
                  :style="progressIndeterminate ? {} : { width: progressPct + '%' }"
                />
              </div>
              <span class="rag-progress-label">{{ progressLabel }}</span>
            </div>
            <div
              v-else-if="syncRunning"
              class="rag-progress-wrap"
              role="progressbar"
              :aria-valuenow="progressIndeterminate ? undefined : progressPct"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="progressLabel"
            >
              <div class="rag-progress-track" :class="{ 'rag-progress-track--busy': progressIndeterminate }">
                <div
                  class="rag-progress-fill"
                  :class="{ 'rag-progress-fill--pulse': progressIndeterminate }"
                  :style="progressIndeterminate ? {} : { width: progressPct + '%' }"
                />
              </div>
              <span class="rag-progress-label">{{ progressLabel }}</span>
            </div>
            <div v-if="ragLive.batchTotal > 0 && syncRunning" class="rag-batch-hint muted">
              本批：{{ ragLive.batchIndex }} / {{ ragLive.batchTotal }}（与进度条一致）
              · {{ ragAccelerate ? "加速并行" : "串行" }}
            </div>
            <label class="switch-line rag-accelerate-line">
              <input v-model="ragPurgeBeforeSync" type="checkbox" :disabled="syncRunning" />
              同步前清理 LightRAG 积压（pending/processing/failed，默认开启）
            </label>
            <label class="switch-line rag-accelerate-line">
              <input v-model="ragAccelerate" type="checkbox" :disabled="syncRunning" />
              加速同步（并行处理多条，默认关闭；开启后更快但占用更多 ai_job 资源）
            </label>
            <div class="rag-actions">
              <button type="button" class="btn primary rag-sync-btn" :disabled="syncRunning || ragStats.unsynced <= 0" @click="startRagSync">
                {{ syncRunning ? "同步中…" : "开始同步未入库岗位" }}
              </button>
              <button
                v-if="syncRunning"
                type="button"
                class="btn secondary"
                :disabled="ragPaused"
                @click="pauseRagSync"
              >
                暂停
              </button>
              <button
                v-if="syncRunning && ragPaused"
                type="button"
                class="btn secondary"
                @click="resumeRagSync"
              >
                继续
              </button>
              <button v-if="syncRunning" type="button" class="btn secondary" @click="cancelRagSync">取消</button>
            </div>
            <p v-if="syncRunning && ragPaused" class="rag-paused-hint muted">当前为暂停状态，未开始的岗位不会继续执行，点「继续」恢复。</p>
            <p v-if="syncDoneSummary" class="rag-done muted">
              上次同步：成功 {{ syncDoneSummary.succeeded }}，失败 {{ syncDoneSummary.failed
              }}<template v-if="syncDoneSummary.skipped != null">，跳过 {{ syncDoneSummary.skipped }}</template
              ><template v-if="syncDoneSummary.cancelled">（已取消）</template>。
            </p>
            <div class="rag-log-wrap">
              <div class="rag-log-title">同步日志</div>
              <ul class="rag-log">
                <li v-for="(line, idx) in syncLog" :key="'s-' + idx" class="rag-log-line">{{ line }}</li>
                <li v-if="!syncLog.length" class="rag-log-line muted">点击「开始同步」后在此展示 SSE 推送内容。</li>
              </ul>
            </div>
          </div>

          <!-- Tab：清理积压 -->
          <div v-show="ragPanelTab === 'purge'" class="rag-tab-panel" role="tabpanel">
            <p class="rag-sync-desc muted">
              清理 ai_job LightRAG 中 pending / processing / failed 文档，释放任务队列与模型占用；<strong>不会</strong>修改岗位 synRag 状态。
            </p>
            <div class="rag-backlog-block rag-backlog-block--tab">
              <div class="rag-backlog-head">
                <h3 class="rag-backlog-title">当前积压</h3>
                <button
                  type="button"
                  class="btn-linkish"
                  :disabled="backlogLoading || purgeRunning"
                  @click="loadRagBacklogStats"
                >
                  {{ backlogLoading ? "刷新中…" : "刷新" }}
                </button>
              </div>
              <div v-if="ragBacklog.error" class="rag-backlog-error muted">{{ ragBacklog.error }}</div>
              <div v-else class="rag-stats-row rag-stats-row--backlog">
                <div class="rag-stat">
                  <span class="lbl">排队 pending</span>
                  <strong :class="{ warn: ragBacklog.pending > 0 }">{{ ragBacklog.pending }}</strong>
                </div>
                <div class="rag-stat">
                  <span class="lbl">处理中</span>
                  <strong :class="{ warn: ragBacklog.processing > 0 }">{{ ragBacklog.processing }}</strong>
                </div>
                <div class="rag-stat">
                  <span class="lbl">失败 failed</span>
                  <strong :class="{ danger: ragBacklog.failed > 0 }">{{ ragBacklog.failed }}</strong>
                </div>
                <div class="rag-stat rag-stat--total">
                  <span class="lbl">积压合计</span>
                  <strong :class="{ danger: ragBacklog.backlogTotal > 0 }">{{ ragBacklog.backlogTotal }}</strong>
                </div>
              </div>
              <p v-if="ragBacklog.loaded && !ragBacklog.error" class="rag-backlog-foot muted">
                LightRAG 已成功 processed：{{ ragBacklog.processed }} 条
              </p>
            </div>
            <div class="rag-actions">
              <button
                type="button"
                class="btn primary"
                :disabled="syncRunning || purgeRunning"
                @click="purgeLightRagBacklog"
              >
                {{ purgeRunning ? "清理中…" : "开始清理 LightRAG 积压" }}
              </button>
            </div>
            <p v-if="purgeDoneSummary" class="rag-done muted">
              上次清理：候选 {{ purgeDoneSummary.candidate }}，成功 {{ purgeDoneSummary.success }}，失败
              {{ purgeDoneSummary.failure
              }}<template v-if="purgeDoneSummary.fullyCleared">（已全部清理）</template
              ><template v-else-if="purgeDoneSummary.queueCleared">（队列已清空）</template
              ><template v-else-if="purgeDoneSummary.candidate > 0">（未完成）</template>。
            </p>
            <div class="rag-log-wrap">
              <div class="rag-log-title">清理日志</div>
              <ul class="rag-log">
                <li v-for="(line, idx) in purgeLog" :key="'p-' + idx" class="rag-log-line">{{ line }}</li>
                <li v-if="!purgeLog.length" class="rag-log-line muted">点击「开始清理 LightRAG 积压」后在此展示结果。</li>
              </ul>
            </div>
          </div>
        </section>
            </div>
          </details>

          <p v-if="error" class="error">{{ error }}</p>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <FloatingFramePanel
        :open="jobDetailFrameOpen"
        :fullscreen="jobDetailFrameFullscreen"
        :title="jobDetailFrameTitle"
        :z-index="13100"
        @backdrop-click="closeDetailFrame"
      >
        <template #actions>
          <button type="button" @click="toggleDetailFrameFullscreen">
            {{ jobDetailFrameFullscreen ? "缩小" : "放大" }}
          </button>
          <button type="button" @click="openDetailFullWindow">完整页面</button>
          <button type="button" class="danger" @click="closeDetailFrame">关闭</button>
        </template>
        <AsyncJobDetail v-if="detailMode === 'job' && selectedJobId" :key="selectedJobId" :embedded-job-id="selectedJobId" />
        <AsyncCompanyDetail v-else-if="detailMode === 'company' && selectedCreditCode" :key="selectedCreditCode" :embedded-credit-code="selectedCreditCode" />
      </FloatingFramePanel>
    </Teleport>

    <JobCompareBar :count="compareCount" :max="maxCompare" @open="openCompare" @clear="clearCompare" />
    <JobCompareModal :open="compareOpen" :jobs="compareJobs" @close="compareOpen = false" />
</template>

<style scoped>
.jobs-center-layout {
  display: grid;
  grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  width: 100%;
}
.jobs-center-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.jobs-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.9);
}
.jobs-toolbar--match {
  grid-template-columns: 1fr;
}
.jobs-search-wrap {
  position: relative;
  min-width: 0;
}
.jobs-search--disabled {
  background: #f1f5f9;
  color: #94a3b8;
  cursor: not-allowed;
  border-color: #e2e8f0;
}
.jobs-search--disabled::placeholder {
  color: #cbd5e1;
}
.search-lock-hint {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.68rem;
  color: #94a3b8;
  pointer-events: none;
}
.jobs-tab-config {
  margin-top: 4px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.82);
  padding: 8px 12px;
}
.jobs-tab-config > summary {
  cursor: pointer;
  color: #475569;
  font-size: 0.88rem;
  font-weight: 700;
}
.jobs-tab-config[open] > summary {
  margin-bottom: 12px;
  color: #4338ca;
}
.rag-config-body {
  padding-top: 4px;
}
.jobs-search {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #dbe1ea;
  font-size: 0.86rem;
}
.jobs-search:focus {
  outline: none;
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}
.jobs-toolbar-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.jobs-sync-toggle {
  margin: 0;
  font-size: 0.78rem;
}
.jobs-panel-tabs {
  padding: 0 4px;
}
.jobs-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}
.jobs-tab {
  border: none;
  background: transparent;
  padding: 8px 2px;
  font-size: 0.9rem;
  font-weight: 700;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}
.jobs-tab.active {
  color: #4338ca;
  border-bottom-color: #6366f1;
}
.job-detail-frame {
  width: 100%;
  height: min(72vh, 720px);
  border: none;
  border-radius: 10px;
  background: #fff;
}
.switch-line { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: .9rem; }
.count { font-size: .85rem; color: var(--text-muted); }
.rag-toolbar-foot { margin-bottom: 10px; }
.btn-rag-toggle {
  font-size: .86rem;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px dashed #c7d2fe;
  background: #f8fafc;
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
}
.btn-rag-toggle:hover { background: #eef2ff; }
.rag-sync-panel {
  margin-bottom: 16px;
  padding: 16px 18px;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #fafbff, #fff);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}
.rag-sync-title { font-size: 1.05rem; margin: 0 0 10px; }
.rag-sync-desc { margin: 0 0 14px; font-size: .88rem; }
.rag-tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  border-bottom: 1px solid #eceff3;
  padding-bottom: 0;
}
.rag-tab {
  position: relative;
  border: none;
  background: transparent;
  padding: 10px 14px;
  font-size: .9rem;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.rag-tab:hover {
  color: var(--text-main);
}
.rag-tab.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}
.rag-tab-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  font-size: .72rem;
  font-weight: 700;
  line-height: 18px;
  text-align: center;
}
.rag-tab-badge--live {
  background: #dbeafe;
  color: #1d4ed8;
  min-width: auto;
  padding: 0 8px;
}
.rag-tab-panel {
  animation: rag-tab-in .18s ease;
}
@keyframes rag-tab-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.rag-backlog-block--tab {
  margin-top: 0;
}
.muted { color: var(--text-muted); }
.rag-stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}
.rag-eta-block {
  margin: 0 0 14px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #dbeafe;
  background: linear-gradient(180deg, #f8fbff, #fff);
}
.rag-eta-main {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 4px;
}
.rag-eta-time {
  font-size: 1.45rem;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: #1e40af;
}
.rag-eta-hint { margin: 0; font-size: .82rem; }
.rag-stats-row--backlog {
  grid-template-columns: repeat(4, 1fr);
}
.rag-backlog-block {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px dashed #dbeafe;
  border-radius: 12px;
  background: #f8fbff;
}
.rag-backlog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.rag-backlog-title {
  margin: 0;
  font-size: .92rem;
  font-weight: 600;
}
.rag-backlog-desc,
.rag-backlog-foot,
.rag-backlog-error {
  margin: 0 0 10px;
  font-size: .82rem;
}
.rag-backlog-foot {
  margin-bottom: 0;
}
.btn-linkish {
  border: none;
  background: transparent;
  color: var(--primary-color);
  font-size: .82rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.btn-linkish:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.rag-stat--total {
  border-color: #bfdbfe;
  background: #eff6ff;
}
.rag-stat {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rag-stat .lbl { font-size: .78rem; color: var(--text-muted); }
.rag-stat strong { font-size: 1.25rem; }
.rag-stat strong.ok { color: #059669; }
.rag-stat strong.warn { color: #b45309; }
.rag-stat strong.danger { color: #dc2626; }
.rag-progress-wrap { margin-bottom: 10px; }
.rag-progress-track {
  height: 10px;
  border-radius: 999px;
  background: #e5e7eb;
  overflow: hidden;
}
.rag-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  transition: width 0.35s ease;
}
.rag-progress-track--busy {
  background: linear-gradient(90deg, #e5e7eb, #eef2ff, #e5e7eb);
  background-size: 200% 100%;
  animation: rag-progress-track-shimmer 1.4s ease-in-out infinite;
}
.rag-progress-fill--pulse {
  width: 42% !important;
  max-width: 42%;
  animation: rag-progress-fill-slide 1.1s ease-in-out infinite;
  opacity: 0.95;
}
@keyframes rag-progress-track-shimmer {
  0% { background-position: 0% 0%; }
  100% { background-position: 200% 0%; }
}
@keyframes rag-progress-fill-slide {
  0% { transform: translateX(-30%); }
  100% { transform: translateX(190%); }
}
.rag-progress-label { display: block; margin-top: 6px; font-size: .8rem; color: var(--text-muted); }
.rag-sync-job-name {
  margin: 0 0 8px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rag-progress-track--minute-zones {
  background: linear-gradient(
    90deg,
    #ecfdf5 0%,
    #ecfdf5 33.333%,
    #bbf7d0 33.333%,
    #bbf7d0 66.666%,
    #86efac 66.666%,
    #86efac 100%
  );
}
.rag-batch-fill {
  transition: width 0.55s linear;
  background: linear-gradient(90deg, #34d399, #059669);
}
.rag-batch-hint { font-size: .82rem; margin-bottom: 10px; }
.rag-accelerate-line { margin: 0 0 12px; }
.rag-actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 10px; }
.rag-paused-hint { font-size: .84rem; margin: 0 0 8px; }
.btn {
  padding: 9px 16px;
  border-radius: 10px;
  font-size: .9rem;
  font-weight: 600;
  border: 1px solid transparent;
  cursor: pointer;
}
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.btn.primary {
  background: var(--primary-color, #6366f1);
  color: #fff;
}
.btn.secondary {
  background: #fff;
  border-color: #d1d5db;
  color: #334155;
}
.rag-done { font-size: .86rem; margin: 0 0 8px; }
.rag-log-wrap {
  border: 1px solid #eceff3;
  border-radius: 12px;
  background: #0f172a;
  color: #e2e8f0;
  max-height: 220px;
  overflow: auto;
  margin-bottom: 10px;
}
.rag-log-wrap:last-child {
  margin-bottom: 0;
}
.rag-log-title {
  padding: 8px 12px;
  font-size: .78rem;
  color: #94a3b8;
  border-bottom: 1px solid #1e293b;
}
.rag-log { list-style: none; margin: 0; padding: 8px 12px 12px; font-family: ui-monospace, monospace; font-size: .78rem; line-height: 1.45; }
.rag-log-line { margin-bottom: 4px; word-break: break-all; }
.load-state {
  text-align: center;
  color: #64748b;
  font-size: 0.82rem;
  padding: 16px 0 8px;
  min-height: 40px;
}
.error { color: var(--danger); margin-top: 8px; min-height: 20px; font-weight: 600; font-size: .9rem; }
@media (max-width: 1100px) {
  .jobs-center-layout { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .home-main { max-width: 100vw; }
  .jobs-toolbar { grid-template-columns: 1fr; }
  .jobs-toolbar-meta { align-items: flex-start; }
}
@media (max-width: 720px) {
  .home-main { padding: 0 10px 76px; }
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
</style>
