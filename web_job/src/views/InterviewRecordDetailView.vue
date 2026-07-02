<script setup>
/**
 * 单条面试记录详情 — 概览面板 + 逐题时间线，使用首页侧栏壳层。
 */
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getStudentId } from "../api/client";
import HomeTopBar from "../components/home/HomeTopBar.vue";
import InterviewAnswerTimeline from "../components/interview/InterviewAnswerTimeline.vue";
import InterviewRecordOverviewPanel from "../components/interview/InterviewRecordOverviewPanel.vue";
import InterviewSummaryBadge from "../components/interview/InterviewSummaryBadge.vue";
import SessionStatusBadge from "../components/interview/SessionStatusBadge.vue";
import { formatDateTime, formatProgress } from "../modules/interview/formatters";
import { useInterviewRecordDetail } from "../modules/interview/useInterviewRecordDetail";
import { useInterviewRecordDelete } from "../modules/interview/useInterviewRecordDelete";

const route = useRoute();
const router = useRouter();
const recordIdRef = computed(() => route.params.recordId);

const { detail, answers, loadError, loading, progressPercent, answeredCount } =
  useInterviewRecordDetail(recordIdRef);

const { deleting, deleteError, confirmAndDelete } = useInterviewRecordDelete();
const actionError = ref("");

const heroTitle = computed(
  () => detail.value?.plan_title || detail.value?.target_role || "面试记录"
);

async function onDeleteRecord() {
  actionError.value = "";
  const ok = await confirmAndDelete(getStudentId(), recordIdRef.value, heroTitle.value);
  if (ok) {
    router.push({ path: "/interview/center" });
    return;
  }
  if (deleteError.value) actionError.value = deleteError.value;
}
</script>

<template>
  <div class="home-main record-detail-main">
      <HomeTopBar
        title="面试记录详情"
        :subtitle="loading && !detail ? '加载中…' : heroTitle"
      />

      <section v-if="detail" class="record-head-card">
        <div class="record-head-main">
          <p class="record-kicker">我的面试记录</p>
          <h1>{{ heroTitle }}</h1>
          <div class="record-badges">
            <SessionStatusBadge :status="detail.session_status" />
            <InterviewSummaryBadge :status="detail.summary_status" />
          </div>
          <p class="record-meta">
            进度 {{ formatProgress(answeredCount, detail.question_total) }}
            · 开始于 {{ formatDateTime(detail.created_at) }}
          </p>
        </div>
        <button
          type="button"
          class="btn-delete"
          :disabled="deleting"
          @click="onDeleteRecord"
        >
          {{ deleting ? "删除中…" : "删除记录" }}
        </button>
      </section>

      <p v-if="loadError || actionError" class="error">{{ loadError || actionError }}</p>
      <template v-else-if="detail">
        <InterviewRecordOverviewPanel
          :detail="detail"
          :progress-percent="progressPercent"
          :answered-count="answeredCount"
        />

        <section class="panel">
          <header class="panel-head">
            <h2>逐题记录</h2>
            <span class="panel-hint">按题号展示题干、作答与评分</span>
          </header>
          <InterviewAnswerTimeline :items="answers" />
        </section>

        <router-link class="back" to="/interview/center">← 返回面试中心</router-link>
      </template>
      <div v-else-if="loading" class="loading-skeleton" aria-busy="true">
        <div class="sk-block" />
        <div class="sk-block sk-block--tall" />
      </div>
  </div>
</template>

<style scoped>
.record-detail-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.record-head-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 18px;
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
}
.record-head-main {
  min-width: 0;
}
.record-kicker {
  margin: 0 0 6px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--home-primary, #5b6adf);
}
.record-head-main h1 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f172a;
}
.record-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.record-meta {
  margin: 10px 0 0;
  font-size: 0.82rem;
  color: #64748b;
}
.btn-delete {
  padding: 8px 14px;
  border: 1px solid #fecaca;
  border-radius: 10px;
  background: #fff;
  color: #b91c1c;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
}
.btn-delete:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.panel {
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  border-radius: var(--home-radius-lg, 16px);
  padding: 16px 18px;
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
}
.panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 14px;
}
.panel-head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
}
.panel-hint {
  font-size: 0.8rem;
  color: #94a3b8;
}
.back {
  display: inline-block;
  color: var(--home-primary, #5b6adf);
  font-size: 0.88rem;
  font-weight: 600;
  text-decoration: none;
}
.back:hover {
  text-decoration: underline;
}
.error {
  color: #b91c1c;
  font-weight: 600;
}
.loading-skeleton {
  display: grid;
  gap: 16px;
}
.sk-block {
  height: 160px;
  border-radius: 16px;
  background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
}
.sk-block--tall {
  height: 280px;
}
@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
