<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiDelete, apiGet, apiPost, getStudentId } from "../api/client";
import { resolveDictLabel } from "../utils/dictLabel";
import { sanitizeRichHtml } from "../utils/richText";
import RagSyncThreeMinuteProgress from "../components/rag/RagSyncThreeMinuteProgress.vue";
import { useRagSyncThreeMinuteProgress } from "../composables/useRagSyncThreeMinuteProgress";

const props = defineProps({
  embeddedJobId: { type: String, default: "" }
});

const route = useRoute();
const job = ref(null);
/** 公司性质展示文案（后端未翻译时前端按 job_dwxz 字典兜底） */
const companyTypeLabel = ref("-");
const related = ref([]);
const error = ref("");
const syncLoading = ref(false);
const unsyncLoading = ref(false);
const syncMessage = ref("");
const ragSyncPreview = ref(null);
const activeNlqxCode = ref(null);

const jobTagDefs = ref([]);
const jobTagLabelMap = computed(() => {
  const m = {};
  (jobTagDefs.value || []).forEach((t) => {
    if (t?.id) m[t.id] = t.label || t.id;
  });
  return m;
});

const ctx = ref(null);
const reviewStars = ref(5);
const reviewComment = ref("");
const selectedTagIds = ref([]);
const reviewHint = ref("");
const publicReviews = ref(null);

const ragSyncProgress = useRagSyncThreeMinuteProgress();
const {
  running: ragSyncRunning,
  elapsedMs: ragSyncElapsedMs,
  fillPct: ragSyncFillPct,
  fillPctRounded: ragSyncFillPctRounded,
  fillColorClass: ragSyncFillColorClass,
  progressLabel: ragSyncProgressLabel,
  overScale: ragSyncOverScale,
  start: startRagSyncProgress,
  stop: stopRagSyncProgress,
} = ragSyncProgress;

const normalizedJob = computed(() => {
  if (!job.value) return null;
  return {
    job_id: job.value.id,
    job_title: job.value.jobName,
    city: job.value.address,
    district: job.value.area,
    salary_range_month: job.value.salaryRange,
    salary_months: "-",
    company_relation: {
      company_name: job.value.companyName,
      credit_code: job.value.companyWid || job.value.companyId
    }
  };
});
const normalizedRelated = computed(() =>
  (related.value || []).map((item) => ({
    job_id: item.id,
    job_title: item.jobName,
    city: item.address,
    district: item.area,
    salary_range_month: item.salaryRange,
    salary_months: "-",
    company_relation: {
      company_name: item.companyName,
      credit_code: item.companyWid || item.companyId
    }
  }))
);

const companyLink = computed(() => {
  const pageId = job.value?.companyWid || job.value?.companyId || "";
  return pageId ? `/companies/${encodeURIComponent(pageId)}` : "/companies";
});

/** 空值统一展示为「-」 */
function fmt(v) {
  if (v === null || v === undefined) return "-";
  const s = String(v).trim();
  return s || "-";
}

const kvRows = computed(() => {
  const data = normalizedJob.value;
  if (!data) return [];
  return [
    ["所属企业", data.company_relation?.company_name || "-"],
    ["工作地点", fmt(job.value?.address || job.value?.gzdd)],
    ["月薪级别", fmt(job.value?.salaryRange)],
    ["工作地区", fmt(job.value?.area)]
  ];
});

const gjzGroups = computed(() => job.value?.gjzGroups || []);
const nlqxItems = computed(() => job.value?.nlqxItems || []);
const activeNlqxItem = computed(
  () => nlqxItems.value.find((item) => item.code === activeNlqxCode.value) || null
);
const ragSyncPreviewJson = computed(() =>
  ragSyncPreview.value ? JSON.stringify(ragSyncPreview.value, null, 2) : ""
);
const ragPreviewHint = computed(() => {
  const n = ragSyncPreview.value?.textLength;
  return n != null ? `字典翻译 + RAG 正文 · ${n} 字` : "字典翻译 + RAG 正文";
});

/** 折叠区块摘要：取前几条非空字段值 */
function fieldPreviewValue(field) {
  if (field?.kind === "nlqx") {
    const items = nlqxItems.value;
    if (items.length) return items.map((item) => item.label).join("、");
    const j = job.value || {};
    return fmt(j.nlqxText);
  }
  return String(field?.value ?? "").trim();
}

function sectionPreview(fields, max = 2) {
  const parts = (fields || [])
    .map((f) => fieldPreviewValue(f))
    .filter((v) => v && v !== "-")
    .slice(0, max);
  return parts.length ? parts.join(" · ") : "点击展开查看";
}

function gjzPreview(groups) {
  const list = groups || [];
  if (!list.length) return "";
  const total = list.reduce((n, g) => n + (g.keywords?.length || 0), 0);
  const sample = list
    .flatMap((g) => g.keywords || [])
    .slice(0, 3)
    .join("、");
  return total ? `${total} 个${sample ? ` · ${sample}` : ""}` : "点击展开查看";
}

const detailSections = computed(() => {
  const j = job.value || {};
  const synRagStatus =
    j.synRag === "1" || j.synRag === 1
      ? "已同步"
      : j.synRag === "0" || j.synRag === 0
        ? "未同步"
        : fmt(j.synRag);
  return [
    {
      title: "企业与地点",
      fields: [
        { label: "用人单位", value: fmt(j.companyName) },
        { label: "用人单位ID", value: fmt(j.companyId || j.yrdw) },
        { label: "公司性质", value: fmt(companyTypeLabel.value) },
        { label: "行业类型", value: fmt(j.industry) },
        { label: "工作地点", value: fmt(j.address || j.gzdd) },
        { label: "工作地区", value: fmt(j.area) }
      ]
    },
    {
      title: "岗位基础信息",
      fields: [
        { label: "职位名称", value: fmt(j.jobName || j.zwmc) },
        { label: "职位类别", value: fmt(j.zwlbText) },
        { label: "需求人数", value: fmt(j.vacancies) },
        { label: "截止日期", value: fmt(j.jzrq) },
        { label: "年度", value: fmt(j.nd) }
      ]
    },
    {
      title: "任职要求与薪资",
      fields: [
        { label: "学历要求", value: fmt(j.xlyqText || j.education) },
        { label: "月薪级别", value: fmt(j.salaryRange) },
        { label: "能力需求", kind: "nlqx" },
        { label: "性别要求", value: fmt(j.xbyqText) },
        { label: "实习期", value: fmt(j.sxqText) }
      ]
    },
    {
      title: "联系信息",
      fields: [
        { label: "联系人", value: fmt(j.lxr) },
        { label: "联系人邮箱", value: fmt(j.lxryx) },
        { label: "联系人电话", value: fmt(j.lxrdh) },
        { label: "联系人手机", value: fmt(j.lxrsjh) },
        { label: "联系人QQ", value: fmt(j.lxrqq) },
        { label: "联系人微信", value: fmt(j.lxrwx) }
      ]
    },
    {
      title: "时间与知识库",
      fields: [
        { label: "生效时间", value: fmt(j.sxsj) },
        { label: "创建时间", value: fmt(j.createTime) },
        { label: "知识库同步", value: synRagStatus },
        { label: "文档路径", value: fmt(j.ragMdPath) }
      ]
    }
  ];
});

const jobId = computed(() => props.embeddedJobId || String(route.params.job_id || "").trim());

/** 职位描述富文本（zwms / content） */
const jobDescriptionHtml = computed(() =>
  sanitizeRichHtml(job.value?.content || job.value?.zwms || "")
);

const loggedIn = computed(() => Boolean(getStudentId()));
const jobFavorited = computed(() => Boolean(ctx.value?.job_favorited));
const hasMyReview = computed(() => Boolean(ctx.value?.my_job_review));

/** 岗位是否已同步至知识库（RAG） */
const jobRagSynced = computed(() => {
  const j = job.value;
  if (!j) return false;
  return j.synRag === "1" || j.synRag === 1 || j.synRag === true;
});

/** 同步按钮文案：已同步为「重新同步」，否则为「待同步」 */
const syncButtonLabel = computed(() => {
  if (syncLoading.value) return "同步中...";
  return jobRagSynced.value ? "重新同步" : "待同步";
});

const unsyncButtonLabel = computed(() => {
  if (unsyncLoading.value) return "下架中...";
  return "下架";
});

const currentSyncJobName = computed(() => {
  if (!syncLoading.value) return "";
  return job.value?.jobName || job.value?.zwmc || normalizedJob.value?.job_title || "";
});

/** 标题区状态标签：同步 /（登录后）评价、收藏，正负态均展示 */
const jobStatusChips = computed(() => {
  if (!job.value) return [];
  const chips = [];
  chips.push({
    label: jobRagSynced.value ? "已同步" : "未同步",
    variant: jobRagSynced.value ? "tip-chip--ok" : "tip-chip--warn",
  });
  if (!loggedIn.value) return chips;
  chips.push({
    label: hasMyReview.value ? "已评价" : "未评价",
    variant: hasMyReview.value ? "tip-chip--ok" : "tip-chip--muted",
  });
  chips.push({
    label: jobFavorited.value ? "已收藏" : "未收藏",
    variant: jobFavorited.value ? "tip-chip--ok" : "tip-chip--muted",
  });
  return chips;
});

const aggJobText = computed(() => {
  const j = publicReviews.value;
  if (!j) return "加载中…";
  if (j.detail) return j.detail;
  if (!j.count) return "暂时还没有评价，欢迎成为第一个打分的人。";
  const dist = (j.review_tag_distribution || [])
    .map((x) => `${jobTagLabelMap.value[x.tag_id] || x.tag_id} ${x.count} 次`)
    .join("；");
  return `共 ${j.count} 条评价，平均 ${j.avg_stars} 星` + (dist ? `。标签分布：${dist}` : "");
});

function toggleNlqx(code) {
  activeNlqxCode.value = activeNlqxCode.value === code ? null : code;
}

async function loadRagPreview() {
  const jid = jobId.value;
  if (!jid) {
    ragSyncPreview.value = null;
    return;
  }
  try {
    ragSyncPreview.value = await apiGet(`/api/jobs/${encodeURIComponent(jid)}/rag-preview`);
  } catch {
    ragSyncPreview.value = null;
  }
}

async function loadJobTagCatalog() {
  try {
    const c = await apiGet("/api/review-tags");
    jobTagDefs.value = c.job_review_tags || [];
  } catch {
    jobTagDefs.value = [];
  }
}

async function refreshJobContext() {
  const sid = getStudentId();
  const jid = jobId.value;
  if (!sid || !jid) {
    ctx.value = null;
    return;
  }
  try {
    const q = new URLSearchParams({ student_id: sid, job_id: jid });
    ctx.value = await apiGet(`/api/me/context?${q}`);
    const mr = ctx.value?.my_job_review;
    if (mr) {
      reviewStars.value = Math.min(5, Math.max(1, Number(mr.stars) || 5));
      reviewComment.value = mr.comment || "";
      selectedTagIds.value = [...(mr.tags || [])];
    } else {
      reviewStars.value = 5;
      reviewComment.value = "";
      selectedTagIds.value = [];
    }
  } catch {
    ctx.value = null;
  }
}

async function loadPublicJobReviews() {
  const jid = jobId.value;
  if (!jid) return;
  try {
    publicReviews.value = await apiGet(`/api/jobs/${encodeURIComponent(jid)}/reviews`);
  } catch (e) {
    publicReviews.value = { count: 0, items: [], detail: e.message };
  }
}

async function loadRelatedJobs(yrdw, excludeJobId = "", limit = 8) {
  const code = String(yrdw || "").trim();
  if (!code) {
    related.value = [];
    return;
  }
  const params = new URLSearchParams({ yrdw: code, limit: String(limit) });
  if (excludeJobId) params.set("excludeJobId", excludeJobId);
  try {
    related.value = await apiGet(`/api/jobs/by-company?${params}`);
  } catch {
    related.value = [];
  }
}

async function loadCompanyJobs(yrdw, limit = 12) {
  const code = String(yrdw || "").trim();
  if (!code) {
    jobs.value = [];
    return;
  }
  const params = new URLSearchParams({ yrdw: code, limit: String(limit) });
  try {
    jobs.value = await apiGet(`/api/jobs/by-company?${params}`);
  } catch {
    jobs.value = [];
  }
}

async function loadJobDetail() {
  try {
    error.value = "";
    reviewHint.value = "";
    activeNlqxCode.value = null;
    const jid = jobId.value;
    const one = await apiGet(`/api/jobs/${encodeURIComponent(jid)}`);
    job.value = one;
    companyTypeLabel.value = await resolveDictLabel("job_dwxz", one?.companyType);
    await loadRelatedJobs(one?.companyId || one?.yrdw, jid, 8);

    await loadJobTagCatalog();
    if (getStudentId()) await refreshJobContext();
    else {
      ctx.value = null;
      reviewStars.value = 5;
      reviewComment.value = "";
      selectedTagIds.value = [];
    }
    await loadPublicJobReviews();
    await loadRagPreview();
  } catch (err) {
    error.value = err.message || "加载失败";
    job.value = null;
    companyTypeLabel.value = "-";
    ragSyncPreview.value = null;
  }
}

async function syncToKnowledgeBase() {
  if (!job.value?.id || syncLoading.value || unsyncLoading.value) return;
  syncLoading.value = true;
  syncMessage.value = "";
  error.value = "";
  startRagSyncProgress();
  try {
    const resp = await apiPost(`/api/jobs/${encodeURIComponent(job.value.id)}/sync-rag`, {});
    if (job.value) {
      job.value.synRag = "1";
      job.value.ragMdPath = resp?.ragMdPath || job.value.ragMdPath;
    }
    syncMessage.value = resp?.message || "同步成功";
    await loadRagPreview();
  } catch (err) {
    error.value = err.message || "同步失败";
  } finally {
    syncLoading.value = false;
    stopRagSyncProgress();
  }
}

async function unsyncFromKnowledgeBase() {
  if (!job.value?.id || !jobRagSynced.value || syncLoading.value || unsyncLoading.value) return;
  if (!window.confirm("确定下架该岗位的知识库数据？将删除 LightRAG / GrepRAG 同步内容，并标记为未同步。")) {
    return;
  }
  unsyncLoading.value = true;
  syncMessage.value = "";
  error.value = "";
  try {
    const resp = await apiPost(`/api/jobs/${encodeURIComponent(job.value.id)}/unsync-rag`, {});
    if (job.value) {
      job.value.synRag = "0";
      job.value.ragMdPath = "";
    }
    ragSyncPreview.value = null;
    syncMessage.value = resp?.message || "知识库下架成功";
  } catch (err) {
    error.value = err.message || "下架失败";
  } finally {
    unsyncLoading.value = false;
  }
}

async function toggleFavorite() {
  const sid = getStudentId();
  const jid = job.value?.id;
  if (!sid || !jid) {
    window.alert("请先登录");
    return;
  }
  try {
    await apiPost("/api/me/favorites/toggle", { student_id: sid, job_id: jid });
    await refreshJobContext();
  } catch (e) {
    window.alert(e.message || "操作失败");
  }
}

async function submitJobReview() {
  const sid = getStudentId();
  const jid = job.value?.id;
  if (!sid || !jid) {
    window.alert("请先登录");
    return;
  }
  try {
    await apiPost("/api/me/reviews/job", {
      student_id: sid,
      job_id: jid,
      stars: Number(reviewStars.value),
      comment: reviewComment.value.trim(),
      tags: [...selectedTagIds.value]
    });
    reviewHint.value = "已保存评价。";
    await loadPublicJobReviews();
    await refreshJobContext();
  } catch (e) {
    window.alert(e.message || "提交失败");
  }
}

async function deleteJobReview() {
  const sid = getStudentId();
  const jid = job.value?.id;
  if (!sid || !jid) return;
  if (!window.confirm("确定删除你对该岗位的评价？（可稍后重新提交）")) return;
  try {
    const q = new URLSearchParams({ student_id: sid, job_id: jid });
    const j = await apiDelete(`/api/me/reviews/job?${q}`);
    reviewHint.value = j.deleted ? "已删除评价。" : "当前没有可删除的评价。";
    await refreshJobContext();
    await loadPublicJobReviews();
  } catch (e) {
    window.alert(e.message || "删除失败");
  }
}

onMounted(loadJobDetail);

watch(
  () => route.params.job_id,
  (newVal, oldVal) => {
    if (newVal && newVal !== oldVal) {
      loadJobDetail();
    }
  }
);
</script>

<template>
  <div>
    <section class="hero">
      
      <h1>{{ normalizedJob?.job_title || "加载中..." }}</h1>
      <p>job_id：<code>{{ route.params.job_id }}</code></p>
      <div v-if="jobStatusChips.length" class="hero-tip-row" aria-label="岗位状态">
        <span
          v-for="(c, idx) in jobStatusChips"
          :key="`${c.label}-${idx}`"
          class="tip-chip"
          :class="c.variant"
        >{{ c.label }}</span>
      </div>
    </section>
    <div class="layout">
      <main class="panel">
        <div class="kv">
          <template v-for="([k, v], idx) in kvRows" :key="`${k}-${idx}`">
            <div class="k">{{ k }}</div>
            <div class="v">
              <router-link v-if="k === '所属企业'" :to="companyLink">{{ v }}</router-link>
              <template v-else>{{ v }}</template>
            </div>
          </template>
        </div>
        <div class="job-action-bar">
          <div class="job-action-bar__grid">
            <button
              type="button"
              class="btn primary job-action-cell"
              :disabled="syncLoading || unsyncLoading || !job"
              @click="syncToKnowledgeBase"
            >
              {{ syncButtonLabel }}
            </button>
            <button
              v-if="jobRagSynced"
              type="button"
              class="btn danger job-action-cell"
              :disabled="syncLoading || unsyncLoading || !job"
              @click="unsyncFromKnowledgeBase"
            >
              {{ unsyncButtonLabel }}
            </button>
            <button
              v-if="loggedIn"
              type="button"
              class="btn secondary job-action-cell"
              @click="toggleFavorite"
            >
              {{ jobFavorited ? "已收藏（取消）" : "收藏岗位" }}
            </button>
            <router-link v-if="loggedIn" class="btn primary job-action-cell job-action-link" to="/me">
              我的收藏
            </router-link>
          </div>
          <RagSyncThreeMinuteProgress
            :running="ragSyncRunning"
            :elapsed-ms="ragSyncElapsedMs"
            :fill-pct="ragSyncFillPct"
            :fill-pct-rounded="ragSyncFillPctRounded"
            :fill-color-class="ragSyncFillColorClass"
            :progress-label="ragSyncProgressLabel"
            :over-scale="ragSyncOverScale"
            :job-name="currentSyncJobName"
            title="知识库同步进度"
          />
          <p v-if="syncMessage" class="job-action-msg job-action-msg--ok">{{ syncMessage }}</p>
          <p v-if="loggedIn" class="job-action-hint muted">
            {{ jobFavorited ? "该岗位已在你的收藏中。" : "收藏后可在「我的收藏」中集中查看。" }}
          </p>
          <p v-else class="job-action-hint muted">登录后可收藏岗位并撰写评价（右上角切换账号）。</p>
        </div>
        <details class="review-fold">
          <summary class="review-fold-summary">评价与口碑（点击展开）</summary>
          <div class="review-fold-body">
        <div class="review-box">
          <label>评价本岗位（1～5 星）</label>
          <select v-model.number="reviewStars" class="review-input">
            <option :value="5">5 星</option>
            <option :value="4">4 星</option>
            <option :value="3">3 星</option>
            <option :value="2">2 星</option>
            <option :value="1">1 星</option>
          </select>
          <textarea v-model="reviewComment" class="review-input" rows="3" placeholder="可选：写几句评价" />
          <label class="tag-label">标签（可选，来自 config/review_tags.json）</label>
          <div class="tag-chips">
            <label v-for="t in jobTagDefs" :key="t.id" class="chip-label">
              <input v-model="selectedTagIds" type="checkbox" :value="t.id" />
              {{ t.label || t.id }}
            </label>
          </div>
          <div class="btn-row tight">
            <button type="button" class="btn primary" :disabled="!loggedIn" @click="submitJobReview">
              提交 / 更新评价
            </button>
            <button
              v-if="hasMyReview"
              type="button"
              class="btn danger"
              :disabled="!loggedIn"
              @click="deleteJobReview"
            >
              删除我的评价
            </button>
          </div>
          <p class="muted">{{ reviewHint }}</p>
        </div>
        <h3 class="section-title">大家怎么说</h3>
        <p class="muted">{{ aggJobText }}</p>
        <ul class="list">
          <li v-for="(it, i) in publicReviews?.items || []" :key="`${it.student_id}-${i}`">
            <strong>{{ it.student_id }}</strong>
            · {{ "★".repeat(it.stars) }}{{ "☆".repeat(5 - it.stars) }}
            <div class="rev-comment">{{ it.comment || "（无评语）" }}</div>
            <div v-if="it.tags?.length" class="rev-tags">
              标签：{{ it.tags.map((id) => jobTagLabelMap[id] || id).join("、") }}
            </div>
          </li>
        </ul>
          </div>
        </details>
        <details v-if="gjzGroups.length" class="info-fold">
          <summary class="info-fold-summary">
            <span class="info-fold-title">关键字</span>
            <span class="info-fold-hint muted">{{ gjzPreview(gjzGroups) }}</span>
          </summary>
          <div class="info-fold-body gjz-section">
            <div v-for="group in gjzGroups" :key="group.groupName" class="gjz-group">
              <div class="gjz-group-title">{{ group.groupName }}</div>
              <div class="gjz-chips">
                <span v-for="kw in group.keywords" :key="`${group.groupName}-${kw}`" class="gjz-chip">{{ kw }}</span>
              </div>
            </div>
          </div>
        </details>
        <details v-for="section in detailSections" :key="section.title" class="info-fold">
          <summary class="info-fold-summary">
            <span class="info-fold-title">{{ section.title }}</span>
            <span class="info-fold-hint muted">{{ sectionPreview(section.fields) }}</span>
          </summary>
          <div class="info-fold-body">
            <div class="kv">
              <template v-for="field in section.fields" :key="`${section.title}-${field.label}`">
                <div class="k">{{ field.label }}</div>
                <div v-if="field.kind === 'nlqx'" class="v nlqx-v">
                  <template v-if="nlqxItems.length">
                    <div class="nlqx-chips">
                      <button
                        v-for="item in nlqxItems"
                        :key="item.code"
                        type="button"
                        class="nlqx-chip"
                        :class="{ 'nlqx-chip--active': activeNlqxCode === item.code }"
                        :aria-expanded="activeNlqxCode === item.code"
                        @click="toggleNlqx(item.code)"
                      >
                        {{ item.label }}
                      </button>
                    </div>
                    <div v-if="activeNlqxItem" class="nlqx-detail">
                      <div class="nlqx-detail-title">{{ activeNlqxItem.label }}</div>
                      <p class="nlqx-detail-body">{{ activeNlqxItem.detail }}</p>
                    </div>
                    <p v-else class="nlqx-hint muted">点击能力类型查看详情</p>
                  </template>
                  <template v-else>{{ fmt(job?.nlqxText) }}</template>
                </div>
                <div v-else class="v">{{ field.value || "-" }}</div>
              </template>
            </div>
          </div>
        </details>
        <details class="info-fold">
          <summary class="info-fold-summary">
            <span class="info-fold-title">职位描述</span>
            <span class="info-fold-hint muted">{{ jobDescriptionHtml ? "点击展开查看" : "暂无职位描述" }}</span>
          </summary>
          <div class="info-fold-body">
            <div
              v-if="jobDescriptionHtml"
              class="rich-text-block"
              v-html="jobDescriptionHtml"
            />
            <p v-else class="muted">暂无职位描述</p>
          </div>
        </details>

        <details class="info-fold">
          <summary class="info-fold-summary">
            <span class="info-fold-title">同企业其他岗位</span>
            <span class="info-fold-hint muted">{{ normalizedRelated.length ? `${normalizedRelated.length} 个` : "暂无" }}</span>
          </summary>
          <div class="info-fold-body">
            <div class="job-list-scroll">
              <ul class="list">
                <li v-if="!normalizedRelated.length">暂无同企业其他岗位</li>
                <li v-for="item in normalizedRelated" :key="item.job_id">
                  <router-link :to="`/jobs/${encodeURIComponent(item.job_id)}`">{{ item.job_title || "-" }}</router-link>
                  <div class="post-meta">行业：{{ item.district || "-" }}</div>
                  <div class="post-meta">薪资：{{ item.salary_range_month || "-" }}</div>
                  <div class="post-meta">地址：{{ item.city || "-" }}</div>
                </li>
              </ul>
            </div>
          </div>
        </details>
        <details v-if="ragSyncPreviewJson" class="info-fold rag-debug-fold">
          <summary class="info-fold-summary">
            <span class="info-fold-title">数据预览（字典翻译 + RAG）</span>
            <span class="info-fold-hint muted">{{ ragPreviewHint }} · 点击展开</span>
          </summary>
          <div class="info-fold-body">
            <p class="rag-debug-tip muted">
              「展示数据」含岗位、用人单位各字段的中文翻译、关键字分组、能力需求详情及职位描述纯文本；
              「markdown」为同步知识库时写入的正文。
            </p>
            <pre class="rag-debug-pre">{{ ragSyncPreviewJson }}</pre>
          </div>
        </details>
        <p class="error">{{ error }}</p>
      </main>
    </div>
  </div>
</template>

<style scoped>
.hero {
  max-width: 1100px;
  margin: 0 auto;
  padding: 42px 20px 16px;
}
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: #e0e7ff;
  color: var(--primary-color);
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 10px;
}
.hero h1 {
  font-size: clamp(1.9rem, 4.4vw, 2.8rem);
  margin-bottom: 8px;
}
.hero p {
  color: var(--text-muted);
  font-size: 0.95rem;
}
.hero-tip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 10px;
}
.tip-chip {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid transparent;
}
.tip-chip--warn {
  background: #fffbeb;
  color: #b45309;
  border-color: #fcd34d;
}
.tip-chip--muted {
  background: #f1f5f9;
  color: #475569;
  border-color: #cbd5e1;
}
.tip-chip--ok {
  background: #ecfdf5;
  color: #047857;
  border-color: #6ee7b7;
}
.review-fold {
  margin-top: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 0 12px 12px;
  background: #fafafa;
}
.review-fold-summary {
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--primary-color);
  padding: 12px 0 10px;
  list-style: none;
}
.review-fold-summary::-webkit-details-marker {
  display: none;
}
.review-fold-body {
  padding-top: 4px;
}
.info-fold {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 0 12px 12px;
  background: #fafafa;
}
.info-fold-summary {
  cursor: pointer;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px 12px;
  padding: 12px 0 10px;
  list-style: none;
  user-select: none;
}
.info-fold-summary::-webkit-details-marker {
  display: none;
}
.info-fold-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--primary-color);
}
.info-fold-title::before {
  content: "▸ ";
  display: inline-block;
  transition: transform 0.15s ease;
  color: #94a3b8;
}
.info-fold[open] .info-fold-title::before {
  transform: rotate(90deg);
}
.info-fold-hint {
  font-size: 0.82rem;
  font-weight: 400;
  text-align: right;
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.info-fold-body {
  padding-top: 2px;
  border-top: 1px solid #eceff3;
}
.layout {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px 70px;
}
.kv {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 8px 12px;
  font-size: 0.92rem;
}
.k {
  color: var(--text-muted);
}
.v a {
  color: var(--primary-color);
  text-decoration: none;
}
.job-action-bar {
  margin-top: 16px;
  padding: 14px 16px;
  border: 1px solid #e8ecf4;
  border-radius: 14px;
  background: linear-gradient(165deg, #fafbff 0%, #ffffff 55%);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset;
}
.job-action-bar__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 160px), 1fr));
  gap: 10px;
  align-items: stretch;
}
.job-action-cell {
  min-height: 42px;
  width: 100%;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 0.88rem;
  white-space: nowrap;
}
.job-action-link {
  text-decoration: none;
}
.job-action-msg {
  margin: 10px 0 0;
  font-size: 0.86rem;
}
.job-action-msg--ok {
  color: #166534;
  font-weight: 600;
}
.btn.danger {
  background: #fef2f2;
  color: #b91c1c;
  border-color: #fecaca;
}
.btn.danger:hover:not(:disabled) {
  background: #fee2e2;
}
.job-action-hint {
  margin: 10px 0 0;
  font-size: 0.82rem;
  line-height: 1.45;
}
@media (max-width: 640px) {
  .job-action-bar__grid {
    grid-template-columns: 1fr;
  }
  .job-action-cell {
    white-space: normal;
  }
}
.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 14px 0;
  align-items: center;
}
.btn-row.tight {
  margin-top: 0;
}
.muted {
  color: var(--text-muted);
  font-size: 0.88rem;
}
.review-box {
  margin-top: 12px;
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px;
}
.review-box label {
  font-size: 0.85rem;
  color: var(--text-muted);
  display: block;
  margin-bottom: 6px;
}
.tag-label {
  margin-top: 8px;
}
.review-input {
  width: 100%;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  padding: 8px;
  font-size: 0.9rem;
  margin-bottom: 8px;
}
.tag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin: 8px 0 12px;
}
.chip-label {
  font-size: 0.85rem;
  cursor: pointer;
  user-select: none;
}
.rev-comment {
  margin-top: 6px;
  color: #6b7280;
  font-size: 0.88rem;
  white-space: pre-wrap;
}
.rev-tags {
  margin-top: 6px;
  font-size: 0.82rem;
  color: #4b5563;
}
.section-title {
  margin: 18px 0 10px;
  font-size: 1.05rem;
}
.gjz-section {
  padding-top: 10px;
  background: transparent;
  border: none;
}
.gjz-group + .gjz-group {
  margin-top: 12px;
}
.gjz-group-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}
.gjz-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.gjz-chip {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.84rem;
  line-height: 1.4;
}
.nlqx-v {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.nlqx-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.nlqx-chip {
  border: 1px solid #c7d2fe;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.84rem;
  line-height: 1.4;
  padding: 4px 12px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.nlqx-chip:hover {
  background: #e0e7ff;
  border-color: #a5b4fc;
}
.nlqx-chip--active {
  background: #4338ca;
  border-color: #4338ca;
  color: #fff;
  box-shadow: 0 0 0 2px rgba(67, 56, 202, 0.18);
}
.nlqx-detail {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}
.nlqx-detail-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
}
.nlqx-detail-body {
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.6;
  color: #4b5563;
  white-space: pre-wrap;
  word-break: break-word;
}
.nlqx-hint {
  margin: 0;
  font-size: 0.82rem;
}
.rag-debug-tip {
  margin: 0 0 10px;
  font-size: 0.82rem;
}
.rag-debug-pre {
  margin: 0;
  border-radius: 10px;
  background: #0f172a;
  color: #f8fafc;
  padding: 12px;
  max-height: 48vh;
  overflow: auto;
  font-size: 0.78rem;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}
.rich-text-block {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  background: #ffffff;
  color: #1f2937;
  font-size: 0.92rem;
  line-height: 1.8;
  letter-spacing: 0.01em;
  word-break: break-word;
  max-height: 360px;
  overflow: auto;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.rich-text-block :deep(p) {
  margin: 0 0 0.75em;
}
.rich-text-block :deep(ul),
.rich-text-block :deep(ol) {
  margin: 0 0 0.75em;
  padding-left: 1.25em;
}
.rich-text-block :deep(img) {
  max-width: 100%;
  height: auto;
}
.list {
  list-style: none;
  display: grid;
  gap: 10px;
  padding: 0;
}
.list li {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 10px;
}
.list a {
  text-decoration: none;
  color: var(--primary-color);
  font-weight: 600;
}
.job-list-scroll {
  max-height: 46vh;
  overflow: auto;
  padding-right: 4px;
}
.post-meta {
  font-size: 0.86rem;
  color: var(--text-muted);
  margin-top: 4px;
}
.error {
  color: var(--danger);
  margin-top: 8px;
  min-height: 20px;
  font-size: 0.9rem;
  font-weight: 600;
}
@media (max-width: 900px) {
  .kv {
    grid-template-columns: 1fr;
  }
  .job-list-scroll {
    max-height: 38vh;
  }
}
</style>
