<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiDelete, apiGet, apiPost, getStudentId } from "../api/client";

const route = useRoute();
const company = ref(null);
const jobs = ref([]);
const error = ref("");

const coTagDefs = ref([]);
const coTagLabelMap = computed(() => {
  const m = {};
  (coTagDefs.value || []).forEach((t) => {
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

const normalizedJobs = computed(() =>
  (jobs.value || []).map((item) => ({
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

const creditCode = computed(() => String(route.params.credit_code || "").trim());

const kvRows = computed(() => {
  const data = company.value;
  if (!data) return [];
  return [
    ["企业名称", data.companyName || "-"],
    ["行业", data.area || "-"],
    ["企业规模", data.companySize || "-"],
    ["所在地", data.address || "-"]
  ];
});

const loggedIn = computed(() => Boolean(getStudentId()));
const companyFollowed = computed(() => Boolean(ctx.value?.company_followed));
const hasMyReview = computed(() => Boolean(ctx.value?.my_company_review));

/** 已登录且本人尚未评价企业时展示「未评价」小标签 */
const showCompanyTipNoReview = computed(() => Boolean(company.value) && loggedIn.value && !hasMyReview.value);

const portraitLine = computed(() => {
  const j = publicReviews.value;
  if (!j || j.detail) return "";
  const fc = j.follower_count != null ? j.follower_count : 0;
  const dist = j.review_tag_distribution || [];
  const distStr = dist.length
    ? dist.map((x) => `${coTagLabelMap.value[x.tag_id] || x.tag_id} ${x.count} 次`).join("；")
    : "（尚无从评价汇总的标签次数，提交带标签的评价后此处会累计）";
  return `画像统计 · 关注人数：${fc}（全站学生）\n评价标签分布：${distStr}`;
});

const aggCoText = computed(() => {
  const j = publicReviews.value;
  if (!j) return "加载中…";
  if (j.detail) return j.detail;
  const fc = j.follower_count != null ? j.follower_count : 0;
  if (!j.count) return `暂时还没有评价。全站关注该企业：${fc} 人。`;
  const dist = (j.review_tag_distribution || [])
    .map((x) => `${coTagLabelMap.value[x.tag_id] || x.tag_id} ${x.count} 次`)
    .join("；");
  return (
    `共 ${j.count} 条评价，平均 ${j.avg_stars} 星 · 全站关注 ${fc} 人` + (dist ? ` · 标签分布：${dist}` : "")
  );
});

async function loadCoTagCatalog() {
  try {
    const c = await apiGet("/api/review-tags");
    coTagDefs.value = c.company_review_tags || [];
  } catch {
    coTagDefs.value = [];
  }
}

async function refreshCoContext() {
  const sid = getStudentId();
  const cc = creditCode.value;
  if (!sid || !cc) {
    ctx.value = null;
    return;
  }
  try {
    const q = new URLSearchParams({ student_id: sid, credit_code: cc });
    ctx.value = await apiGet(`/api/me/context?${q}`);
    const mr = ctx.value?.my_company_review;
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

async function loadPublicCoReviews() {
  const cc = creditCode.value;
  if (!cc) return;
  try {
    publicReviews.value = await apiGet(`/api/companies/${encodeURIComponent(cc)}/reviews`);
  } catch (e) {
    publicReviews.value = { count: 0, items: [], detail: e.message };
  }
}

async function loadCompany() {
  try {
    error.value = "";
    reviewHint.value = "";
    const cc = creditCode.value;
    const [one, allJobs] = await Promise.all([
      apiGet(`/api/companies/${encodeURIComponent(cc)}`),
      apiGet("/api/jobs")
    ]);
    company.value = one;
    jobs.value = (allJobs || []).filter((j) => j.companyId === one.id).slice(0, 12);

    await loadCoTagCatalog();
    if (getStudentId()) await refreshCoContext();
    else {
      ctx.value = null;
      reviewStars.value = 5;
      reviewComment.value = "";
      selectedTagIds.value = [];
    }
    await loadPublicCoReviews();
  } catch (err) {
    error.value = err.message || "加载失败";
    company.value = null;
  }
}

async function toggleFollow() {
  const sid = getStudentId();
  const cc = creditCode.value;
  if (!sid || !cc) {
    window.alert("请先登录");
    return;
  }
  try {
    await apiPost("/api/me/follows/toggle", { student_id: sid, credit_code: cc });
    await refreshCoContext();
    await loadPublicCoReviews();
  } catch (e) {
    window.alert(e.message || "操作失败");
  }
}

async function submitCompanyReview() {
  const sid = getStudentId();
  const cc = creditCode.value;
  if (!sid || !cc) {
    window.alert("请先登录");
    return;
  }
  try {
    await apiPost("/api/me/reviews/company", {
      student_id: sid,
      credit_code: cc,
      stars: Number(reviewStars.value),
      comment: reviewComment.value.trim(),
      tags: [...selectedTagIds.value]
    });
    reviewHint.value = "已保存评价。";
    await loadPublicCoReviews();
    await refreshCoContext();
  } catch (e) {
    window.alert(e.message || "提交失败");
  }
}

async function deleteCompanyReview() {
  const sid = getStudentId();
  const cc = creditCode.value;
  if (!sid || !cc) return;
  if (!window.confirm("确定删除你对该企业的评价？（可稍后重新提交）")) return;
  try {
    const q = new URLSearchParams({ student_id: sid, credit_code: cc });
    const j = await apiDelete(`/api/me/reviews/company?${q}`);
    reviewHint.value = j.deleted ? "已删除评价。" : "当前没有可删除的评价。";
    await refreshCoContext();
    await loadPublicCoReviews();
  } catch (e) {
    window.alert(e.message || "删除失败");
  }
}

onMounted(loadCompany);

watch(
  () => route.params.credit_code,
  (newVal, oldVal) => {
    if (newVal && newVal !== oldVal) {
      loadCompany();
    }
  }
);
</script>

<template>
  <div>
    <section class="hero">
      <span class="badge">Company Detail</span>
      <h1>{{ company?.companyName || company?.company_name || "加载中..." }}</h1>
      <p>credit_code：<code>{{ route.params.credit_code }}</code></p>
      <div v-if="showCompanyTipNoReview" class="hero-tip-row" aria-label="状态提示">
        <span class="tip-chip tip-chip--muted">未评价</span>
      </div>
      <p v-if="portraitLine" class="portrait muted">{{ portraitLine }}</p>
    </section>
    <div class="layout">
      <main class="panel">
        <div class="kv">
          <template v-for="([k, v], idx) in kvRows" :key="`${k}-${idx}`">
            <div class="k">{{ k }}</div>
            <div class="v">{{ v }}</div>
          </template>
        </div>
        <div v-if="loggedIn" class="btn-row">
          <button type="button" class="btn secondary" @click="toggleFollow">
            {{ companyFollowed ? "已关注（点击取消）" : "关注企业" }}
          </button>
          <router-link class="btn primary" to="/me">我的关注</router-link>
        </div>
        <p v-else class="muted">登录后可关注与评价企业。</p>
        <p v-if="loggedIn" class="muted fol-hint">
          {{ companyFollowed ? "该企业已在你的关注列表中。" : "关注后可在「我的」中快速回访。" }}
        </p>
        <details class="review-fold">
          <summary class="review-fold-summary">评价与口碑（点击展开）</summary>
          <div class="review-fold-body">
        <div class="review-box">
          <label>评价本企业（1～5 星）</label>
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
            <label v-for="t in coTagDefs" :key="t.id" class="chip-label">
              <input v-model="selectedTagIds" type="checkbox" :value="t.id" />
              {{ t.label || t.id }}
            </label>
          </div>
          <div class="btn-row tight">
            <button type="button" class="btn primary" :disabled="!loggedIn" @click="submitCompanyReview">
              提交 / 更新评价
            </button>
            <button
              v-if="hasMyReview"
              type="button"
              class="btn danger"
              :disabled="!loggedIn"
              @click="deleteCompanyReview"
            >
              删除我的评价
            </button>
          </div>
          <p class="muted">{{ reviewHint }}</p>
        </div>
        <h3 class="section-title">大家怎么说</h3>
        <p class="muted">{{ aggCoText }}</p>
        <ul class="list">
          <li v-for="(it, i) in publicReviews?.items || []" :key="`${it.student_id}-${i}`">
            <strong>{{ it.student_id }}</strong>
            · {{ "★".repeat(it.stars) }}{{ "☆".repeat(5 - it.stars) }}
            <div class="rev-comment">{{ it.comment || "（无评语）" }}</div>
            <div v-if="it.tags?.length" class="rev-tags">
              标签：{{ it.tags.map((id) => coTagLabelMap[id] || id).join("、") }}
            </div>
          </li>
        </ul>
          </div>
        </details>
        <h3 class="section-title">该企业发布的岗位</h3>
        <ul class="list">
          <li v-if="!normalizedJobs.length">暂无该企业岗位数据</li>
          <li v-for="item in normalizedJobs" :key="item.job_id">
            <router-link :to="`/jobs/${encodeURIComponent(item.job_id)}`">{{ item.job_title || "-" }}</router-link>
            <div class="post-meta">行业：{{ item.district || "-" }}</div>
            <div class="post-meta">薪资：{{ item.salary_range_month || "-" }}</div>
            <div class="post-meta">地址：{{ item.city || "-" }}</div>
          </li>
        </ul>
        <p class="error">{{ error }}</p>
        <pre>{{ company ? JSON.stringify(company, null, 2) : "" }}</pre>
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
.tip-chip--muted {
  background: #f1f5f9;
  color: #475569;
  border-color: #cbd5e1;
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
.portrait {
  margin-top: 10px;
  line-height: 1.6;
  white-space: pre-wrap;
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
.fol-hint {
  margin-top: 0;
  margin-bottom: 8px;
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
.section-title {
  margin: 18px 0 10px;
  font-size: 1.05rem;
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
.post-meta {
  font-size: 0.86rem;
  color: var(--text-muted);
  margin-top: 4px;
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
}
</style>
