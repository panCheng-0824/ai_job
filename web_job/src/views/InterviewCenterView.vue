<script setup>
/**
 * 面试中心：待面试与历史记录分区展示。
 */
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, getStudentId } from "../api/client";
import HomeTopBar from "../components/home/HomeTopBar.vue";
import InterviewCenterSessionCard from "../components/interview/InterviewCenterSessionCard.vue";
import InterviewCenterStatCards from "../components/interview/InterviewCenterStatCards.vue";
import { fetchInterviewRecords } from "../modules/interview/api";
import { fetchMyInterviewBookings } from "../modules/interview/bookingApi";
import {
  bookingToPendingCard,
  computePassRate,
  isHistoryRecord,
  isUpcomingRecord
} from "../modules/interview/recordCenterMeta";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const error = ref("");
const guest = ref(false);
const studentName = ref("");
const records = ref([]);
const bookings = ref([]);
const bookingNotice = ref("");
const showAllPending = ref(false);
const activeFilter = ref("all");
const activeRecordId = ref("");
const lastLoadedAt = ref(null);

const pendingRecords = computed(() => {
  const fromBookings = bookings.value.map(bookingToPendingCard).filter(Boolean);
  const fromRecords = records.value.filter(isUpcomingRecord);
  return [...fromBookings, ...fromRecords].sort(
    (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
  );
});

const historyRecords = computed(() =>
  records.value
    .filter(isHistoryRecord)
    .sort(
      (a, b) =>
        new Date(b.completed_at || b.created_at || 0).getTime() -
        new Date(a.completed_at || a.created_at || 0).getTime()
    )
);

const pendingCount = computed(() => pendingRecords.value.length);
const finishedCount = computed(() => historyRecords.value.length);
const passRate = computed(() => computePassRate(records.value));

const showPendingSection = computed(() => activeFilter.value === "all" || activeFilter.value === "pending");
const showHistorySection = computed(() => activeFilter.value === "all" || activeFilter.value === "done");

const visiblePending = computed(() => {
  const list = pendingRecords.value;
  if (showAllPending.value || activeFilter.value === "pending") return list;
  return list.slice(0, 6);
});

const hasMorePending = computed(
  () => activeFilter.value === "all" && !showAllPending.value && pendingRecords.value.length > 6
);
const lastLoadedText = computed(() => {
  if (!lastLoadedAt.value) return "尚未刷新";
  return `最近刷新：${new Date(lastLoadedAt.value).toLocaleTimeString()}`;
});

async function loadStudentName(studentId) {
  try {
    const resp = await apiGet(`/api/students/${encodeURIComponent(studentId)}`);
    studentName.value = resp?.学生基本信息?.姓名 || "";
  } catch {
    studentName.value = "";
  }
}

async function loadRecords() {
  const studentId = getStudentId();
  guest.value = !studentId;
  error.value = "";
  if (!studentId) {
    records.value = [];
    bookings.value = [];
    return;
  }
  loading.value = true;
  try {
    await loadStudentName(studentId);
    const [resp, bookingResp] = await Promise.all([
      fetchInterviewRecords(studentId, { fresh: true }),
      fetchMyInterviewBookings(studentId)
    ]);
    records.value = resp.items || [];
    bookings.value = bookingResp.items || [];
    lastLoadedAt.value = Date.now();
    consumeBookingRouterState();
  } catch (e) {
    error.value = e.message || "加载面试记录失败";
  } finally {
    loading.value = false;
  }
}

function onFilter(filter) {
  activeFilter.value = filter;
  if (filter === "pending") showAllPending.value = true;
}

function enterRoom(recordId) {
  if (isJobBookingCardId(recordId)) {
    openBookingPrep(recordId);
    return;
  }
  activeRecordId.value = recordId;
  router.push(`/interview/center/room/${encodeURIComponent(recordId)}`);
}

function isJobBookingCardId(recordId) {
  return String(recordId || "").startsWith("job-booking-");
}

function findBookingByCardId(recordId) {
  const bookingId = Number(String(recordId).replace("job-booking-", ""));
  if (!Number.isFinite(bookingId)) return null;
  return bookings.value.find((b) => Number(b.booking_id) === bookingId) || null;
}

function openBookingPrep(recordId) {
  activeRecordId.value = recordId;
  const booking = findBookingByCardId(recordId);
  const jobId = booking?.job_id;
  router.push(jobId ? { path: "/interview/industry", query: { job_id: jobId } } : "/interview/industry");
}

function openDetail(recordId) {
  if (isJobBookingCardId(recordId)) {
    openBookingPrep(recordId);
    return;
  }
  activeRecordId.value = recordId;
  router.push(`/me/interviews/${encodeURIComponent(recordId)}`);
}

function consumeBookingRouterState() {
  const jobId = history.state?.interviewBookingJobId;
  if (!jobId) return;
  bookingNotice.value = "岗位已加入待面试列表";
  try {
    const next = { ...(history.state || {}) };
    delete next.interviewBookingJobId;
    history.replaceState(next, "");
  } catch {
    /* ignore */
  }
}

function goPickPlan() {
  router.push("/interview/industry");
}

function goChat() {
  router.push("/student-chat");
}

watch(
  () => route.path,
  (path) => {
    if (path === "/interview/center") loadRecords();
  },
  { immediate: true }
);

</script>

<template>
  <div class="home-main interview-center-main">
    <HomeTopBar
      title="面试中心"
      subtitle="管理待开始的模拟面试，回顾历史答题与评分"
      :student-name="studentName"
    />

    <div class="toolbar">
      <span class="toolbar-meta">{{ lastLoadedText }}</span>
      <button type="button" class="refresh-btn" :disabled="loading" @click="loadRecords">
        <span class="refresh-btn-icon" :class="{ 'refresh-btn-icon--spinning': loading }" aria-hidden="true">↻</span>
        <span>{{ loading ? "刷新中…" : "立即刷新" }}</span>
      </button>
    </div>

    <p v-if="guest" class="empty-panel">
      请先
      <router-link to="/login">登录</router-link>
      后查看面试记录。
    </p>
    <p v-else-if="error" class="empty-panel error">{{ error }}</p>

    <template v-else>
      <p v-if="bookingNotice" class="booking-notice" role="status">{{ bookingNotice }}</p>
      <div class="interview-center-content">
      <InterviewCenterStatCards
        :pending-count="pendingCount"
        :finished-count="finishedCount"
        :pass-rate="passRate"
        :loading="loading"
        :active-filter="activeFilter"
        @filter="onFilter"
      />

      <div class="center-layout" :class="{ 'center-layout--single': activeFilter !== 'all' }">
        <section v-if="showPendingSection" class="center-main">
          <header class="section-head">
            <h2>待面试</h2>
            <button type="button" class="link-btn" @click="goPickPlan">去选题库</button>
          </header>

          <p v-if="loading" class="empty-panel">加载中…</p>
          <div v-else-if="pendingRecords.length" class="upcoming-grid">
            <InterviewCenterSessionCard
              v-for="item in visiblePending"
              :key="item.record_id"
              :item="item"
              variant="upcoming"
              :active="activeRecordId === item.record_id"
              @enter-room="enterRoom"
              @open-detail="openDetail"
            />
          </div>
          <p v-else class="empty-panel">
            暂无待开始的模拟面试。可在
            <router-link to="/interview/industry">面试分类</router-link>
            选择大纲，或在
            <button type="button" class="inline-link" @click="goChat">AI助手</button>
            中确认大纲后开始。
          </p>

          <div v-if="hasMorePending" class="more-wrap">
            <button type="button" class="more-btn" @click="showAllPending = true">查看更多</button>
          </div>
        </section>

        <aside v-if="showHistorySection" class="center-rail">
          <header class="section-head">
            <h2>历史面试记录</h2>
            <button
              v-if="activeFilter === 'done'"
              type="button"
              class="link-btn"
              @click="activeFilter = 'all'"
            >
              显示全部
            </button>
          </header>

          <p v-if="loading" class="empty-rail">加载中…</p>
          <div v-else-if="historyRecords.length" class="history-list">
            <InterviewCenterSessionCard
              v-for="item in historyRecords"
              :key="item.record_id"
              :item="item"
              variant="history"
              :active="activeRecordId === item.record_id"
              @enter-room="enterRoom"
              @open-detail="openDetail"
            />
          </div>
          <p v-else class="empty-rail">暂无历史面试记录。</p>
        </aside>
      </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.interview-center-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--home-radius-lg, 16px);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
}

.toolbar-meta {
  margin-right: auto;
  font-size: 0.76rem;
  color: #94a3b8;
}

.interview-center-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #c7d2fe;
  background: linear-gradient(180deg, #ffffff 0%, #f8faff 100%);
  color: #4338ca;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: #eef2ff;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(99, 102, 241, 0.16);
}

.refresh-btn:disabled {
  opacity: 0.62;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.refresh-btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1em;
  height: 1em;
  line-height: 1;
}

.refresh-btn-icon--spinning {
  animation: refresh-spin 0.9s linear infinite;
}

@keyframes refresh-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.center-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);
  gap: 14px;
  align-items: start;
}

.center-layout--single {
  grid-template-columns: 1fr;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.center-main {
  padding: 16px;
  border-radius: var(--home-radius-lg, 16px);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
}

.section-head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
}

.link-btn {
  border: none;
  background: transparent;
  color: var(--home-primary, #5b6adf);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 0;
}

.upcoming-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.center-layout--single .upcoming-grid {
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}

.more-wrap {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}

.more-btn {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 0.84rem;
  font-weight: 600;
  padding: 8px 28px;
  border-radius: 999px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.more-btn:hover {
  border-color: #c7d2fe;
  color: var(--home-primary, #5b6adf);
}

.center-rail {
  position: sticky;
  top: calc(var(--home-topbar-h, 56px) + 20px);
  max-height: calc(100vh - var(--home-topbar-h, 56px) - 48px);
  overflow: auto;
  overscroll-behavior: contain;
  padding: 16px;
  border-radius: var(--home-radius-lg, 16px);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
  display: flex;
  flex-direction: column;
}

.history-list {
  display: grid;
  gap: 12px;
  align-content: start;
}

.empty-panel,
.empty-rail {
  margin: 0;
  padding: 28px 16px;
  text-align: center;
  color: #64748b;
  font-size: 0.88rem;
  line-height: 1.65;
  border-radius: var(--home-radius-lg, 16px);
  border: 1px dashed #dbeafe;
  background: rgba(255, 255, 255, 0.7);
}

.empty-panel.error {
  color: #dc2626;
  border-color: #fecaca;
}

.booking-notice {
  margin: 0;
  padding: 10px 14px;
  border-radius: 10px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #047857;
  font-size: 0.84rem;
  font-weight: 600;
}

.empty-panel a,
.inline-link {
  color: var(--home-primary, #5b6adf);
  font-weight: 600;
  text-decoration: none;
  border: none;
  background: transparent;
  cursor: pointer;
  font: inherit;
  padding: 0;
}

@media (max-width: 900px) {
  .center-layout {
    grid-template-columns: 1fr;
  }

  .center-rail {
    position: static;
    max-height: none;
  }

  .center-main,
  .center-rail {
    padding: 14px;
  }
}
</style>
