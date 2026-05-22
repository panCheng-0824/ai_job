<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { apiGet, apiPost } from "../api/client";
import FloatingFramePanel from "../components/FloatingFramePanel.vue";

const route = useRoute();
const studentPortrait = ref(null);
const error = ref("");
const query = ref("");
const jobs = ref([]);
const companies = ref([]);
const loading = ref(false);
/** 最近一次「开始匹配」请求耗时（毫秒），用于展示匹配时长 */
const lastMatchDurationMs = ref(null);
/** 匹配进行中：已流逝毫秒（定时刷新，用于等待态展示） */
const matchElapsedMs = ref(0);
let matchElapsedTimer = null;

function clearMatchElapsedTimer() {
  if (matchElapsedTimer != null) {
    clearInterval(matchElapsedTimer);
    matchElapsedTimer = null;
  }
}

function startMatchElapsedTimer(t0) {
  clearMatchElapsedTimer();
  matchElapsedMs.value = 0;
  matchElapsedTimer = setInterval(() => {
    matchElapsedMs.value = performance.now() - t0;
  }, 100);
}
/** 是否已执行过至少一次「开始匹配」（用于区分初始态与「暂无数据」） */
const recommendSearched = ref(false);
/** 当前在右侧展示推荐理由的岗位 id（点击左侧选中） */
const selectedJobId = ref(null);
/** 悬停预览：优先于选中态展示右侧理由 */
const hoverJobId = ref(null);
const copyBtnText = ref("复制 JSON");
/** LightRAG 检索摘要（与岗位同步知识库） */
const ragInfo = ref(null);
/** 与 `/api/skills/job-info-query` 返回的 `recommendation` 对齐：无匹配原因等（列表仍用 `jobs`） */
const recommendation = ref(null);
/** 是否使用语义相似缓存（需服务端 JOB_INFO_SEM_CACHE_ENABLED=1） */
const useSemanticCache = ref(true);
/** 最近一次匹配返回的 cache 元信息（命中时 API 顶层 cache.hit=true） */
const matchCacheMeta = ref(null);

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

/** 与 recommendation.recommended_jobs 按 job_id 对齐后的理由（优先用接口结构化字段） */
function reasonsForJob(job) {
  if (!job?.job_id) return [];
  const rec = recommendation.value?.recommended_jobs || [];
  const hit = rec.find((x) => x.job_id === job.job_id);
  if (hit?.match_reasons?.length) return hit.match_reasons;
  if (hit?.match_reason) return [hit.match_reason];
  const raw = job.match_reasons;
  if (Array.isArray(raw) && raw.length) return raw.map(String);
  return [];
}

const selectedJob = computed(() => {
  const id = selectedJobId.value;
  if (!id) return null;
  return (jobs.value || []).find((j) => j.job_id === id) || null;
});

/** 右侧理由区：悬停优先，否则为点击选中的岗位 */
const previewJob = computed(() => {
  const h = hoverJobId.value;
  if (h) return (jobs.value || []).find((j) => j.job_id === h) || null;
  return selectedJob.value;
});

const reasonPanelTitle = computed(() => {
  if (!previewJob.value) return "";
  return previewJob.value.job_title || previewJob.value.job_name || "岗位";
});

/** 当前预览岗位的推荐理由条目（供模板一次计算） */
const selectedReasonLines = computed(() => {
  if (!previewJob.value) return [];
  return reasonsForJob(previewJob.value);
});

/** 右侧：无岗位时的说明（与后端 no_match_detail / rag 对齐） */
const noJobReasonBlocks = computed(() => {
  const rec = recommendation.value;
  const detail = rec?.no_match_detail;
  if (detail?.causes?.length) {
    return {
      headline: detail.title || "暂无推荐",
      causes: detail.causes,
      suggestions: detail.suggestions || []
    };
  }
  const parts = [];
  if (ragInfo.value?.hint) parts.push(String(ragInfo.value.hint));
  if (ragInfo.value?.detail) parts.push(String(ragInfo.value.detail));
  if (rec?.notes?.length) parts.push(rec.notes.join(" "));
  if (!parts.length) parts.push("当前条件下未返回可展示的推荐岗位，请调整诉求后重试。");
  return { headline: "暂无推荐", causes: parts, suggestions: [] };
});

/** 岗位详情弹层（与导航 Portal 弹框交互一致） */
const jobDetailFrameOpen = ref(false);
const jobDetailFrameFullscreen = ref(false);
const jobDetailIframeSrc = ref("");
const jobDetailFrameTitle = ref("");

function closeJobDetailFrame() {
  jobDetailFrameOpen.value = false;
  jobDetailFrameFullscreen.value = false;
  jobDetailIframeSrc.value = "";
  jobDetailFrameTitle.value = "";
}

function jobDetailEmbedUrl(path) {
  const u = new URL(path, window.location.origin);
  u.searchParams.set("_embed", "1");
  return u.pathname + u.search + u.hash;
}

function openJobDetailFrame(job) {
  if (!job?.job_id) return;
  const id = encodeURIComponent(String(job.job_id).trim());
  jobDetailFrameTitle.value = job.job_title || job.job_name || job.job_id || "岗位详情";
  jobDetailIframeSrc.value = jobDetailEmbedUrl(`/jobs/${id}`);
  jobDetailFrameOpen.value = true;
  jobDetailFrameFullscreen.value = false;
}

function toggleJobDetailFullscreen() {
  jobDetailFrameFullscreen.value = !jobDetailFrameFullscreen.value;
}

function openJobDetailFullWindow() {
  if (!jobDetailIframeSrc.value) return;
  const u = new URL(jobDetailIframeSrc.value, window.location.origin);
  u.searchParams.delete("_embed");
  const href = u.pathname + u.search + u.hash;
  window.open(href, "_blank", "noopener,noreferrer");
}

function selectJobForReason(job) {
  if (!job?.job_id) return;
  selectedJobId.value = job.job_id;
}

function onJobCardActivate(job) {
  if (!job?.job_id) return;
  selectJobForReason(job);
  openJobDetailFrame(job);
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

function getStudentId() {
  return route.query.student_id || localStorage.getItem("student_id") || "";
}

async function loadStudent() {
  const sid = getStudentId();
  if (!sid) return;
  try {
    studentPortrait.value = await apiGet(`/api/students/${encodeURIComponent(sid)}`);
  } catch (err) {
    error.value = err.message;
  }
}

function formatMatchDuration(ms) {
  if (!Number.isFinite(ms) || ms < 0) return "—";
  if (ms < 1000) return `${Math.max(1, Math.round(ms))} 毫秒`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)} 秒`;
  const m = Math.floor(ms / 60000);
  const s = ((ms % 60000) / 1000).toFixed(1);
  return `${m} 分 ${s} 秒`;
}

async function runRecommend() {
  if (!query.value.trim()) {
    error.value = "请输入岗位诉求后再查询";
    return;
  }
  loading.value = true;
  lastMatchDurationMs.value = null;
  matchCacheMeta.value = null;
  ragInfo.value = null;
  recommendation.value = null;
  selectedJobId.value = null;
  hoverJobId.value = null;
  const t0 = performance.now();
  startMatchElapsedTimer(t0);
  try {
    error.value = "";
    const s = studentInfo.value || {};
    const studentContext = [
      s["专业名称"] && `专业：${s["专业名称"]}`,
      s["学历"] && `学历：${s["学历"]}`,
      s["毕业年度"] && `毕业届别：${s["毕业年度"]}`,
      s["学校名称"] && `学校：${s["学校名称"]}`,
      s["院系名称"] && `院系：${s["院系名称"]}`
    ]
      .filter(Boolean)
      .join("；");
    const data = await apiPost("/api/skills/job-info-query", {
      query: query.value.trim(),
      top_n_jobs: 5,
      top_n_companies: 5,
      use_rag: true,
      use_semantic_cache: useSemanticCache.value,
      student_context: studentContext
    });
    jobs.value = data.jobs || [];
    companies.value = data.companies || [];
    ragInfo.value = data.rag || null;
    recommendation.value = data.recommendation || null;
    matchCacheMeta.value = data.cache && typeof data.cache === "object" ? data.cache : null;
    recommendSearched.value = true;
  } catch (err) {
    error.value = err.message;
    matchCacheMeta.value = null;
    recommendSearched.value = true;
  } finally {
    clearMatchElapsedTimer();
    const elapsed = performance.now() - t0;
    matchElapsedMs.value = elapsed;
    lastMatchDurationMs.value = elapsed;
    loading.value = false;
  }
}

onBeforeUnmount(() => {
  clearMatchElapsedTimer();
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

onMounted(() => {
  loadStudent();
  document.addEventListener("keydown", onJobDetailDocKey);
});
</script>

<template>
  <div>
    <section class="hero">
      <span class="badge">Student Center</span>
      <h1>学生信息与岗位洞察中心</h1>
      <p>当前登录账号：<code>{{ studentInfo?.["学号"] || "-" }}</code></p>
    </section>
    <div class="container">
      <main style="display: flex; flex-direction: column; gap: 16px;">
        <section class="panel">
          <div class="metric-grid">
            <div class="metric"><p>身份编号</p><strong>{{ studentInfo?.["学号"] || "-" }}</strong></div>
            <div class="metric"><p>姓名</p><strong>{{ studentInfo?.["姓名"] || "-" }}</strong></div>
            <div class="metric"><p>专业方向</p><strong>{{ majorText }}</strong></div>
          </div>
          <p class="error">{{ error }}</p>
          <div class="panel-head">
            <h2 class="section-title">完整学生资料</h2>
            <button class="toggle" @click="copyJson">{{ copyBtnText }}</button>
          </div>
          <div class="form-grid">
            <label v-for="item in baseFields" :key="item.label" class="field">
              <span>{{ item.label }}</span>
              <input :value="item.value ?? '-'" readonly />
            </label>
          </div>
          <details class="collapse-wrap">
            <summary>展开家庭信息（{{ familyInfoList.length }} 条）</summary>
            <div class="collapse-body">
              <div v-if="!familyInfoList.length" class="empty-tip">暂无家庭信息</div>
              <div v-for="(item, idx) in familyInfoList" v-else :key="`${item['学号']}-${idx}`" class="sub-card">
                <div class="sub-title">家庭成员 {{ idx + 1 }}</div>
                <div class="form-grid">
                  <label class="field"><span>学号</span><input :value="item['学号'] ?? '-'" readonly /></label>
                  <label class="field"><span>家长姓名</span><input :value="item['家长姓名'] || '-'" readonly /></label>
                  <label class="field"><span>与本人关系</span><input :value="item['与本人关系'] || '-'" readonly /></label>
                  <label class="field"><span>家长出生日期</span><input :value="item['家长出生日期'] || '-'" readonly /></label>
                  <label class="field"><span>证件类型</span><input :value="item['证件类型'] || '-'" readonly /></label>
                  <label class="field"><span>家长证件号</span><input :value="item['家长证件号'] || '-'" readonly /></label>
                  <label class="field"><span>家长单位</span><input :value="item['家长单位'] || '-'" readonly /></label>
                  <label class="field"><span>家长职务</span><input :value="item['家长职务'] || '-'" readonly /></label>
                  <label class="field"><span>家长职业</span><input :value="item['家长职业'] || '-'" readonly /></label>
                  <label class="field"><span>家长邮政编码</span><input :value="item['家长邮政编码'] || '-'" readonly /></label>
                  <label class="field"><span>家长联系电话</span><input :value="item['家长联系电话'] || '-'" readonly /></label>
                  <label class="field"><span>家长手机号</span><input :value="item['家长手机号'] || '-'" readonly /></label>
                  <label class="field"><span>平均月收入</span><input :value="item['平均月收入'] ?? '-'" readonly /></label>
                </div>
              </div>
            </div>
          </details>
          <details class="collapse-wrap">
            <summary>展开获奖信息（{{ awardInfoList.length }} 条）</summary>
            <div class="collapse-body">
              <div v-if="!awardInfoList.length" class="empty-tip">暂无获奖信息</div>
              <div v-for="(item, idx) in awardInfoList" v-else :key="`${item['学号']}-${idx}`" class="sub-card">
                <div class="sub-title">获奖记录 {{ idx + 1 }}</div>
                <div class="form-grid">
                  <label class="field"><span>学号</span><input :value="item['学号'] ?? '-'" readonly /></label>
                  <label class="field"><span>奖项年度</span><input :value="item['奖项年度'] ?? '-'" readonly /></label>
                  <label class="field"><span>项目名称</span><input :value="item['项目名称'] || '-'" readonly /></label>
                  <label class="field"><span>项目类别</span><input :value="item['项目类别'] || '-'" readonly /></label>
                  <label class="field field-wide"><span>项目描述</span><textarea :value="item['项目描述'] || '-'" rows="3" readonly /></label>
                </div>
              </div>
            </div>
          </details>
          <details class="collapse-wrap">
            <summary>展开心理咨询记录（{{ counselingRecordList.length }} 条）</summary>
            <div class="collapse-body">
              <div v-if="!counselingRecordList.length" class="empty-tip">暂无心理咨询记录</div>
              <div v-for="(item, idx) in counselingRecordList" v-else :key="`${item['申请ID']}-${idx}`" class="sub-card">
                <div class="sub-title">咨询记录 {{ idx + 1 }}</div>

                <div class="form-grid psych-grid">
                  <label class="field"><span>申请ID</span><input :value="item['申请ID'] || '-'" readonly /></label>
                  <label class="field"><span>学号</span><input :value="item['学号'] ?? '-'" readonly /></label>
                  <label class="field"><span>年度</span><input :value="item['年度'] ?? '-'" readonly /></label>
                  <label class="field"><span>咨询时间</span><input :value="item['咨询时间'] || '-'" readonly /></label>
                  <label class="field field-wide"><span>咨询议题</span><textarea :value="item['咨询议题'] || '-'" rows="2" readonly /></label>
                  <label class="field field-wide"><span>咨询效果</span><textarea :value="item['咨询效果'] || '-'" rows="2" readonly /></label>
                </div>
              </div>
            </div>
          </details>
          <details class="collapse-wrap">
            <summary>展开心理干预记录（{{ counselorRecordList.length }} 条）</summary>
            <div class="collapse-body">
              <div v-if="!counselorRecordList.length" class="empty-tip">暂无心理干预记录</div>
              <div v-for="(item, idx) in counselorRecordList" v-else :key="`${item['记录ID']}-${idx}`" class="sub-card">
                <div class="sub-title">干预记录 {{ idx + 1 }}</div>

                <div class="form-grid psych-grid">
                  <label class="field"><span>记录ID</span><input :value="item['记录ID'] || '-'" readonly /></label>
                  <label class="field"><span>学号</span><input :value="item['学号'] ?? '-'" readonly /></label>
                  <label class="field"><span>咨询申请ID</span><input :value="item['咨询申请ID'] || '-'" readonly /></label>
                  <label class="field"><span>咨询时间</span><input :value="item['咨询时间'] || '-'" readonly /></label>
                  <label class="field field-wide"><span>咨询概要</span><textarea :value="item['咨询概要'] || '-'" rows="3" readonly /></label>
                </div>
              </div>
            </div>
          </details>
          <details class="collapse-wrap">
            <summary>展开心理跟踪记录（{{ trackingRecordList.length }} 条）</summary>
            <div class="collapse-body">
              <div v-if="!trackingRecordList.length" class="empty-tip">暂无心理跟踪记录</div>
              <div v-for="(item, idx) in trackingRecordList" v-else :key="`${item['档案主键']}-${idx}`" class="sub-card">
                <div class="sub-title">跟踪记录 {{ idx + 1 }}</div>

                <div class="form-grid psych-grid">
                  <label class="field"><span>学号</span><input :value="item['学号'] ?? '-'" readonly /></label>
                  <label class="field"><span>档案主键</span><input :value="item['档案主键'] || '-'" readonly /></label>
                  <label class="field"><span>咨询ID</span><input :value="item['咨询ID'] || '-'" readonly /></label>
                  <label class="field"><span>添加时间</span><input :value="item['添加时间'] || '-'" readonly /></label>
                  <label class="field field-wide"><span>寻求问题</span><textarea :value="item['寻求问题'] || '-'" rows="2" readonly /></label>
                  <label class="field field-wide"><span>问题评估</span><textarea :value="item['问题评估'] || '-'" rows="2" readonly /></label>
                  <label class="field field-wide"><span>咨询效果</span><textarea :value="item['咨询效果'] || '-'" rows="2" readonly /></label>
                  <label class="field"><span>学生状态</span><input :value="item['学生状态'] || '-'" readonly /></label>
                  <label class="field"><span>院系合作</span><input :value="item['院系合作'] || '-'" readonly /></label>
                  <label class="field field-wide"><span>其他情况</span><textarea :value="item['其他情况'] || '-'" rows="2" readonly /></label>
                </div>
              </div>
            </div>
          </details>
          <details class="collapse-wrap">
            <summary>展开完整学生资料</summary>
            <div class="collapse-body">
              <pre>{{ fullPortraitJson || "加载中..." }}</pre>
            </div>
          </details>
        </section>

        <section class="panel">
          <h2 class="section-title">岗位推荐联动查询</h2>
          
          <div class="line">
            <input v-model="query" placeholder="例如：想找杭州前端、双休、成长空间好的岗位" @keydown.enter.prevent="runRecommend" />
            <button class="match-btn" :class="{ 'match-btn--busy': loading }" :disabled="loading" @click="runRecommend">
              {{ loading ? "匹配中…" : "开始匹配" }}
            </button>
          </div>
          <label class="switch-line">
            <input v-model="useSemanticCache" type="checkbox" />
            使用语义缓存
          </label>
          <p v-if="loading" class="match-duration match-duration--live">
            已匹配时长 {{ formatMatchDuration(matchElapsedMs) }}
          </p>
          <p
            v-else-if="recommendSearched && lastMatchDurationMs != null"
            class="match-duration"
          >
            本次匹配用时 {{ formatMatchDuration(lastMatchDurationMs) }}
            <span v-if="cacheHitActive" class="match-duration-cache-tag">（缓存）</span>
          </p>
          <div
            v-if="recommendSearched && cacheHitActive && !loading"
            class="cache-hit-banner"
            role="status"
          >
            <span class="cache-hit-badge">{{ cacheHitTitle }}</span>
            <span v-if="cacheHitDetail" class="cache-hit-detail">{{ cacheHitDetail }}</span>
            <span class="cache-hit-hint">结果来自历史推荐，未重新检索知识库与大模型分析</span>
          </div>
          <div class="match-block">
            <div v-if="loading" class="match-overlay" role="status" aria-live="polite">
              <div class="match-spinner" aria-hidden="true" />
              <p class="match-overlay-title">正在匹配岗位</p>
              <p class="match-overlay-elapsed">已匹配时长 {{ formatMatchDuration(matchElapsedMs) }}</p>
              <p class="match-overlay-sub">检索知识库并整理推荐结果…</p>
            </div>
            <div class="result-grid" :class="{ 'result-grid--matching': loading }">
            <div class="result-col">
              <h3 class="section-title">推荐岗位</h3>
              <ul class="mini-list">
                <li v-if="loading" class="match-list-spacer" aria-hidden="true" />
                <li v-else-if="!recommendSearched" class="empty-tip">输入诉求后点击「开始匹配」</li>
                <li v-else-if="!jobs.length" class="empty-tip">暂无数据</li>
                <li
                  v-else
                  v-for="item in jobs"
                  :key="item.job_id"
                  class="job-pick"
                  :class="{
                    'job-pick--active': selectedJobId === item.job_id,
                    'job-pick--hover': hoverJobId === item.job_id
                  }"
                  role="button"
                  tabindex="0"
                  @click="onJobCardActivate(item)"
                  @keydown.enter.prevent="onJobCardActivate(item)"
                  @mouseenter="hoverJobId = item.job_id"
                  @mouseleave="hoverJobId = null"
                >
                  <div class="job-pick-head">
                    <span class="job-pick-title">{{ item.job_title || "-" }}</span>
                  </div>
                  <p class="job-pick-meta job-pick-ids">
                    <span class="mono">ID {{ item.job_id || "-" }}</span>
                    <span v-if="item.score != null && item.score !== ''" class="job-score"
                      >匹配分 {{ item.score }}</span
                    >
                  </p>
                  <p class="job-pick-meta">
                    {{ item.city || "-" }} {{ item.district || "" }} ｜
                    {{ item.company_name || item.company_relation?.company_name || "-" }}
                  </p>
                </li>
              </ul>
            </div>
            <div class="result-col reason-panel">
              <h3 class="section-title">推荐理由</h3>
              <div v-if="loading" class="reason-panel-spacer" aria-hidden="true" />
              <template v-else-if="!jobs.length">
                <template v-if="!recommendSearched">
                  <p class="muted reason-placeholder">请先完成左侧岗位匹配查询。</p>
                </template>
                <template v-else>
                  <p class="reason-headline">{{ noJobReasonBlocks.headline }}</p>
                  <p class="muted reason-sub">未推荐岗位的可能原因：</p>
                  <ul class="reason-list">
                    <li v-for="(c, idx) in noJobReasonBlocks.causes" :key="'c-' + idx">{{ c }}</li>
                  </ul>
                  <template v-if="noJobReasonBlocks.suggestions?.length">
                    <p class="muted reason-sub">建议：</p>
                    <ul class="reason-list">
                      <li v-for="(s, idx) in noJobReasonBlocks.suggestions" :key="'s-' + idx">{{ s }}</li>
                    </ul>
                  </template>
                </template>
              </template>
              <template v-else>
                <p v-if="!previewJob" class="muted reason-placeholder">
                  悬停卡片查看推荐理由；点击卡片打开岗位详情（标题栏拖动、边缘缩放、可放大或新标签页打开）。
                </p>
                <template v-else>
                  <p class="reason-job-title">{{ reasonPanelTitle }}</p>
                  <ul v-if="selectedReasonLines.length" class="reason-list">
                    <li v-for="(line, idx) in selectedReasonLines" :key="idx">{{ line }}</li>
                  </ul>
                  <p v-else class="muted reason-placeholder">该岗位暂无单独生成的推荐理由（可能为检索排序展示）。</p>
                </template>
              </template>
            </div>
          </div>
          </div>
          <details v-if="ragInfo?.enabled && ragInfo.answer_preview" class="rag-details">
            <summary>查看本次 RAG 检索摘要</summary>
            <pre class="rag-pre">{{ ragInfo.answer_preview }}</pre>
          </details>
          <p v-else-if="ragInfo && !ragInfo.enabled" class="muted rag-fallback">
            本次为规则匹配（RAG：{{ ragInfo.mode || "未启用" }}<template v-if="ragInfo.detail"> — {{ ragInfo.detail }}</template>）。
          </p>
        </section>
      </main>
    </div>

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
  </div>
</template>

<style scoped>
.hero { padding: 86px 20px 50px; text-align: center; background: radial-gradient(circle at top right, #eef2ff, transparent), radial-gradient(circle at top left, #f5f3ff, transparent); }
.badge { display: inline-block; padding: 5px 15px; background: #e0e7ff; color: var(--primary-color); border-radius: 20px; font-size: .85rem; font-weight: 600; margin-bottom: 14px; }
.hero h1 { font-size: clamp(2.1rem, 5vw, 3rem); margin-bottom: 10px; }
.hero p { color: var(--text-muted); }
.container { max-width: 1100px; margin: 0 auto; padding: 0 20px 80px; }
.panel { background: #fff; border: 1px solid rgba(31,41,55,.08); border-radius: 18px; box-shadow: 0 10px 30px rgba(15,23,42,.06); padding: 18px; }
.metric-grid { display: grid; gap: 12px; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 16px; }
.metric { border: 1px solid #eceff3; border-radius: 14px; padding: 12px; background: linear-gradient(180deg, #fff, #fcfcff); }
.metric p { color: var(--text-muted); font-size: .82rem; }
.metric strong { display: block; margin-top: 6px; font-size: 1.02rem; }
.panel-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.section-title { font-size: 1rem; margin-bottom: 10px; }
.toggle { border: 1px solid #d1d5db; border-radius: 999px; padding: 7px 10px; background: #fff; cursor: pointer; font-size: .8rem; color: var(--text-main); }
.collapse-wrap { border: 1px solid #eceff3; border-radius: 12px; background: #fff; padding: 8px 10px; }
.collapse-wrap + .collapse-wrap { margin-top: 10px; }
.collapse-wrap > summary { cursor: pointer; color: var(--primary-color); font-size: .9rem; font-weight: 600; user-select: none; }
.collapse-body { margin-top: 10px; }
.form-grid { display: grid; gap: 10px; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 10px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: .78rem; color: var(--text-muted); }
.field input, .field textarea { width: 100%; border: 1px solid #dbe1ea; border-radius: 10px; padding: 9px 10px; background: #f8fafc; color: #111827; font-size: .86rem; }
.field textarea { resize: vertical; min-height: 72px; }
.field-wide { grid-column: 1 / -1; }
.sub-card { border: 1px solid #eceff3; border-radius: 12px; padding: 10px; background: #fcfcff; margin-bottom: 10px; }
.sub-title { font-size: .88rem; font-weight: 600; margin-bottom: 8px; color: #374151; }
.psych-meta { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 0 0 10px; }
.psych-meta span { background: #eef2ff; color: #3730a3; font-size: .78rem; padding: 6px 8px; border-radius: 8px; border: 1px solid #dbeafe; }
.psych-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.empty-tip { color: var(--text-muted); font-size: .9rem; padding: 10px; border: 1px dashed #d1d5db; border-radius: 10px; }
pre { margin: 0; border-radius: 10px; background: #0f172a; color: #f8fafc; padding: 12px; max-height: 34vh; overflow: auto; font-size: .78rem; }
.line { display: grid; grid-template-columns: 1fr auto; gap: 10px; margin-bottom: 10px; }
.switch-line { display: flex; align-items: center; gap: 8px; margin: 0 0 10px; color: var(--text-muted); font-size: .9rem; }
input, button { padding: 10px 12px; border-radius: 10px; border: 1px solid #d1d5db; }
button { border: none; background: var(--primary-color); color: #fff; font-weight: 600; }
.result-grid { display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }
.result-col { min-width: 0; }
.job-pick { cursor: pointer; user-select: none; transition: border-color 0.15s, background 0.15s; }
.job-pick:focus { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.job-pick--active { border-color: #a5b4fc !important; background: #eef2ff !important; }
.job-pick--hover { border-color: #c7d2fe !important; background: #f8fafc !important; }
.job-pick-head { display: flex; align-items: flex-start; justify-content: flex-start; gap: 8px; }
.job-pick-title { font-weight: 600; color: #111827; font-size: 0.92rem; flex: 1; min-width: 0; }
.job-pick-meta { color: var(--text-muted); font-size: 0.8rem; margin-top: 6px !important; }
.job-pick-ids { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: center; margin-top: 4px !important; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.72rem; color: #64748b; word-break: break-all; }
.job-score { font-weight: 600; color: #4338ca; font-size: 0.78rem; }
.reason-panel { border: 1px solid #eceff3; border-radius: 12px; padding: 12px; background: #fafafa; min-height: 120px; }
.reason-headline { font-weight: 700; color: #1e293b; margin: 0 0 8px; font-size: 0.95rem; }
.reason-job-title { font-weight: 700; color: #1e293b; margin: 0 0 10px; font-size: 0.95rem; }
.reason-sub { margin: 10px 0 6px; font-size: 0.82rem; }
.reason-list { margin: 0; padding-left: 1.1rem; color: #374151; font-size: 0.88rem; line-height: 1.55; }
.reason-list li { margin-bottom: 6px; }
.reason-placeholder { margin: 0; padding: 8px 0; font-size: 0.88rem; }
.rag-hint { font-size: 0.82rem; color: var(--text-muted, #6b7280); margin: -4px 0 10px; line-height: 1.45; }
.rag-details { margin-top: 12px; border: 1px solid #e5e7eb; border-radius: 10px; padding: 8px 10px; background: #fafafa; }
.rag-details > summary { cursor: pointer; font-size: 0.86rem; font-weight: 600; color: var(--primary-color, #6366f1); }
.rag-pre { margin: 8px 0 0; white-space: pre-wrap; word-break: break-word; font-size: 0.78rem; line-height: 1.45; color: #374151; max-height: 220px; overflow: auto; }
.rag-fallback { margin-top: 10px; font-size: 0.8rem; }
.mini-list { list-style: none; display: grid; gap: 8px; padding: 0; }
.mini-list li { border: 1px solid #eceff3; border-radius: 10px; padding: 10px; }
.mini-list a { color: var(--primary-color); text-decoration: none; font-weight: 600; font-size: .9rem; }
.mini-list p { color: var(--text-muted); font-size: .8rem; margin-top: 4px; }
.match-duration { margin: 0 0 12px; font-size: 0.86rem; color: #4338ca; font-weight: 600; }
.match-duration-cache-tag { margin-left: 6px; color: #059669; font-weight: 700; }
.match-duration--live { color: #6366f1; animation: match-duration-pulse 1.5s ease-in-out infinite; }
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
  line-height: 1.45;
}
.cache-hit-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: #059669;
  color: #fff;
  font-weight: 700;
  font-size: 0.78rem;
  white-space: nowrap;
}
.cache-hit-detail { color: #047857; font-weight: 600; }
.cache-hit-hint { color: #6b7280; font-size: 0.8rem; }
@keyframes match-duration-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.72; }
}
.match-overlay-elapsed {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #4338ca;
}
.match-block { position: relative; min-height: 160px; }
.match-overlay {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px 16px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(6px);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.18);
  animation: match-overlay-in 0.28s ease;
}
@keyframes match-overlay-in {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}
.match-spinner {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: 3px solid #e5e7eb;
  border-top-color: var(--primary-color, #6366f1);
  animation: match-spin 0.72s linear infinite;
}
@keyframes match-spin {
  to { transform: rotate(360deg); }
}
.match-overlay-title { margin: 0; font-size: 1rem; font-weight: 700; color: #1e293b; }
.match-overlay-sub { margin: 0; font-size: 0.82rem; color: var(--text-muted); }
.result-grid--matching { opacity: 0.42; pointer-events: none; transition: opacity 0.2s ease; }
.match-btn--busy { box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.35); animation: match-btn-pulse 1.2s ease-in-out infinite; }
@keyframes match-btn-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25); }
  50% { box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2); }
}
.match-list-spacer { min-height: 120px; list-style: none; border: none !important; padding: 0 !important; background: transparent !important; }
.reason-panel-spacer { min-height: 100px; }
.error { color: var(--danger); font-size: .9rem; font-weight: 600; min-height: 20px; margin-bottom: 10px; }
@media (max-width: 980px) { .metric-grid { grid-template-columns: 1fr; } .result-grid { grid-template-columns: 1fr; } .form-grid { grid-template-columns: 1fr; } .psych-meta { grid-template-columns: 1fr; } .psych-grid { grid-template-columns: 1fr; } }
</style>
