<script setup>
import { onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiGet, getStudentId } from "../api/client";
import InterviewRecordCard from "../components/interview/InterviewRecordCard.vue";
import { fetchInterviewRecords } from "../modules/interview/api";

const route = useRoute();

const activeTab = ref("overview");
const sidLabel = ref("-");
const guest = ref(false);
const loadError = ref("");
const summary = ref(null);
const favorites = ref({ jobs: [] });
const follows = ref({ companies: [] });
const jobReviews = ref({ items: [] });
const companyReviews = ref({ items: [] });
const tagMaps = ref({ job: {}, company: {} });
/** 我的面试记录（V2 student_interview_records） */
const interviewRecords = ref({ items: [] });

const tabs = [
  { id: "overview", label: "概览" },
  { id: "interviews", label: "面试记录" },
  { id: "fav", label: "我的收藏" },
  { id: "fol", label: "我的关注" },
  { id: "revj", label: "岗位评价" },
  { id: "revc", label: "企业评价" }
];

function starsStr(n) {
  const s = Math.max(1, Math.min(5, Number(n) || 0));
  return "★".repeat(s) + "☆".repeat(5 - s);
}

function formatTagLine(ids, map) {
  if (!ids?.length) return "";
  const labels = ids.map((id) => map[id] || id);
  return `标签：${labels.join("、")}`;
}

async function onInterviewRecordDeleted(recordId) {
  interviewRecords.value = {
    ...interviewRecords.value,
    items: (interviewRecords.value.items || []).filter((r) => r.record_id !== recordId)
  };
}

async function loadAll() {
  const sid = getStudentId();
  sidLabel.value = sid || "未登录";
  guest.value = !sid;
  loadError.value = "";
  summary.value = null;
  if (!sid) {
    favorites.value = { jobs: [] };
    follows.value = { companies: [] };
    jobReviews.value = { items: [] };
    companyReviews.value = { items: [] };
    interviewRecords.value = { items: [] };
    return;
  }
  const q = new URLSearchParams({ student_id: sid });
  try {
    const [sum, fav, fol, rj, rc, tagsResp, irec] = await Promise.all([
      apiGet(`/api/me/summary?${q}`),
      apiGet(`/api/me/favorites?${q}`),
      apiGet(`/api/me/follows?${q}`),
      apiGet(`/api/me/reviews/jobs?${q}`),
      apiGet(`/api/me/reviews/companies?${q}`),
      apiGet("/api/review-tags"),
      fetchInterviewRecords(sid)
    ]);
    summary.value = sum;
    favorites.value = fav;
    follows.value = fol;
    jobReviews.value = rj;
    companyReviews.value = rc;
    interviewRecords.value = irec;
    const job = {};
    const company = {};
    (tagsResp.job_review_tags || []).forEach((t) => {
      if (t?.id) job[t.id] = t.label || t.id;
    });
    (tagsResp.company_review_tags || []).forEach((t) => {
      if (t?.id) company[t.id] = t.label || t.id;
    });
    tagMaps.value = { job, company };
  } catch (e) {
    loadError.value = e.message || "加载失败";
  }
}

function applyTabFromRoute() {
  const t = route.query.tab;
  if (typeof t === "string" && tabs.some((x) => x.id === t)) {
    activeTab.value = t;
  }
}

onMounted(() => {
  applyTabFromRoute();
  loadAll();
});

watch(() => route.query.tab, applyTabFromRoute);
</script>

<template>
  <div>
    <section class="hero">
      <h1>我的</h1>
      <p>学号：<code>{{ sidLabel }}</code></p>
      <p v-if="guest" class="warn">
        未检测到登录学号，请先在
        <router-link to="/login">登录页</router-link>
        登录。
      </p>
    </section>
    <div class="container">
      <div class="tabs">
        <button
          v-for="t in tabs"
          :key="t.id"
          type="button"
          class="tab"
          :class="{ active: activeTab === t.id }"
          @click="activeTab = t.id"
        >
          {{ t.label }}
        </button>
      </div>
      <p v-if="loadError" class="error">{{ loadError }}</p>
      <div v-show="activeTab === 'overview'" class="panel">
        <div v-if="summary" class="stat-grid">
          <div class="stat"><span>收藏岗位</span><strong>{{ summary.favorite_job_count }}</strong></div>
          <div class="stat"><span>关注企业</span><strong>{{ summary.followed_company_count }}</strong></div>
          <div class="stat"><span>岗位评价</span><strong>{{ summary.job_review_count }}</strong></div>
          <div class="stat"><span>企业评价</span><strong>{{ summary.company_review_count }}</strong></div>
        </div>
        <p v-else-if="!guest && !loadError" class="muted">加载中…</p>
        <p class="muted hint">在岗位列表、岗位详情可收藏岗位；在企业列表、企业详情可关注企业并提交评价。</p>
      </div>
      <div v-show="activeTab === 'interviews'" class="panel">
        <p class="muted hint">模拟面试确认大纲后，记录会出现在此处。也可从<router-link to="/interview/plans">面试大纲</router-link>查看题库。</p>
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(interviewRecords.items || []).length" class="empty">暂无面试记录</li>
          <InterviewRecordCard
            v-for="r in interviewRecords.items || []"
            v-else
            :key="r.record_id"
            :item="r"
            :student-id="getStudentId()"
            @deleted="onInterviewRecordDeleted"
          />
        </ul>
      </div>
      <div v-show="activeTab === 'fav'" class="panel">
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(favorites.jobs || []).length" class="empty">暂无收藏</li>
          <li v-for="j in favorites.jobs || []" v-else :key="j.job_id" class="card-li">
            <router-link :to="`/jobs/${encodeURIComponent(j.job_id)}`">{{ j.job_title || j.job_id }}</router-link>
            <p class="muted">
              {{ j.city || "" }} {{ j.district || "" }} ｜ {{ j.company_relation?.company_name || "" }}
            </p>
          </li>
        </ul>
      </div>
      <div v-show="activeTab === 'fol'" class="panel">
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(follows.companies || []).length" class="empty">暂无关注</li>
          <li v-for="c in follows.companies || []" v-else :key="c.credit_code" class="card-li">
            <router-link :to="`/companies/${encodeURIComponent(c.credit_code)}`">{{
              c.company_name || c.credit_code
            }}</router-link>
            <p class="muted">{{ c.industry || "" }}</p>
          </li>
        </ul>
      </div>
      <div v-show="activeTab === 'revj'" class="panel">
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(jobReviews.items || []).length" class="empty">暂无岗位评价</li>
          <li v-for="x in jobReviews.items || []" v-else :key="x.job_id" class="card-li">
            <router-link :to="`/jobs/${encodeURIComponent(x.job_id)}`">{{
              (x.job && x.job.job_title) || x.job_id
            }}</router-link>
            <p class="stars">{{ starsStr(x.review?.stars) }}</p>
            <p>{{ (x.review?.comment || "").slice(0, 200) || "（无文字）" }}</p>
            <p v-if="x.review?.tags?.length" class="tag-line">{{ formatTagLine(x.review.tags, tagMaps.job) }}</p>
          </li>
        </ul>
      </div>
      <div v-show="activeTab === 'revc'" class="panel">
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(companyReviews.items || []).length" class="empty">暂无企业评价</li>
          <li v-for="x in companyReviews.items || []" v-else :key="x.credit_code" class="card-li">
            <router-link :to="`/companies/${encodeURIComponent(x.credit_code)}`">{{
              (x.company && x.company.company_name) || x.credit_code
            }}</router-link>
            <p class="stars">{{ starsStr(x.review?.stars) }}</p>
            <p>{{ (x.review?.comment || "").slice(0, 200) || "（无文字）" }}</p>
            <p v-if="x.review?.tags?.length" class="tag-line">{{ formatTagLine(x.review.tags, tagMaps.company) }}</p>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hero {
  padding: 88px 20px 36px;
  text-align: center;
  background: radial-gradient(circle at top right, #eef2ff, transparent),
    radial-gradient(circle at top left, #f5f3ff, transparent);
}
.hero h1 {
  font-size: clamp(1.75rem, 4vw, 2.2rem);
  margin-bottom: 8px;
}
.hero p {
  color: var(--text-muted, #6b7280);
  font-size: 0.95rem;
}
.warn {
  color: var(--danger, #dc2626);
  font-weight: 600;
  margin-top: 10px;
}
.warn a {
  color: var(--primary-color, #6366f1);
}
.container {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 18px 80px;
}
.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.tab {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 0.88rem;
  cursor: pointer;
  color: #374151;
}
.tab.active {
  border-color: var(--primary-color, #6366f1);
  color: var(--primary-color, #6366f1);
  font-weight: 600;
  background: #eef2ff;
}
.panel {
  background: #fff;
  border: 1px solid rgba(31, 41, 55, 0.08);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.stat {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px;
  text-align: center;
}
.stat strong {
  display: block;
  font-size: 1.35rem;
  margin-top: 4px;
  color: var(--primary-color, #6366f1);
}
.stat span {
  font-size: 0.8rem;
  color: var(--text-muted, #6b7280);
}
.cards {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}
.card-li {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px;
}
.card-li a {
  color: var(--primary-color, #6366f1);
  font-weight: 600;
  text-decoration: none;
}
.muted {
  color: var(--text-muted, #6b7280);
  font-size: 0.85rem;
  margin-top: 6px;
}
.hint {
  font-size: 0.9rem;
  margin-top: 12px;
}
.stars {
  color: #f59e0b;
  letter-spacing: 1px;
  margin-top: 4px;
}
.tag-line {
  font-size: 0.82rem;
  color: #4b5563;
  margin-top: 4px;
}
.empty {
  color: var(--text-muted, #6b7280);
  padding: 20px;
  text-align: center;
}
.error {
  color: var(--danger, #dc2626);
  font-weight: 600;
  margin-bottom: 12px;
}
</style>
