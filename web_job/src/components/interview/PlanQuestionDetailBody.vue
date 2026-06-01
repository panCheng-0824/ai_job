<script setup>
/**
 * 题目详情抽屉内容区 — 题干、提示、维度、追问、评分与参考答案分块展示。
 */
import { computed } from "vue";

const props = defineProps({
  question: { type: Object, required: true }
});

const criteriaEntries = computed(() => {
  const raw = props.question?.eval_criteria;
  if (!raw || typeof raw !== "object") return [];
  return Object.entries(raw).filter(([, v]) => v != null && String(v).trim());
});

const durationLabel = computed(() => {
  const sec = Number(props.question?.timeout_seconds);
  if (!sec || sec <= 0) return "";
  if (sec < 60) return `${sec} 秒`;
  const min = Math.round(sec / 60);
  return min === 1 ? "约 1 分钟" : `约 ${min} 分钟`;
});

function formatCriterionKey(key) {
  return String(key || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
</script>

<template>
  <div class="detail-body">
    <section class="hero-card">
      <p class="hero-label">题干</p>
      <p class="hero-text">{{ question.text || "—" }}</p>
    </section>

    <div v-if="question.weight != null || durationLabel" class="stat-row">
      <div v-if="question.weight != null" class="stat">
        <span class="stat-label">权重</span>
        <strong>{{ question.weight }}</strong>
      </div>
      <div v-if="durationLabel" class="stat">
        <span class="stat-label">建议时长</span>
        <strong>{{ durationLabel }}</strong>
      </div>
    </div>

    <section v-if="question.thinking_hint" class="panel panel-hint">
      <h3><span class="panel-icon">提</span>思考提示</h3>
      <p>{{ question.thinking_hint }}</p>
    </section>

    <section v-if="question.dimensions?.length" class="panel">
      <h3><span class="panel-icon">维</span>考察维度</h3>
      <div class="chips">
        <span v-for="d in question.dimensions" :key="d" class="chip chip-dim">{{ d }}</span>
      </div>
    </section>

    <section v-if="question.preset_followups?.length" class="panel">
      <h3><span class="panel-icon">追</span>预设追问</h3>
      <ol class="followups">
        <li v-for="(f, i) in question.preset_followups" :key="i">
          <span class="follow-index">{{ i + 1 }}</span>
          <span>{{ f }}</span>
        </li>
      </ol>
    </section>

    <section v-if="criteriaEntries.length" class="panel">
      <h3><span class="panel-icon">评</span>评分标准</h3>
      <div class="criteria-list">
        <article v-for="[k, v] in criteriaEntries" :key="k" class="criteria-row">
          <h4>{{ formatCriterionKey(k) }}</h4>
          <p>{{ v }}</p>
        </article>
      </div>
    </section>

    <section v-if="question.reference_answer" class="panel panel-ref">
      <h3><span class="panel-icon">答</span>参考答案</h3>
      <p class="ref-text">{{ question.reference_answer }}</p>
    </section>
  </div>
</template>

<style scoped>
.detail-body {
  display: grid;
  gap: 14px;
}

.hero-card {
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
  border: 1px solid #e0e7ff;
}

.hero-label {
  margin: 0 0 8px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6366f1;
}

.hero-text {
  margin: 0;
  font-size: 1rem;
  line-height: 1.65;
  color: #111827;
  white-space: pre-wrap;
  word-break: break-word;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.stat {
  padding: 12px 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #eceff3;
  display: grid;
  gap: 4px;
}

.stat-label {
  font-size: 0.7rem;
  color: #9ca3af;
  font-weight: 600;
}

.stat strong {
  font-size: 1rem;
  color: #1f2937;
}

.panel {
  padding: 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #eceff3;
}

.panel h3 {
  margin: 0 0 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #374151;
}

.panel-icon {
  display: inline-flex;
  width: 22px;
  height: 22px;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: #f3f4f6;
  font-size: 0.72rem;
  color: #6366f1;
}

.panel p,
.ref-text {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.6;
  color: #4b5563;
  white-space: pre-wrap;
  word-break: break-word;
}

.panel-hint {
  background: #fffbeb;
  border-color: #fde68a;
}

.panel-hint .panel-icon {
  background: #fef3c7;
  color: #b45309;
}

.panel-ref {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.panel-ref .panel-icon {
  background: #dcfce7;
  color: #15803d;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip-dim {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 5px 11px;
  border-radius: 999px;
  background: #ecfdf5;
  color: #047857;
}

.followups {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.followups li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #374151;
}

.follow-index {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.72rem;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.criteria-list {
  display: grid;
  gap: 8px;
}

.criteria-row {
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
}

.criteria-row h4 {
  margin: 0 0 4px;
  font-size: 0.78rem;
  font-weight: 700;
  color: #6366f1;
}

.criteria-row p {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.5;
  color: #374151;
}
</style>
