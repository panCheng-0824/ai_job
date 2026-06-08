<script setup>
import { computed } from "vue";
import { parseJobMatchReason } from "../utils/jobMatchReason";

const props = defineProps({
  reason: { type: String, default: "" },
  sections: { type: Array, default: null },
  score: { type: [Number, String], default: null },
  charCount: { type: Number, default: null }
});

const blocks = computed(() => {
  if (Array.isArray(props.sections) && props.sections.length) {
    return props.sections
      .map((s) => ({
        key: s.key || s.title || "section",
        title: s.title || "说明",
        body: String(s.body || "").trim()
      }))
      .filter((s) => s.body);
  }
  return parseJobMatchReason(props.reason);
});

const displayCharCount = computed(() => {
  if (props.charCount != null && props.charCount > 0) return props.charCount;
  return String(props.reason || "").replace(/\s+/g, "").length;
});

const scoreText = computed(() => {
  const v = props.score;
  if (v == null || v === "") return "";
  return String(v);
});
</script>

<template>
  <div class="job-match-reason">
    <div v-if="scoreText || displayCharCount" class="job-match-reason-meta">
      <span v-if="scoreText" class="job-match-reason-score">匹配分 {{ scoreText }}</span>
      <span v-if="displayCharCount" class="job-match-reason-len">约 {{ displayCharCount }} 字</span>
    </div>
    <div v-if="blocks.length" class="job-match-reason-blocks">
      <section v-for="block in blocks" :key="block.key" class="job-match-reason-block">
        <h4 class="job-match-reason-block-title">{{ block.title }}</h4>
        <p class="job-match-reason-block-body">{{ block.body }}</p>
      </section>
    </div>
    <p v-else class="muted job-match-reason-empty">暂无推荐理由。</p>
  </div>
</template>

<style scoped>
.job-match-reason-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-bottom: 10px;
  font-size: 0.78rem;
}
.job-match-reason-score {
  font-weight: 700;
  color: #4338ca;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef2ff;
}
.job-match-reason-len {
  color: #64748b;
}
.job-match-reason-blocks {
  display: grid;
  gap: 10px;
}
.job-match-reason-block {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}
.job-match-reason-block-title {
  margin: 0 0 6px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #4338ca;
  letter-spacing: 0.02em;
}
.job-match-reason-block-body {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.65;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
}
.job-match-reason-empty {
  margin: 0;
  font-size: 0.88rem;
}
.muted {
  color: #6b7280;
}
</style>
