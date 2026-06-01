<script setup>
/**
 * 大纲题目只读卡片 — 支持点击打开详情抽屉；下滑加载更多。
 */
import { computed, ref, watch } from "vue";
import { useScrollLoadSentinel, useScrollLoadSlice } from "../../composables/useScrollLoadSlice";
import PlanQuestionDetailDrawer from "./PlanQuestionDetailDrawer.vue";

const props = defineProps({
  questions: { type: Array, default: () => [] },
  pageSize: { type: Number, default: 12 },
  /** 详情页开启：点击卡片弹出抽屉 */
  interactive: { type: Boolean, default: false }
});

const itemsRef = computed(() => props.questions || []);
const scrollRootRef = ref(null);
const sentinelRef = ref(null);
const activeIndex = ref(-1);
const drawerVisible = ref(false);

const { slice, hasMore, progressLabel, loadMore, resetVisible, batchSize } = useScrollLoadSlice(
  itemsRef,
  props.pageSize
);

useScrollLoadSentinel(scrollRootRef, sentinelRef, { hasMore, loadMore });

watch(
  () => props.questions?.length,
  () => resetVisible()
);

const activeQuestion = computed(() =>
  activeIndex.value >= 0 ? props.questions[activeIndex.value] : null
);

function questionKey(q, i) {
  return q.iq_row_id || q.question_id || `q-${i}`;
}

function previewText(text) {
  const t = String(text || "").trim();
  if (t.length <= 140) return t;
  return `${t.slice(0, 140)}…`;
}

function openQuestion(index) {
  if (!props.interactive) return;
  activeIndex.value = index;
  drawerVisible.value = true;
}

function closeDrawer() {
  drawerVisible.value = false;
}

function goPrev() {
  if (activeIndex.value > 0) activeIndex.value -= 1;
}

function goNext() {
  if (activeIndex.value < props.questions.length - 1) activeIndex.value += 1;
}
</script>

<template>
  <div class="q-card-list">
    <div v-if="!questions.length" class="empty">暂无题目</div>
    <template v-else>
      <p v-if="interactive" class="hint">点击题目查看详情 · 抽屉内可用 ← → 切换题目</p>

      <div ref="scrollRootRef" class="q-scroll">
        <component
          :is="interactive ? 'button' : 'article'"
          v-for="(q, i) in slice"
          :key="questionKey(q, i)"
          class="q-card"
          :class="{ 'q-card--active': interactive && activeIndex === i && drawerVisible }"
          :type="interactive ? 'button' : undefined"
          @click="interactive ? openQuestion(i) : undefined"
        >
          <header class="q-card-head">
            <span class="q-badge">Q{{ (q.seq_no ?? i) + 1 }}</span>
            <span v-if="q.weight && q.weight !== 1" class="q-weight">权重 {{ q.weight }}</span>
          </header>
          <p class="q-text" :title="q.text">{{ previewText(q.text) }}</p>
          <p v-if="q.thinking_hint" class="q-hint">提示：{{ q.thinking_hint }}</p>
          <span v-if="interactive" class="q-tap">查看详情 →</span>
        </component>

        <div v-if="hasMore" ref="sentinelRef" class="load-sentinel">
          <span class="load-hint">继续下滑加载更多…</span>
        </div>
        <p v-else-if="questions.length > batchSize" class="load-done">已全部展示</p>
      </div>

      <footer class="progress-foot">{{ progressLabel }}</footer>

      <PlanQuestionDetailDrawer
        :visible="drawerVisible"
        :question="activeQuestion"
        :index="activeIndex"
        :total="questions.length"
        @close="closeDrawer"
        @prev="goPrev"
        @next="goNext"
      />
    </template>
  </div>
</template>

<style scoped>
.q-card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.hint {
  margin: 0 0 4px;
  font-size: 0.78rem;
  color: #9ca3af;
}

.q-scroll {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
  max-height: min(52vh, 520px);
  overflow-y: auto;
  padding: 2px 4px 4px 0;
  align-content: start;
}

.q-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fafbff;
  min-height: 88px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: left;
  font-family: inherit;
}

button.q-card {
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}

button.q-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.12);
  transform: translateY(-1px);
}

.q-card--active {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.q-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.q-badge {
  font-size: 0.72rem;
  font-weight: 700;
  color: #4338ca;
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 999px;
}

.q-weight {
  font-size: 0.68rem;
  color: #6b7280;
}

.q-text {
  margin: 0;
  font-size: 0.84rem;
  line-height: 1.45;
  color: #1f2937;
  word-break: break-word;
}

.q-hint {
  margin: 0;
  font-size: 0.72rem;
  color: #6b7280;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.q-tap {
  margin-top: auto;
  font-size: 0.72rem;
  font-weight: 600;
  color: #6366f1;
}

.load-sentinel {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  padding: 8px 0;
}

.load-hint,
.load-done {
  margin: 0;
  font-size: 0.78rem;
  color: #9ca3af;
}

.progress-foot {
  font-size: 0.76rem;
  color: #6b7280;
  text-align: center;
  padding-top: 4px;
  border-top: 1px solid #f1f5f9;
}

.empty {
  text-align: center;
  color: #9ca3af;
  font-size: 0.88rem;
  padding: 24px;
}
</style>
