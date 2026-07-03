<script setup>
import { computed, reactive, watch } from "vue";

const RADAR_DEFS = [
  { key: "professional", label: "专业能力" },
  { key: "communication", label: "沟通能力" },
  { key: "office", label: "办公技能" },
  { key: "comprehensive", label: "综合素养" },
  { key: "practice", label: "实践能力" }
];

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  suggestedTags: { type: Array, default: () => [] },
  section: { type: String, default: "all" } // all | tags | radar
});

const form = reactive({
  tagsText: "",
  radar: {
    professional: 72,
    communication: 72,
    office: 72,
    comprehensive: 72,
    practice: 72
  }
});

const tagList = computed(() => linesToTags(form.tagsText));

watch(
  () => props.modelValue,
  (v) => {
    form.tagsText = Array.isArray(v?.tags) ? v.tags.join("、") : "";
    for (const dim of RADAR_DEFS) {
      const n = Number(v?.radar?.[dim.key]);
      form.radar[dim.key] = Number.isFinite(n) ? Math.max(0, Math.min(100, n)) : 72;
    }
  },
  { immediate: true, deep: true }
);

function linesToTags(text) {
  return String(text || "")
    .split(/[,，、\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 20);
}

function addSuggested(tag) {
  const current = linesToTags(form.tagsText);
  if (current.includes(tag)) return;
  current.push(tag);
  form.tagsText = current.join("、");
}

function removeTag(tag) {
  form.tagsText = tagList.value.filter((t) => t !== tag).join("、");
}

function isTagAdded(tag) {
  return tagList.value.includes(tag);
}

function getPayload() {
  return {
    tags: linesToTags(form.tagsText),
    radar: { ...form.radar }
  };
}

defineExpose({ getPayload });
</script>

<template>
  <div class="form-stack">
    <section v-if="props.section !== 'radar'" class="form-section">
      <h4 class="form-section-title">能力标签</h4>
      <p class="form-section-desc">最多 20 个，将用于岗位匹配与简历展示。</p>
      <label class="field">
        <span class="sr-only">能力标签</span>
        <input v-model="form.tagsText" placeholder="输入标签，多个用顿号分隔" />
      </label>
      <div v-if="tagList.length" class="tag-preview">
        <span v-for="tag in tagList" :key="tag" class="tag-chip">
          {{ tag }}
          <button type="button" class="tag-remove" :aria-label="`移除 ${tag}`" @click="removeTag(tag)">×</button>
        </span>
      </div>
      <div v-if="suggestedTags.length" class="suggest-block">
        <span class="suggest-label">推荐标签（来自奖惩/专业）</span>
        <div class="suggest-tags">
          <button
            v-for="tag in suggestedTags"
            :key="tag"
            type="button"
            class="suggest-tag"
            :class="{ 'suggest-tag--added': isTagAdded(tag) }"
            :disabled="isTagAdded(tag)"
            @click="addSuggested(tag)"
          >
            {{ isTagAdded(tag) ? "✓" : "+" }} {{ tag }}
          </button>
        </div>
      </div>
    </section>

    <section v-if="props.section !== 'tags'" class="form-section">
      <h4 class="form-section-title">能力雷达</h4>
      <p class="form-section-desc">自评 0–100，拖动滑块调整各维度得分。</p>
      <div class="radar-block">
        <label v-for="dim in RADAR_DEFS" :key="dim.key" class="slider-field">
          <div class="slider-head">
            <span>{{ dim.label }}</span>
            <strong>{{ form.radar[dim.key] }}</strong>
          </div>
          <input
            v-model.number="form.radar[dim.key]"
            type="range"
            min="0"
            max="100"
            step="1"
            :style="{ '--val': form.radar[dim.key] + '%' }"
          />
        </label>
      </div>
    </section>
  </div>
</template>

<style scoped>
.form-stack {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-section-title {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 700;
  color: #334155;
}

.form-section-desc {
  margin: -2px 0 0;
  font-size: 0.74rem;
  color: #94a3b8;
  line-height: 1.45;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field input {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.88rem;
  color: #0f172a;
  font-family: inherit;
  background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.field input:focus {
  outline: none;
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15);
}

.tag-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px 4px 12px;
  border-radius: 999px;
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.74rem;
  font-weight: 600;
}

.tag-remove {
  border: none;
  background: transparent;
  color: #6366f1;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
  opacity: 0.7;
}

.tag-remove:hover {
  opacity: 1;
}

.suggest-block {
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
}

.suggest-label {
  display: block;
  font-size: 0.72rem;
  color: #64748b;
  margin-bottom: 8px;
}

.suggest-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.suggest-tag {
  border: 1px dashed #cbd5e1;
  background: #fff;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.72rem;
  color: #475569;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}

.suggest-tag:hover:not(:disabled) {
  border-color: #818cf8;
  color: #4338ca;
  background: #eef2ff;
}

.suggest-tag--added,
.suggest-tag:disabled {
  border-style: solid;
  border-color: #c7d2fe;
  background: #eef2ff;
  color: #6366f1;
  cursor: default;
  opacity: 0.85;
}

.radar-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 12px 14px;
  background: #f8fafc;
  border-radius: 12px;
}

.slider-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.slider-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.78rem;
  color: #64748b;
}

.slider-head strong {
  font-size: 0.84rem;
  font-weight: 700;
  color: var(--home-primary, #5b6adf);
  min-width: 28px;
  text-align: right;
}

.slider-field input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: linear-gradient(
    to right,
    var(--home-primary, #5b6adf) 0%,
    var(--home-primary, #5b6adf) var(--val, 50%),
    #e2e8f0 var(--val, 50%),
    #e2e8f0 100%
  );
  outline: none;
  cursor: pointer;
}

.slider-field input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--home-primary, #5b6adf);
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.15);
  cursor: grab;
}

.slider-field input[type="range"]::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--home-primary, #5b6adf);
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.15);
  cursor: grab;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
