<script setup>
/**
 * 单条面试记录详情 — 概览面板 + 逐题时间线，风格与面试大纲详情页对齐。
 */
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getStudentId } from "../api/client";
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
    router.push({ path: "/me", query: { tab: "interviews" } });
    return;
  }
  if (deleteError.value) actionError.value = deleteError.value;
}
</script>

<template>
  <div class="detail-page">
    <section class="hero">
      <p class="hero-kicker">我的面试记录</p>
      <h1>{{ loading && !detail ? "加载中…" : heroTitle }}</h1>
      <div v-if="detail" class="hero-badges">
        <SessionStatusBadge :status="detail.session_status" />
        <InterviewSummaryBadge :status="detail.summary_status" />
      </div>
      <p v-if="detail" class="hero-meta">
        进度 {{ formatProgress(answeredCount, detail.question_total) }}
        · 开始于 {{ formatDateTime(detail.created_at) }}
      </p>
      <button
        v-if="detail"
        type="button"
        class="btn-delete-hero"
        :disabled="deleting"
        @click="onDeleteRecord"
      >
        {{ deleting ? "删除中…" : "删除记录" }}
      </button>
    </section>

    <div class="container">
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

        <router-link class="back" to="/me?tab=interviews">← 返回我的面试记录</router-link>
      </template>
      <div v-else-if="loading" class="loading-skeleton" aria-busy="true">
        <div class="sk-block" />
        <div class="sk-block sk-block--tall" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 260px);
}

.hero {
  padding: 88px 20px 20px;
  text-align: center;
}

.hero-kicker {
  margin: 0 0 6px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6366f1;
}

.hero-badges {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.hero-meta {
  margin: 10px 0 0;
  font-size: 0.88rem;
  color: var(--text-muted, #6b7280);
}

.btn-delete-hero {
  margin-top: 12px;
  padding: 6px 14px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fff;
  color: #b91c1c;
  font-size: 0.85rem;
  cursor: pointer;
}

.btn-delete-hero:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.container {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 18px 80px;
}

.panel {
  background: #fff;
  border: 1px solid #eceff3;
  border-radius: 16px;
  padding: 16px 18px;
  margin-bottom: 16px;
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
}

.panel-hint {
  font-size: 0.8rem;
  color: var(--text-muted, #9ca3af);
}

.back {
  display: inline-block;
  margin-top: 4px;
  color: var(--primary-color, #6366f1);
  font-size: 0.9rem;
  text-decoration: none;
}

.error {
  color: #dc2626;
  padding: 12px 0;
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
