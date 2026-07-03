<script setup>
/**
 * 个人中心 — 收藏 / 关注 / 评价 / 投递 / 面试记录，使用首页侧栏壳层。
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, getStudentId } from "../api/client";
import { setStudentServerAvatar } from "../composables/useStudentAvatar";
import { uploadStudentAvatar } from "../composables/useStudentProfile";
import HomeTopBar from "../components/home/HomeTopBar.vue";
import StudentAvatar from "../components/home/StudentAvatar.vue";
import InterviewRecordCard from "../components/interview/InterviewRecordCard.vue";
import { maskName, maskStudentField } from "../utils/studentDesensitize";
import { fetchInterviewRecords } from "../modules/interview/api";
import { fetchMyApplications } from "../modules/applications/api";
import { embedUrl } from "../utils/embedFrame";

const route = useRoute();
const router = useRouter();

const activeTab = ref("overview");
const studentName = ref("");
const avatarUrl = ref("");
const guest = ref(false);
const loadError = ref("");
const summary = ref(null);
const favorites = ref({ jobs: [] });
const follows = ref({ companies: [] });
const jobReviews = ref({ items: [] });
const companyReviews = ref({ items: [] });
const tagMaps = ref({ job: {}, company: {} });
const interviewRecords = ref({ items: [] });
const applications = ref({ items: [], jobs: [] });

const tabs = [
  { id: "overview", label: "概览" },
  { id: "applications", label: "我的投递" },
  { id: "interviews", label: "面试记录" },
  { id: "fav", label: "我的收藏" },
  { id: "fol", label: "我的关注" },
  { id: "revj", label: "岗位评价" },
  { id: "revc", label: "企业评价" }
];

const studentId = computed(() => getStudentId());
const accountSubtitle = computed(() => {
  if (guest.value) return "登录后查看收藏、关注与个人数据";
  const sid = maskStudentField("学号", studentId.value);
  return `学号 ${sid || "—"}`;
});
const displayStudentName = computed(() => maskName(studentName.value) || "同学");

function starsStr(n) {
  const s = Math.max(1, Math.min(5, Number(n) || 0));
  return "★".repeat(s) + "☆".repeat(5 - s);
}

function formatAppliedAt(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 16);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function jobDetailTo(jobId) {
  return embedUrl(`/jobs/${encodeURIComponent(jobId)}`);
}

function companyDetailTo(creditCode) {
  return embedUrl(`/companies/${encodeURIComponent(creditCode)}`);
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

async function loadStudentName(sid) {
  try {
    const data = await apiGet(`/api/students/${encodeURIComponent(sid)}`);
    studentName.value = data?.["学生基本信息"]?.["姓名"] || "";
    avatarUrl.value = data?.["学生基本信息"]?.["头像"] || "";
    setStudentServerAvatar(avatarUrl.value, sid);
  } catch {
    studentName.value = "";
    avatarUrl.value = "";
  }
}

async function avatarUploadHandler(file) {
  const url = await uploadStudentAvatar(file, studentId.value);
  avatarUrl.value = url;
  return url;
}

async function loadAll() {
  const sid = studentId.value;
  guest.value = !sid;
  loadError.value = "";
  summary.value = null;
  studentName.value = "";
  if (!sid) {
    favorites.value = { jobs: [] };
    follows.value = { companies: [] };
    jobReviews.value = { items: [] };
    companyReviews.value = { items: [] };
    interviewRecords.value = { items: [] };
    applications.value = { items: [], jobs: [] };
    return;
  }
  const q = new URLSearchParams({ student_id: sid });
  try {
    const [sum, fav, fol, rj, rc, tagsResp, irec, apps] = await Promise.all([
      apiGet(`/api/me/summary?${q}`),
      apiGet(`/api/me/favorites?${q}`),
      apiGet(`/api/me/follows?${q}`),
      apiGet(`/api/me/reviews/jobs?${q}`),
      apiGet(`/api/me/reviews/companies?${q}`),
      apiGet("/api/review-tags"),
      fetchInterviewRecords(sid, { fresh: true }),
      fetchMyApplications(sid),
      loadStudentName(sid)
    ]);
    summary.value = sum;
    favorites.value = fav;
    follows.value = fol;
    jobReviews.value = rj;
    companyReviews.value = rc;
    interviewRecords.value = irec;
    applications.value = apps || { items: [], jobs: [] };
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
    return;
  }
  activeTab.value = "overview";
}

function selectTab(id) {
  activeTab.value = id;
  const query = id === "overview" ? {} : { tab: id };
  router.replace({ path: "/me", query });
}

onMounted(() => {
  applyTabFromRoute();
  loadAll();
});

watch(() => route.query.tab, applyTabFromRoute);
</script>

<template>
  <div class="home-main me-main">
      <HomeTopBar
        title="个人中心"
        subtitle="管理收藏、关注、投递、评价与面试记录"
        :student-name="displayStudentName"
      />

      <section class="account-card">
        <div class="account-profile">
          <StudentAvatar
            :name="studentName"
            :student-id="studentId"
            :image-url="avatarUrl"
            size="xl"
            editable
            :upload-handler="avatarUploadHandler"
            title="点击修改头像"
          />
          <div class="account-meta">
            <strong>{{ guest ? "未登录" : displayStudentName || "同学" }}</strong>
            <span>{{ accountSubtitle }}</span>
          </div>
        </div>
        <div v-if="guest" class="account-actions">
          <router-link to="/login" class="account-btn account-btn--primary">前往登录</router-link>
        </div>
        <div v-else class="account-actions">
          <button type="button" class="account-btn account-btn--ghost" @click="selectTab('overview')">数据概览</button>
        </div>
      </section>

      <div class="me-tabs" role="tablist" aria-label="个人中心分类">
        <button
          v-for="t in tabs"
          :key="t.id"
          type="button"
          role="tab"
          class="me-tab"
          :class="{ active: activeTab === t.id }"
          :aria-selected="activeTab === t.id"
          @click="selectTab(t.id)"
        >
          {{ t.label }}
        </button>
      </div>

      <p v-if="loadError" class="me-error">{{ loadError }}</p>

      <div v-show="activeTab === 'overview'" class="me-panel">
        <div v-if="summary" class="stat-grid">
          <div class="stat">
            <span>投递岗位</span>
            <strong>{{ summary.application_count ?? 0 }}</strong>
          </div>
          <div class="stat">
            <span>收藏岗位</span>
            <strong>{{ summary.favorite_job_count }}</strong>
          </div>
          <div class="stat">
            <span>关注企业</span>
            <strong>{{ summary.followed_company_count }}</strong>
          </div>
          <div class="stat">
            <span>岗位评价</span>
            <strong>{{ summary.job_review_count }}</strong>
          </div>
          <div class="stat">
            <span>企业评价</span>
            <strong>{{ summary.company_review_count }}</strong>
          </div>
        </div>
        <p v-else-if="guest" class="empty">请先登录</p>
        <p v-else-if="!loadError" class="muted">加载中…</p>
        <p class="muted hint">在岗位列表、岗位详情可一键投递；收藏岗位与关注企业请在对应详情页操作。</p>
      </div>

      <div v-show="activeTab === 'applications'" class="me-panel">
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(applications.items || []).length" class="empty">暂无投递记录</li>
          <li v-for="item in applications.items || []" v-else :key="item.job_id" class="card-li">
            <router-link :to="jobDetailTo(item.job_id)">{{
              item.job?.job_title || item.job_id
            }}</router-link>
            <p class="muted">
              {{ item.job?.city || "" }}
              {{ item.job?.company_relation?.company_name ? `｜ ${item.job.company_relation.company_name}` : "" }}
            </p>
            <p class="muted small">投递时间：{{ formatAppliedAt(item.applied_at) }}</p>
          </li>
        </ul>
      </div>

      <div v-show="activeTab === 'interviews'" class="me-panel">
        <p class="muted hint">
          面试记录已整合至
          <router-link to="/interview/center">面试中心</router-link>，可查看待面试与历史回放。
        </p>
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(interviewRecords.items || []).length" class="empty">
            暂无面试记录 ·
            <router-link to="/interview/center">前往面试中心</router-link>
          </li>
          <InterviewRecordCard
            v-for="r in (interviewRecords.items || []).slice(0, 3)"
            v-else
            :key="r.record_id"
            :item="r"
            :student-id="getStudentId()"
            @deleted="onInterviewRecordDeleted"
          />
        </ul>
        <p v-if="!guest && (interviewRecords.items || []).length > 3" class="muted hint">
          <router-link to="/interview/center">查看全部 {{ interviewRecords.items.length }} 条记录 →</router-link>
        </p>
      </div>

      <div v-show="activeTab === 'fav'" class="me-panel">
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(favorites.jobs || []).length" class="empty">暂无收藏</li>
          <li v-for="j in favorites.jobs || []" v-else :key="j.job_id" class="card-li">
            <router-link :to="jobDetailTo(j.job_id)">{{ j.job_title || j.job_id }}</router-link>
            <p class="muted">
              {{ j.city || "" }} {{ j.district || "" }} ｜ {{ j.company_relation?.company_name || "" }}
            </p>
          </li>
        </ul>
      </div>

      <div v-show="activeTab === 'fol'" class="me-panel">
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(follows.companies || []).length" class="empty">暂无关注</li>
          <li v-for="c in follows.companies || []" v-else :key="c.credit_code" class="card-li">
            <router-link :to="companyDetailTo(c.credit_code)">{{
              c.company_name || c.credit_code
            }}</router-link>
            <p class="muted">{{ c.industry || "" }}</p>
          </li>
        </ul>
      </div>

      <div v-show="activeTab === 'revj'" class="me-panel">
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(jobReviews.items || []).length" class="empty">暂无岗位评价</li>
          <li v-for="x in jobReviews.items || []" v-else :key="x.job_id" class="card-li">
            <router-link :to="jobDetailTo(x.job_id)">{{
              (x.job && x.job.job_title) || x.job_id
            }}</router-link>
            <p class="stars">{{ starsStr(x.review?.stars) }}</p>
            <p>{{ (x.review?.comment || "").slice(0, 200) || "（无文字）" }}</p>
            <p v-if="x.review?.tags?.length" class="tag-line">{{ formatTagLine(x.review.tags, tagMaps.job) }}</p>
          </li>
        </ul>
      </div>

      <div v-show="activeTab === 'revc'" class="me-panel">
        <ul class="cards">
          <li v-if="guest" class="empty">请先登录</li>
          <li v-else-if="!(companyReviews.items || []).length" class="empty">暂无企业评价</li>
          <li v-for="x in companyReviews.items || []" v-else :key="x.credit_code" class="card-li">
            <router-link :to="companyDetailTo(x.credit_code)">{{
              (x.company && x.company.company_name) || x.credit_code
            }}</router-link>
            <p class="stars">{{ starsStr(x.review?.stars) }}</p>
            <p>{{ (x.review?.comment || "").slice(0, 200) || "（无文字）" }}</p>
            <p v-if="x.review?.tags?.length" class="tag-line">{{ formatTagLine(x.review.tags, tagMaps.company) }}</p>
          </li>
        </ul>
      </div>
    </div>
</template>

<style scoped>
.me-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.account-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 18px;
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
}
.account-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.account-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(145deg, #c7d2fe, #818cf8);
  color: #312e81;
  font-size: 1.05rem;
  font-weight: 800;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.account-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.account-meta strong {
  font-size: 1rem;
  color: #0f172a;
}
.account-meta span {
  font-size: 0.78rem;
  color: #64748b;
}
.account-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.account-btn {
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  border: 1px solid transparent;
}
.account-btn--primary {
  background: linear-gradient(135deg, #5b6adf, #6366f1);
  color: #fff;
}
.account-btn--ghost {
  background: #fff;
  border-color: #c7d2fe;
  color: var(--home-primary, #5b6adf);
}
.account-btn--ghost:hover {
  background: #eef2ff;
}
.me-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.me-tab {
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 0.82rem;
  cursor: pointer;
  color: #475569;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.me-tab:hover {
  border-color: #c7d2fe;
  color: var(--home-primary, #5b6adf);
}
.me-tab.active {
  border-color: var(--home-primary, #5b6adf);
  color: var(--home-primary, #5b6adf);
  font-weight: 700;
  background: #eef2ff;
}
.me-panel {
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  border-radius: var(--home-radius-lg, 16px);
  padding: 16px 18px;
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
}
.me-error {
  color: #b91c1c;
  font-weight: 600;
  font-size: 0.88rem;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.stat {
  border: 1px solid #e8ecff;
  border-radius: 12px;
  padding: 12px;
  text-align: center;
  background: #f8faff;
}
.stat strong {
  display: block;
  font-size: 1.35rem;
  margin-top: 4px;
  color: var(--home-primary, #5b6adf);
}
.stat span {
  font-size: 0.8rem;
  color: #64748b;
}
.cards {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}
.card-li {
  border: 1px solid #e8ecff;
  border-radius: 12px;
  padding: 12px;
  background: #fafbff;
}
.card-li a {
  color: var(--home-primary, #5b6adf);
  font-weight: 600;
  text-decoration: none;
}
.card-li a:hover {
  text-decoration: underline;
}
.muted.small {
  font-size: 0.78rem;
}
.muted {
  color: #64748b;
  font-size: 0.85rem;
  margin-top: 6px;
}
.hint {
  font-size: 0.88rem;
  margin-top: 12px;
}
.hint a,
.empty a {
  color: var(--home-primary, #5b6adf);
  font-weight: 600;
  text-decoration: none;
}
.hint a:hover,
.empty a:hover {
  text-decoration: underline;
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
  color: #64748b;
  padding: 20px;
  text-align: center;
}
@media (max-width: 720px) {
  .account-card {
    flex-direction: column;
    align-items: stretch;
  }
  .account-actions {
    justify-content: flex-end;
  }
}
</style>
