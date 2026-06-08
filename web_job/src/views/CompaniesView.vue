<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { apiGet, apiPost, getStudentId } from "../api/client";

const companies = ref([]);
const page = ref(1);
const pageSize = 20;
const total = ref(0);
const hasMore = ref(true);
const loadingMore = ref(false);
/** 输入框：未回车时本地过滤；回车后写入 remoteKeyword 并走接口分页 */
const searchInput = ref("");
/** 最近一次回车提交给后端的检索词 */
const remoteKeyword = ref("");
const error = ref("");
const followedCodes = ref(new Set());
const sentinelRef = ref(null);
const listScrollRef = ref(null);
let observer;

const normalizedCompanies = computed(() =>
  (companies.value || []).map((item) => ({
    credit_code: item.id,
    company_name: item.companyName,
    industry: item.area,
    employee_count_range: item.companySize,
    job_count: Number(item.jobCount ?? 0)
  }))
);

const filtered = computed(() => {
  const q = searchInput.value.trim().toLowerCase();
  if (!q) return normalizedCompanies.value;
  return normalizedCompanies.value.filter((item) => {
    const text = `${item.company_name || ""} ${item.credit_code || ""} ${item.industry || ""}`.toLowerCase();
    return text.includes(q);
  });
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
  return `共 ${total.value} 家企业`;
});

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

async function loadFollows() {
  const sid = getStudentId();
  if (!sid) {
    followedCodes.value = new Set();
    return;
  }
  try {
    const f = await apiGet(`/api/me/follows?student_id=${encodeURIComponent(sid)}`);
    followedCodes.value = new Set(f.credit_codes || []);
  } catch {
    followedCodes.value = new Set();
  }
}

async function toggleFollow(creditCode, ev) {
  ev?.preventDefault();
  ev?.stopPropagation();
  const sid = getStudentId();
  if (!sid) {
    window.alert("请先登录");
    return;
  }
  if (!creditCode) return;
  try {
    const resp = await apiPost("/api/me/follows/toggle", { student_id: sid, credit_code: creditCode });
    followedCodes.value = new Set(resp.followed_companies || []);
  } catch (err) {
    window.alert(err.message || "操作失败");
  }
}

function isFollowing(code) {
  return followedCodes.value.has(code);
}

function resetPagedList() {
  companies.value = [];
  page.value = 1;
  hasMore.value = true;
  total.value = 0;
  error.value = "";
}

async function loadNextPage() {
  if (loadingMore.value || !hasMore.value) return;
  loadingMore.value = true;
  try {
    const rk = remoteKeyword.value.trim();
    const kw = rk ? `&keyword=${encodeURIComponent(rk)}` : "";
    const data = await apiGet(`/api/companies/paged?page=${page.value}&pageSize=${pageSize}${kw}`);
    const items = data?.items || [];
    companies.value.push(...items);
    total.value = Number(data?.total || 0);
    hasMore.value = Boolean(data?.hasMore);
    page.value += 1;
  } catch (err) {
    error.value = err.message;
  } finally {
    loadingMore.value = false;
  }
}

function onSearchEnter() {
  remoteKeyword.value = searchInput.value.trim();
  resetPagedList();
  void loadNextPage();
}

onMounted(async () => {
  await loadFollows();
  await loadNextPage();
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        loadNextPage();
      }
    },
    { root: listScrollRef.value, rootMargin: "200px 0px" }
  );
  if (sentinelRef.value) observer.observe(sentinelRef.value);
});

onBeforeUnmount(() => {
  if (observer) observer.disconnect();
});
</script>

<template>
  <div>
    <section class="hero">
      <h1>企业列表</h1>
      <p>企业信息与岗位供给统一查看，快速判断机会密度。</p>
    </section>
    <div class="container">
      <main class="panel">
        <div class="toolbar sticky-toolbar">
          <input
            v-model="searchInput"
            class="search"
            placeholder="企业名称 / 企业ID / 行业 — 输入即本地筛选，回车查库"
            @keydown.enter.prevent="onSearchEnter"
          />
          <div class="toolbar-meta">
            <router-link class="me-link" to="/me">我的</router-link>
            <span class="count">{{ totalText }}</span>
            <span v-if="showPageText" class="count">{{ pageText }}</span>
          </div>
        </div>
        <div ref="listScrollRef" class="list-scroll-wrap">
          <ul class="post-grid">
            <li v-if="!filtered.length && !loadingMore" class="empty">没有匹配结果</li>
            <li v-for="item in filtered" v-else :key="item.credit_code" class="post-card">
              <router-link class="post-title" :to="`/companies/${item.credit_code}`">{{
                item.company_name || "-"
              }}</router-link>
              <div class="post-meta">统一社会信用代码：{{ item.credit_code || "-" }}</div>
              <div class="post-meta">
                行业：{{ item.industry || "-" }} ｜ 规模：{{ item.employee_count_range || "-" }}
              </div>
              <div class="post-meta">关联岗位：{{ item.job_count }} 个</div>
              <div class="links-row">
                <button
                  type="button"
                  class="fol-btn"
                  :class="{ on: isFollowing(item.credit_code) }"
                  @click="toggleFollow(item.credit_code, $event)"
                >
                  {{ isFollowing(item.credit_code) ? "已关注" : "关注" }}
                </button>
                <router-link class="inline-link" :to="`/companies/${item.credit_code}`">查看企业详情</router-link>
                <router-link class="inline-link" :to="`/companies/${item.credit_code}#company-jobs`">浏览企业岗位</router-link>
              </div>
            </li>
          </ul>
          <div ref="sentinelRef" class="load-state">
            <span v-if="loadingMore">加载中...</span>
            <span v-else-if="!hasMore && companies.length">已加载全部企业</span>
          </div>
        </div>
        <p class="error">{{ error }}</p>
      </main>
    </div>
  </div>
</template>

<style scoped>
.hero {
  padding: 88px 20px 52px;
  text-align: center;
  background: radial-gradient(circle at top right, #eef2ff, transparent),
    radial-gradient(circle at top left, #f5f3ff, transparent);
}
.hero h1 {
  font-size: clamp(2rem, 4.8vw, 3rem);
  margin-bottom: 12px;
}
.hero p {
  color: var(--text-muted);
}
.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px 80px;
}
.toolbar {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}
.sticky-toolbar {
  position: sticky;
  top: 10px;
  z-index: 5;
  background: #fff;
  padding: 8px;
  border-radius: 12px;
  border: 1px solid #eceff3;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}
.toolbar-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.me-link {
  font-size: 0.86rem;
  color: var(--primary-color);
  font-weight: 600;
  text-decoration: none;
}
.search {
  width: 100%;
  padding: 11px 12px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  font-size: 0.95rem;
}
.search:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
}
.count {
  font-size: 0.85rem;
  color: var(--text-muted);
}
.post-grid {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 0;
}
.list-scroll-wrap {
  max-height: calc(100vh - 220px);
  overflow: auto;
  padding-right: 4px;
}
.post-card {
  border: 1px solid #eceff3;
  border-radius: 14px;
  padding: 16px;
  background: linear-gradient(180deg, #fff, #fcfcff);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.post-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 26px rgba(15, 23, 42, 0.08);
}
.post-title {
  font-size: 1.1rem;
  font-weight: 600;
  text-decoration: none;
  color: var(--text-main);
}
.post-meta {
  font-size: 0.86rem;
  color: var(--text-muted);
  margin-top: 6px;
}
.links-row {
  margin-top: 10px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.fol-btn {
  font-size: 0.86rem;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font-weight: 600;
}
.fol-btn.on {
  border-color: #a5b4fc;
  background: #eef2ff;
  color: var(--primary-color);
}
.inline-link {
  font-size: 0.86rem;
  text-decoration: none;
  color: var(--primary-color);
  font-weight: 600;
}
.empty {
  text-align: center;
  padding: 28px 8px;
  color: var(--text-muted);
}
.load-state {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.86rem;
  padding: 6px 0 4px;
  min-height: 26px;
}
.error {
  color: var(--danger);
  margin-top: 8px;
  min-height: 20px;
  font-weight: 600;
  font-size: 0.9rem;
}
@media (max-width: 900px) {
  .list-scroll-wrap {
    max-height: 62vh;
  }
  .toolbar-meta {
    align-items: flex-start;
  }
}
</style>
