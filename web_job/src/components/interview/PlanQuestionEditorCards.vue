<script setup>
/**
 * 大纲题目编辑 — 可折叠；展开后随弹窗整体滚动，无内嵌滚动条。
 */
import { computed, nextTick, ref, unref, watch } from "vue";
import { useScrollLoadSentinel, useScrollLoadSlice } from "../../composables/useScrollLoadSlice";
import { emptyQuestion } from "../../modules/interview/planForm";
import PlanQuestionFormSummary from "./PlanQuestionFormSummary.vue";

const props = defineProps({
  questions: { type: Array, default: () => [] },
  /** 弹窗主滚动容器（HTMLElement 或 Ref） */
  scrollRoot: { type: [Object, null], default: null }
});

const emit = defineEmits(["update:questions"]);

const questionsOpen = ref(true);
const sentinelRef = ref(null);

const itemsRef = computed(() => props.questions || []);
const { slice, hasMore, progressLabel, loadMore, revealAll, resetVisible, batchSize } = useScrollLoadSlice(
  itemsRef,
  8
);

const scrollRootRef = computed(() => {
  const root = props.scrollRoot;
  return root && typeof root === "object" && "value" in root ? root.value : root;
});

useScrollLoadSentinel(scrollRootRef, sentinelRef, { hasMore, loadMore });

watch(
  () => props.questions?.length,
  (n, prev) => {
    if (prev != null && n < prev) resetVisible();
  }
);

const firstPreview = computed(() => {
  const q = (props.questions || []).find((it) => String(it.text || "").trim());
  const t = String(q?.text || "").trim();
  if (!t) return "";
  return t.length > 80 ? `${t.slice(0, 80)}…` : t;
});

function emitQuestions(next) {
  emit("update:questions", next);
}

function updateField(index, field, value) {
  const next = props.questions.map((q, i) => (i === index ? { ...q, [field]: value } : q));
  emitQuestions(next);
}

function scrollToBottom() {
  const root = unref(scrollRootRef);
  root?.scrollTo?.({ top: root.scrollHeight, behavior: "smooth" });
}

async function addQuestion() {
  questionsOpen.value = true;
  const next = [...props.questions, emptyQuestion(props.questions.length)];
  emitQuestions(next);
  revealAll();
  await nextTick();
  scrollToBottom();
}

function removeQuestion(index) {
  if (props.questions.length <= 1) return;
  emitQuestions(props.questions.filter((_, i) => i !== index));
}
</script>

<template>
  <section class="editor-wrap">
    <div class="section-head">
      <button type="button" class="section-toggle" @click="questionsOpen = !questionsOpen">
        <div class="toggle-main">
          <span class="toggle-title">题目列表</span>
          <span class="count-badge">{{ questions.length }} 题</span>
          <span v-if="!questionsOpen" class="toggle-hint">{{ firstPreview || "点击展开" }}</span>
        </div>
        <span class="toggle-icon">{{ questionsOpen ? "▾" : "▸" }}</span>
      </button>
      <button v-if="questionsOpen" type="button" class="link-btn" @click="addQuestion">+ 添加题目</button>
    </div>

    <PlanQuestionFormSummary
      v-if="!questionsOpen"
      :count="questions.length"
      :preview="firstPreview"
      :progress-label="progressLabel"
    />

    <template v-else>
      <div class="editor-list">
        <article v-for="(q, i) in slice" :key="i" class="edit-card">
          <div class="edit-card-top">
            <span class="q-badge">第 {{ i + 1 }} 题</span>
            <button
              v-if="questions.length > 1"
              type="button"
              class="link-btn danger"
              @click="removeQuestion(i)"
            >
              删除
            </button>
          </div>
          <textarea
            rows="3"
            class="q-input"
            placeholder="题干"
            :value="q.text"
            @input="updateField(i, 'text', $event.target.value)"
          />
          <div class="meta-row">
            <input
              class="hint-input"
              placeholder="思考提示（可选）"
              :value="q.thinking_hint"
              @input="updateField(i, 'thinking_hint', $event.target.value)"
            />
            <label class="weight-field">
              <span>权重</span>
              <input
                type="number"
                min="0.1"
                step="0.1"
                class="weight-input"
                :value="q.weight ?? 1"
                @input="updateField(i, 'weight', Number($event.target.value) || 1)"
              />
            </label>
          </div>
        </article>

        <div v-if="hasMore" ref="sentinelRef" class="load-sentinel">
          <span class="load-hint">继续下滑加载更多题目…</span>
        </div>
        <p v-else-if="questions.length > batchSize" class="load-done">已全部展示</p>
      </div>

      <footer class="progress-foot">{{ progressLabel }}</footer>
    </template>
  </section>
</template>

<style scoped>
.editor-wrap {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f9fafb;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-right: 12px;
  background: #f8fafc;
  border-bottom: 1px solid #eceff3;
}

.section-toggle {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}

.toggle-main {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.toggle-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: #374151;
}

.count-badge {
  font-size: 0.72rem;
  font-weight: 600;
  color: #047857;
  background: #ecfdf5;
  padding: 2px 8px;
  border-radius: 999px;
}

.toggle-hint {
  flex: 1 1 100%;
  font-size: 0.82rem;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toggle-icon {
  flex-shrink: 0;
  color: #9ca3af;
}

.editor-list {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.edit-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  display: grid;
  gap: 8px;
}

.edit-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.q-badge {
  font-size: 0.72rem;
  font-weight: 700;
  color: #4338ca;
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 999px;
}

.meta-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: end;
}

.q-input,
.hint-input,
.weight-input {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 0.85rem;
  font-family: inherit;
  box-sizing: border-box;
}

.q-input {
  resize: vertical;
  min-height: 72px;
}

.weight-field {
  display: grid;
  gap: 4px;
  font-size: 0.72rem;
  color: #6b7280;
  font-weight: 600;
  min-width: 72px;
}

.weight-input {
  text-align: center;
}

.link-btn {
  border: none;
  background: none;
  color: #6366f1;
  font-size: 0.82rem;
  cursor: pointer;
  font-weight: 600;
  flex-shrink: 0;
  padding: 8px 0;
}

.link-btn.danger {
  color: #dc2626;
}

.load-sentinel {
  display: flex;
  justify-content: center;
  padding: 8px 0 4px;
}

.load-hint,
.load-done {
  margin: 0;
  font-size: 0.78rem;
  color: #9ca3af;
  text-align: center;
}

.progress-foot {
  padding: 8px 12px;
  border-top: 1px dashed #e5e7eb;
  font-size: 0.76rem;
  color: #6b7280;
  text-align: center;
}

@media (max-width: 640px) {
  .meta-row {
    grid-template-columns: 1fr;
  }

  .section-head {
    flex-direction: column;
    align-items: stretch;
    padding-right: 0;
  }

  .link-btn {
    padding: 0 14px 10px;
    text-align: left;
  }
}
</style>
