<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiDelete, apiGet, apiPost, getStudentId } from "../api/client";

const route = useRoute();
const job = ref(null);
const related = ref([]);
const error = ref("");
const syncLoading = ref(false);
const syncMessage = ref("");

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
      credit_code: job.value.companyId
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
      credit_code: item.companyId
    }
  }))
);

const companyLink = computed(() => {
  const code = normalizedJob.value?.company_relation?.credit_code || "";
  return code ? `/companies/${encodeURIComponent(code)}` : "/companies";
});

const kvRows = computed(() => {
  const data = normalizedJob.value;
  if (!data) return [];
  return [["所属企业", data.company_relation?.company_name || "-"]];
});

const detailSections = computed(() => {
  const j = job.value || {};
  const synRagStatus =
    j.synRag === "1" || j.synRag === 1
      ? "已同步"
      : j.synRag === "0" || j.synRag === 0
        ? "未同步"
        : j.synRag;
  return [
    {
      title: "企业与地点",
      fields: [
        { label: "公司全称", value: j.companyName },
        { label: "公司性质", value: j.companyType },
        { label: "所在地址", value: j.address },
        { label: "所属行业", value: j.industry },
        { label: "涉及领域", value: j.area }
      ]
    },
    {
      title: "岗位基础信息",
      fields: [
        { label: "岗位全称", value: j.jobName },
        { label: "招聘标题", value: j.postingTitle },
        { label: "岗位性质", value: j.jobType },
        { label: "招聘数量", value: j.vacancies }
      ]
    },
    {
      title: "任职要求与薪资",
      fields: [
        { label: "学历要求", value: j.education },
        { label: "薪资范围", value: j.salaryRange },
        { label: "专业限制", value: j.majorReq }
      ]
    },
    {
      title: "来源与时间",
      fields: [
        { label: "信息来源", value: j.source },
        { label: "发布时间", value: j.publishTime },
        { label: "创建时间", value: j.createTime },
        { label: "synRag", value: synRagStatus },
        { label: "ragMdPath", value: j.ragMdPath }
      ]
    }
  ];
});

const jobId = computed(() => String(route.params.job_id || "").trim());
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

async function loadJobDetail() {
  try {
    error.value = "";
    reviewHint.value = "";
    const jid = jobId.value;
    const [one, all] = await Promise.all([
      apiGet(`/api/jobs/${encodeURIComponent(jid)}`),
      apiGet("/api/jobs")
    ]);
    job.value = one;
    related.value = (all || []).filter((x) => x.id !== one.id && x.companyId === one.companyId).slice(0, 8);

    await loadJobTagCatalog();
    if (getStudentId()) await refreshJobContext();
    else {
      ctx.value = null;
      reviewStars.value = 5;
      reviewComment.value = "";
      selectedTagIds.value = [];
    }
    await loadPublicJobReviews();
  } catch (err) {
    error.value = err.message || "加载失败";
    job.value = null;
  }
}

async function syncToKnowledgeBase() {
  if (!job.value?.id || syncLoading.value) return;
  syncLoading.value = true;
  syncMessage.value = "";
  error.value = "";
  try {
    const resp = await apiPost(`/api/jobs/${encodeURIComponent(job.value.id)}/sync-rag`, {});
    if (job.value) {
      job.value.synRag = "1";
      job.value.ragMdPath = resp?.ragMdPath || job.value.ragMdPath;
    }
    syncMessage.value = resp?.message || "同步成功";
  } catch (err) {
    error.value = err.message || "同步失败";
  } finally {
    syncLoading.value = false;
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
      <span class="badge">Job Detail</span>
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
              :disabled="syncLoading || !job"
              @click="syncToKnowledgeBase"
            >
              {{ syncButtonLabel }}
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
        <div v-for="section in detailSections" :key="section.title" class="detail-section">
          <h3 class="section-title">{{ section.title }}</h3>
          <div class="kv">
            <template v-for="field in section.fields" :key="`${section.title}-${field.label}`">
              <div class="k">{{ field.label }}</div>
              <div class="v">{{ field.value || "-" }}</div>
            </template>
          </div>
        </div>
        <details class="detail-box">
          <summary>展开招聘正文（content）</summary>
          <div class="detail-box-body">
            <div class="rich-text-block">{{ job?.content || "-" }}</div>
          </div>
        </details>

        <h3 class="section-title">同企业其他岗位</h3>
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
        <p class="error">{{ error }}</p>
        <pre>{{ normalizedJob ? JSON.stringify(normalizedJob, null, 2) : "" }}</pre>
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
.detail-section {
  margin-top: 14px;
}
.detail-box {
  margin-top: 10px;
  border: 1px solid #eceff3;
  border-radius: 12px;
  background: #fff;
  padding: 8px 10px;
}
.detail-box summary {
  cursor: pointer;
  color: var(--primary-color);
  font-size: 0.9rem;
  font-weight: 600;
}
.detail-box-body {
  margin-top: 10px;
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
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 360px;
  overflow: auto;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
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
pre {
  margin-top: 12px;
  border-radius: 10px;
  background: #0f172a;
  color: #f8fafc;
  padding: 12px;
  max-height: 36vh;
  overflow: auto;
  font-size: 0.78rem;
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
