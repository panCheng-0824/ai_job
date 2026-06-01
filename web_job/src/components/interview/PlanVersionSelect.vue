<script setup>
/**
 * 大纲详情页 — 版本下拉选择（多版本时展示）。
 */
import { computed } from "vue";
import { formatDateTime } from "../../modules/interview/formatters";

const props = defineProps({
  versions: { type: Array, default: () => [] },
  modelValue: { type: Number, default: null }
});

const emit = defineEmits(["update:modelValue"]);

const hasMultiple = computed(() => (props.versions?.length || 0) > 1);

function labelOf(item) {
  const latest = item.is_latest ? " · 最新" : "";
  const date = item.created_at ? formatDateTime(item.created_at) : "";
  const count = item.question_count != null ? `${item.question_count} 题` : "";
  const meta = [count, date].filter(Boolean).join(" · ");
  return meta ? `v${item.version}${latest}（${meta}）` : `v${item.version}${latest}`;
}

function onChange(event) {
  const next = Number(event.target.value);
  if (!Number.isNaN(next)) {
    emit("update:modelValue", next);
  }
}
</script>

<template>
  <div v-if="hasMultiple" class="version-select-wrap">
    <label class="version-label" for="plan-version-select">版本</label>
    <select
      id="plan-version-select"
      class="version-select"
      :value="modelValue"
      @change="onChange"
    >
      <option v-for="item in versions" :key="item.version" :value="item.version">
        {{ labelOf(item) }}
      </option>
    </select>
  </div>
</template>

<style scoped>
.version-select-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.version-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: #4b5563;
}

.version-select {
  min-width: 220px;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  font-size: 0.88rem;
  color: #111827;
}

.version-select:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}
</style>
