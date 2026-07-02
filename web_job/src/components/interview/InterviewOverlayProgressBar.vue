<script setup>
/**
 * 面试遮层 — 顶部进度条与可点击题号步进。
 *
 * 绿=已答（回看）、蓝=答题中、灰=待答（不可点）。
 */
import { computed } from "vue";
import {
  isProgressDotClickable,
  resolveProgressDotKind
} from "../../modules/interview/interviewOverlayHelpers";

const props = defineProps({
  /** 当前正在作答的 seq_no */
  liveSeqNo: { type: Number, default: 0 },
  /** 用户选中的 seq_no（回看已答或点回答题中） */
  selectedSeqNo: { type: Number, default: null },
  total: { type: Number, default: 0 },
  questions: { type: Array, default: () => [] }
});

const emit = defineEmits(["select"]);

const sortedQuestions = computed(() => {
  const list = Array.isArray(props.questions) ? [...props.questions] : [];
  return list.sort((a, b) => Number(a.seq_no ?? 0) - Number(b.seq_no ?? 0));
});

const displayIndex = computed(() => {
  const t = props.total;
  const sel = props.selectedSeqNo != null ? Number(props.selectedSeqNo) : Number(props.liveSeqNo);
  const i = sel + 1;
  if (t > 0) return Math.min(i, t);
  return i;
});

const percent = computed(() => {
  if (!props.total) return 0;
  return Math.min(100, Math.round((displayIndex.value / props.total) * 100));
});

function dotMeta(q) {
  const kind = resolveProgressDotKind(q, props.liveSeqNo);
  const seq = Number(q?.seq_no ?? 0);
  const selected =
    props.selectedSeqNo != null ? Number(props.selectedSeqNo) === seq : Number(props.liveSeqNo) === seq;
  const questionText = q?.question_text || "";
  return { kind, seq, selected, clickable: isProgressDotClickable(kind), questionText };
}

function dotClass(meta) {
  return {
    dot: true,
    [`dot--${meta.kind}`]: true,
    "dot--selected": meta.selected,
    "dot--clickable": meta.clickable,
    "dot--disabled": !meta.clickable
  };
}

function dotTitle(meta, q) {
  const preview = (q?.question_text || "").slice(0, 50);
  const suffix = preview ? ` — "${preview}"` : "";
  if (meta.kind === "done") return `第 ${meta.seq + 1} 题 · 已答 ✓ 点击回看答题记录${suffix}`;
  if (meta.kind === "live") return `第 ${meta.seq + 1} 题 · 答题中${suffix}`;
  return `第 ${meta.seq + 1} 题 · 待答${suffix}`;
}

function onDotClick(q) {
  const meta = dotMeta(q);
  if (!meta.clickable) return;
  emit("select", { seqNo: meta.seq, kind: meta.kind });
}
</script>

<template>
  <div class="progress-wrap">
    <div class="progress-meta">
      <span class="progress-label">第 <strong class="progress-num">{{ displayIndex }}</strong> / {{ total || "?" }} 题</span>
      <span class="progress-pct">{{ percent }}%（已完成）</span>
    </div>
    <div class="progress-track" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100">
      <div class="progress-fill" :style="{ width: `${percent}%` }" />
    </div>
    <div
      v-if="total > 0 && total <= 20"
      class="progress-dots"
      role="list"
      aria-label="题目进度，绿色已答可回看，蓝色为答题中，灰色待答不可点"
    >
      <button
        v-for="q in sortedQuestions.slice(0, total)"
        :key="q.question_id || q.seq_no"
        type="button"
        role="listitem"
        class="dot-btn"
        :class="dotClass(dotMeta(q))"
        :title="dotTitle(dotMeta(q), q)"
        :disabled="!dotMeta(q).clickable"
        :aria-current="dotMeta(q).selected ? 'step' : undefined"
        @click="onDotClick(q)"
      />
    </div>
    <p v-if="total > 0 && total <= 20" class="progress-dots-legend">
      <span class="legend-dot legend-dot--done">●</span> 已答可回看
      <span class="legend-dot legend-dot--live">●</span> 答题中
      <span class="legend-dot legend-dot--pending">●</span> 待答
    </p>
    <p v-else-if="total > 20" class="progress-dots-hint">共 {{ total }} 题，题号较多请通过下方题干区作答</p>
  </div>
</template>

<style scoped>
.progress-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.progress-meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 13px;
}
.progress-label {
  font-weight: 600;
  color: var(--text, #0f172a);
}
.progress-num {
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
}
.progress-pct {
  color: var(--text-muted, #64748b);
  font-variant-numeric: tabular-nums;
}
.progress-track {
  height: 6px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #059669, #10b981);
  transition: width 0.35s ease;
}
.progress-dots {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.progress-dots-hint {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}
.dot-btn {
  width: 10px;
  height: 10px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: #cbd5e1;
}
.dot-btn.dot--done {
  background: #10b981;
  position: relative;
}
.dot-btn.dot--done::after {
  content: "✓";
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 7px;
  font-weight: 800;
  color: #fff;
  line-height: 1;
}
.dot-btn.dot--live {
  background: #2563eb;
  animation: dot-pulse 1.5s ease-in-out infinite;
}
@keyframes dot-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4); }
  50% { box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.2); }
}
.dot-btn.dot--pending {
  background: #cbd5e1;
}
.dot-btn.dot--clickable {
  cursor: pointer;
}
.dot-btn.dot--clickable:hover {
  transform: scale(1.15);
}
.dot-btn.dot--selected.dot--done,
.dot-btn.dot--selected.dot--live {
  box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.2);
}
.dot-btn.dot--disabled {
  cursor: not-allowed;
  opacity: 0.85;
}
.progress-dots-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin: 0;
  font-size: 12px;
  color: #64748b;
}
.legend-dot {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.legend-dot--done {
  color: #10b981;
}
.legend-dot--live {
  color: #2563eb;
}
.legend-dot--pending {
  color: #cbd5e1;
}
</style>
