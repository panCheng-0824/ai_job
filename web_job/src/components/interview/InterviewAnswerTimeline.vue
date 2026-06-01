<script setup>
/**
 * 逐题答题时间线 — 展示题干、作答、评分与筛选。
 */
import { computed, ref } from "vue";
import { ANSWER_STATUS } from "../../modules/interview/constants";
import { formatDateTime, formatScore } from "../../modules/interview/formatters";

const props = defineProps({
  items: { type: Array, default: () => [] }
});

const filter = ref("all");

const filterOptions = [
  { id: "all", label: "全部" },
  { id: "pending", label: "未答" },
  { id: "done", label: "已答" }
];

const counts = computed(() => {
  const all = props.items.length;
  const pending = props.items.filter((a) => a.answer_status === "pending").length;
  return { all, pending, done: all - pending };
});

const filteredItems = computed(() => {
  if (filter.value === "pending") {
    return props.items.filter((a) => a.answer_status === "pending");
  }
  if (filter.value === "done") {
    return props.items.filter((a) => a.answer_status && a.answer_status !== "pending");
  }
  return props.items;
});

function statusMeta(s) {
  return ANSWER_STATUS[s] || { label: s || "—", tone: "muted" };
}

function displaySeq(a) {
  const n = Number(a.seq_no);
  return Number.isNaN(n) ? "?" : n + 1;
}

function questionPreview(text, questionId) {
  const t = String(text || "").trim();
  if (t) {
    if (t.length <= 200) return t;
    return `${t.slice(0, 200)}…`;
  }
  const qid = String(questionId || "").trim();
  if (qid) return `（题干未同步，题目 ID：${qid}）`;
  return "（题干未同步至题库，请确认大纲 MQ 已落库）";
}
</script>

<template>
  <div class="timeline-wrap">
    <div class="toolbar">
      <div class="filters" role="tablist" aria-label="答题筛选">
        <button
          v-for="opt in filterOptions"
          :key="opt.id"
          type="button"
          class="filter-btn"
          :class="{ active: filter === opt.id }"
          @click="filter = opt.id"
        >
          {{ opt.label }}
          <span class="count">{{ counts[opt.id] ?? counts.all }}</span>
        </button>
      </div>
      <span class="toolbar-hint">共 {{ items.length }} 题</span>
    </div>

    <ol class="timeline">
      <li v-if="!filteredItems.length" class="empty">
        {{ filter === "all" ? "暂无答题记录" : "当前筛选下无题目" }}
      </li>
      <li
        v-for="a in filteredItems"
        :key="a.answer_row_id || a.question_id"
        class="step"
        :class="`step--${statusMeta(a.answer_status).tone}`"
      >
        <div class="step-marker" aria-hidden="true" />
        <div class="step-body">
          <header class="step-head">
            <span class="seq">第 {{ displaySeq(a) }} 题</span>
            <span class="status" :class="`status--${statusMeta(a.answer_status).tone}`">
              {{ statusMeta(a.answer_status).label }}
            </span>
          </header>

          <p class="question">{{ questionPreview(a.question_text, a.question_id) }}</p>

          <details v-if="a.answer_text" class="answer-block" open>
            <summary>我的回答</summary>
            <p class="answer">{{ a.answer_text }}</p>
          </details>
          <p v-else class="answer-empty">尚未作答，可在「继续模拟面试」中完成本题。</p>

          <div v-if="a.score != null || a.evaluator_comment" class="eval-block">
            <p v-if="a.score != null" class="score">
              得分 <strong>{{ formatScore(a.score) }}</strong>
            </p>
            <p v-if="a.evaluator_comment" class="comment">{{ a.evaluator_comment }}</p>
          </div>

          <footer class="step-foot">
            <span v-if="a.answered_at">答题 {{ formatDateTime(a.answered_at) }}</span>
            <span v-if="a.summarized_at"> · 总结 {{ formatDateTime(a.summarized_at) }}</span>
            <span v-if="a.question_id" class="qid">ID {{ a.question_id }}</span>
          </footer>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.timeline-wrap {
  display: grid;
  gap: 12px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.filter-btn {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 0.82rem;
  cursor: pointer;
  color: #374151;
}
.filter-btn.active {
  border-color: #6366f1;
  background: #eef2ff;
  color: #4338ca;
  font-weight: 600;
}
.count {
  margin-left: 4px;
  opacity: 0.75;
}
.toolbar-hint {
  font-size: 0.8rem;
  color: var(--text-muted, #9ca3af);
}
.timeline {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}
.step {
  position: relative;
  display: grid;
  grid-template-columns: 12px 1fr;
  gap: 12px;
}
.step-marker {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 14px;
  background: #d1d5db;
  box-shadow: 0 0 0 3px #f3f4f6;
}
.step--info .step-marker {
  background: #6366f1;
  box-shadow: 0 0 0 3px #eef2ff;
}
.step--ok .step-marker {
  background: #059669;
  box-shadow: 0 0 0 3px #d1fae5;
}
.step-body {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px 14px;
  background: #fff;
}
.step-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.seq {
  font-size: 0.82rem;
  font-weight: 700;
  color: #4338ca;
}
.status {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
}
.status--muted {
  background: #f3f4f6;
  color: #6b7280;
}
.status--info {
  background: #eef2ff;
  color: #4338ca;
}
.status--ok {
  background: #d1fae5;
  color: #047857;
}
.question {
  margin: 0 0 10px;
  font-size: 0.92rem;
  line-height: 1.55;
  color: #111827;
  white-space: pre-wrap;
}
.answer-block {
  margin: 0 0 8px;
  border-left: 3px solid #e5e7eb;
  padding-left: 10px;
}
.answer-block summary {
  cursor: pointer;
  font-size: 0.82rem;
  color: var(--text-muted, #6b7280);
  margin-bottom: 6px;
}
.answer {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.55;
  white-space: pre-wrap;
  color: #374151;
}
.answer-empty {
  margin: 0 0 8px;
  font-size: 0.85rem;
  color: var(--text-muted, #9ca3af);
  font-style: italic;
}
.eval-block {
  margin-top: 8px;
  padding: 8px 10px;
  background: #f0fdf4;
  border-radius: 8px;
}
.score {
  margin: 0;
  font-size: 0.85rem;
  color: #047857;
}
.comment {
  margin: 6px 0 0;
  font-size: 0.85rem;
  color: #4b5563;
  line-height: 1.5;
}
.step-foot {
  margin-top: 10px;
  font-size: 0.75rem;
  color: var(--text-muted, #9ca3af);
}
.qid {
  margin-left: 8px;
}
.empty {
  text-align: center;
  color: var(--text-muted, #6b7280);
  padding: 24px 16px;
  border: 1px dashed #e5e7eb;
  border-radius: 12px;
}
</style>
