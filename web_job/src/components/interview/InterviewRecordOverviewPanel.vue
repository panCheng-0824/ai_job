<script setup>
/**
 * 面试记录详情 — 概览区：进度、得分、状态与快捷操作。
 */
import { computed } from "vue";
import InterviewSummaryBadge from "./InterviewSummaryBadge.vue";
import SessionStatusBadge from "./SessionStatusBadge.vue";
import { formatDateTime, formatProgress, formatScore } from "../../modules/interview/formatters";

const props = defineProps({
  detail: { type: Object, required: true },
  progressPercent: { type: Number, default: 0 },
  answeredCount: { type: Number, default: 0 }
});

const continueChatQuery = computed(() => {
  const q = {};
  if (props.detail.interview_session_id) {
    q.interview_session = props.detail.interview_session_id;
  }
  if (props.detail.chat_session_id) {
    q.session_id = props.detail.chat_session_id;
  }
  return q;
});

const planDetailLink = computed(() => {
  if (!props.detail.plan_id) return null;
  const q = props.detail.plan_version != null ? { version: String(props.detail.plan_version) } : {};
  return {
    path: `/interview/plans/${encodeURIComponent(props.detail.plan_id)}`,
    query: q
  };
});
</script>

<template>
  <section class="overview">
    <div class="stat-grid">
      <div class="stat-card">
        <span class="stat-label">答题进度</span>
        <strong class="stat-value">{{ formatProgress(answeredCount, detail.question_total) }}</strong>
        <div class="progress-track" aria-hidden="true">
          <div class="progress-fill" :style="{ width: `${progressPercent}%` }" />
        </div>
        <span class="stat-sub">{{ progressPercent }}%</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">综合得分</span>
        <strong class="stat-value stat-value--score">{{ formatScore(detail.total_score) }}</strong>
        <span class="stat-sub">满分按单题评分汇总</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">会话状态</span>
        <div class="stat-badges">
          <SessionStatusBadge :status="detail.session_status" />
          <InterviewSummaryBadge :status="detail.summary_status" />
        </div>
        <span class="stat-sub">record · {{ detail.record_id }}</span>
      </div>
    </div>

    <dl class="meta-list">
      <div v-if="detail.target_role" class="meta-row">
        <dt>目标岗位</dt>
        <dd>{{ detail.target_role }}</dd>
      </div>
      <div v-if="detail.industry_label" class="meta-row">
        <dt>行业分类</dt>
        <dd>{{ detail.industry_label }}</dd>
      </div>
      <div v-if="detail.plan_id" class="meta-row">
        <dt>关联大纲</dt>
        <dd>
          {{ detail.plan_id }}
          <span v-if="detail.plan_version != null" class="muted">v{{ detail.plan_version }}</span>
        </dd>
      </div>
      <div class="meta-row">
        <dt>开始时间</dt>
        <dd>{{ formatDateTime(detail.created_at) }}</dd>
      </div>
      <div v-if="detail.completed_at" class="meta-row">
        <dt>完成时间</dt>
        <dd>{{ formatDateTime(detail.completed_at) }}</dd>
      </div>
      <div v-if="detail.summary_at" class="meta-row">
        <dt>总结时间</dt>
        <dd>{{ formatDateTime(detail.summary_at) }}</dd>
      </div>
    </dl>

    <div class="actions">
      <router-link
        v-if="detail.interview_session_id"
        class="btn btn-primary"
        :to="{ path: '/student-chat', query: continueChatQuery }"
      >
        继续模拟面试
      </router-link>
      <router-link v-if="planDetailLink" class="btn btn-secondary" :to="planDetailLink">
        查看面试大纲
      </router-link>
    </div>
  </section>
</template>

<style scoped>
.overview {
  background: #fff;
  border: 1px solid #eceff3;
  border-radius: 16px;
  padding: 18px;
  margin-bottom: 16px;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}
.stat-card {
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 14px;
}
.stat-label {
  display: block;
  font-size: 0.78rem;
  color: var(--text-muted, #6b7280);
  margin-bottom: 4px;
}
.stat-value {
  font-size: 1.35rem;
  color: #111827;
}
.stat-value--score {
  color: #047857;
}
.stat-sub {
  display: block;
  margin-top: 6px;
  font-size: 0.75rem;
  color: var(--text-muted, #9ca3af);
}
.stat-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}
.progress-track {
  height: 6px;
  background: #e5e7eb;
  border-radius: 999px;
  margin-top: 8px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #2563eb);
  border-radius: 999px;
  transition: width 0.35s ease;
}
.meta-list {
  display: grid;
  gap: 8px;
  margin: 0 0 16px;
}
.meta-row {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px;
  font-size: 0.88rem;
}
.meta-row dt {
  color: var(--text-muted, #6b7280);
  margin: 0;
}
.meta-row dd {
  margin: 0;
  color: #111827;
}
.muted {
  color: var(--text-muted, #9ca3af);
  font-size: 0.82rem;
  margin-left: 4px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid transparent;
}
.btn-primary {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
}
.btn-secondary {
  background: #fff;
  border-color: #d1d5db;
  color: #374151;
}
</style>
