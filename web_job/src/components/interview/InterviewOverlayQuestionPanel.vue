<script setup>
/**
 * 面试遮层 — 当前题干卡片（序号、状态、题干、思考提示）。
 */
import { computed } from "vue";
import { answerStatusMeta, phaseLabel } from "../../modules/interview/interviewOverlayHelpers";

const props = defineProps({
  seqNo: { type: Number, default: 0 },
  questionText: { type: String, default: "" },
  thinkingHint: { type: String, default: "" },
  answerStatus: { type: String, default: "pending" },
  phase: { type: String, default: "question" }
});

const status = computed(() => answerStatusMeta(props.answerStatus));
const phaseText = computed(() => phaseLabel(props.phase));
const displaySeq = computed(() => (Number.isFinite(props.seqNo) ? props.seqNo + 1 : 1));
</script>

<template>
  <section class="question-panel" aria-label="当前题目">
    <div class="question-panel__tags">
      <span class="tag tag--phase">{{ phaseText }}</span>
      <span class="tag" :class="`tag--${status.tone}`">{{ status.label }}</span>
    </div>
    <h3 class="question-panel__title">第 {{ displaySeq }} 题</h3>
    <p v-if="questionText" class="question-panel__text">{{ questionText }}</p>
    <p v-else class="question-panel__placeholder">面试官正在出题，请稍候…</p>
    <p v-if="thinkingHint" class="question-panel__hint">
      <span class="hint-label">思考方向</span>
      {{ thinkingHint }}
    </p>
  </section>
</template>

<style scoped>
.question-panel {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 18px;
}
.question-panel__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.tag {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
}
.tag--phase {
  background: #dbeafe;
  color: #1d4ed8;
}
.tag--done {
  background: #d1fae5;
  color: #047857;
}
.tag--active {
  background: #fef3c7;
  color: #b45309;
}
.tag--pending {
  background: #f1f5f9;
  color: #64748b;
}
.question-panel__title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.question-panel__text {
  margin: 0;
  font-size: 16px;
  line-height: 1.65;
  color: #0f172a;
  font-weight: 500;
}
.question-panel__placeholder {
  margin: 0;
  font-size: 14px;
  color: #94a3b8;
  font-style: italic;
}
.question-panel__hint {
  margin: 12px 0 0;
  padding-top: 12px;
  border-top: 1px dashed #cbd5e1;
  font-size: 13px;
  line-height: 1.55;
  color: #475569;
}
.hint-label {
  display: inline-block;
  margin-right: 6px;
  font-weight: 600;
  color: #0369a1;
}
</style>
