<script setup>
/**
 * 面试记录列表卡片，用于「我的」页与记录详情入口。
 */
import InterviewSummaryBadge from "./InterviewSummaryBadge.vue";
import SessionStatusBadge from "./SessionStatusBadge.vue";
import { formatDateTime, formatProgress, formatScore } from "../../modules/interview/formatters";
import { useInterviewRecordDelete } from "../../modules/interview/useInterviewRecordDelete";

const props = defineProps({
  item: { type: Object, required: true },
  studentId: { type: String, default: "" }
});

const emit = defineEmits(["deleted"]);

const { deleting, confirmAndDelete } = useInterviewRecordDelete();

const displayTitle = () =>
  props.item.plan_title || props.item.target_role || "模拟面试";

async function onDeleteClick(evt) {
  evt.preventDefault();
  evt.stopPropagation();
  const ok = await confirmAndDelete(props.studentId, props.item.record_id, displayTitle());
  if (ok) emit("deleted", props.item.record_id);
}
</script>

<template>
  <li class="card">
    <div class="head">
      <router-link class="title" :to="`/me/interviews/${encodeURIComponent(item.record_id)}`">
        {{ displayTitle() }}
      </router-link>
      <div class="head-actions">
        <div class="badges">
          <SessionStatusBadge :status="item.session_status" />
          <InterviewSummaryBadge :status="item.summary_status" />
        </div>
        <button
          type="button"
          class="btn-delete"
          :disabled="deleting || !studentId"
          title="删除面试记录"
          @click="onDeleteClick"
        >
          {{ deleting ? "删除中…" : "删除" }}
        </button>
      </div>
    </div>
    <p v-if="item.industry_label" class="muted">行业：{{ item.industry_label }}</p>
    <p class="muted">
      进度 {{ formatProgress(item.question_answered, item.question_total) }}
      · 得分 {{ formatScore(item.total_score) }}
    </p>
    <p class="muted time">{{ formatDateTime(item.created_at) }}</p>
  </li>
</template>

<style scoped>
.card {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px;
  list-style: none;
}
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.head-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
}
.title {
  color: var(--primary-color, #6366f1);
  font-weight: 600;
  text-decoration: none;
}
.btn-delete {
  padding: 2px 8px;
  border: 1px solid #fecaca;
  border-radius: 6px;
  background: #fff;
  color: #b91c1c;
  font-size: 0.75rem;
  cursor: pointer;
}
.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.muted {
  color: var(--text-muted, #6b7280);
  font-size: 0.85rem;
  margin-top: 6px;
}
.time {
  font-size: 0.8rem;
}
</style>
