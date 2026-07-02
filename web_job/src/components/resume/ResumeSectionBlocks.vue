<script setup>
import { newSectionItem } from "../../modules/resume/sectionsModel";

const props = defineProps({
  sectionKey: { type: String, required: true },
  items: { type: Array, required: true },
  hint: { type: String, default: "" },
  placeholder: { type: String, default: "" },
  rows: { type: Number, default: 5 },
  allowMultiple: { type: Boolean, default: true },
  entryLabel: { type: String, default: "条" },
  accent: { type: String, default: "#4f46e5" },
  studioMode: { type: Boolean, default: false }
});

const emit = defineEmits(["update:items"]);

function patch(next) {
  emit("update:items", next);
}

function updateItem(index, field, value) {
  const next = props.items.map((item, i) =>
    i === index ? { ...item, [field]: value } : item
  );
  patch(next);
}

function addItem() {
  patch([...props.items, newSectionItem()]);
}

function removeItem(index) {
  if (props.items.length <= 1) {
    patch([newSectionItem()]);
    return;
  }
  patch(props.items.filter((_, i) => i !== index));
}

function moveItem(index, dir) {
  const j = index + dir;
  if (j < 0 || j >= props.items.length) return;
  const next = [...props.items];
  const t = next[index];
  next[index] = next[j];
  next[j] = t;
  patch(next);
}
</script>

<template>
  <div class="section-blocks" :class="{ 'section-blocks--studio': studioMode }" :style="{ '--sec-accent': accent }">
    <div class="section-blocks-head">
      <h3 class="section-label">{{ sectionKey }}</h3>
      <button
        v-if="allowMultiple"
        type="button"
        class="btn-add-entry"
        @click="addItem"
      >
        {{ studioMode ? "添加" : `+ 添加${entryLabel}` }}
      </button>
    </div>
    <p v-if="hint && !studioMode" class="section-hint">{{ hint }}</p>

    <div
      v-for="(item, index) in items"
      :key="item.id"
      class="entry-card"
      :class="{ 'entry-card--solo': !allowMultiple }"
    >
      <div v-if="allowMultiple" class="entry-card-toolbar">
        <span class="entry-index">{{ entryLabel }} {{ index + 1 }}</span>
        <div class="entry-actions">
          <button
            type="button"
            class="entry-mini"
            :disabled="index === 0"
            title="上移"
            @click="moveItem(index, -1)"
          >
            ↑
          </button>
          <button
            type="button"
            class="entry-mini"
            :disabled="index === items.length - 1"
            title="下移"
            @click="moveItem(index, 1)"
          >
            ↓
          </button>
          <button type="button" class="entry-mini danger" title="删除" @click="removeItem(index)">
            删除
          </button>
        </div>
      </div>
      <label v-if="allowMultiple" class="field field-wide entry-title-field">
        <span>小标题（可选）</span>
        <input
          :value="item.title"
          placeholder="例如：XX公司实习、校级项目"
          @input="updateItem(index, 'title', $event.target.value)"
        />
      </label>
      <label class="field field-wide">
        <span v-if="!allowMultiple">内容</span>
        <textarea
          :value="item.body"
          :rows="rows"
          :placeholder="placeholder"
          @input="updateItem(index, 'body', $event.target.value)"
        />
      </label>
    </div>
  </div>
</template>

<style scoped>
.section-blocks {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px dashed #e8ecf1;
}
.section-blocks:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}
.section-blocks-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.section-blocks--studio {
  margin-bottom: 0;
  padding: 0 0 18px;
  border-top: 1px solid #eef2f6;
  border-bottom: none;
}
.section-blocks--studio .section-blocks-head {
  margin-bottom: 12px;
  padding: 10px 22px;
  background: linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #eef2f6;
}
.section-blocks--studio .section-label {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #1e293b;
}
.section-blocks--studio .entry-card--solo {
  margin: 0 22px;
}
.section-blocks--studio .btn-add-entry {
  border-color: #e2e8f0;
  background: #fff;
  color: #64748b;
  font-weight: 600;
  font-size: 0.76rem;
  padding: 4px 12px;
}
.section-blocks--studio .field span {
  font-size: 0.74rem;
  color: #94a3b8;
}
.section-blocks--studio .field input,
.section-blocks--studio .field textarea {
  border: none;
  border-bottom: 1px solid #e8ecf4;
  border-radius: 0;
  padding: 6px 0;
  background: transparent;
}
.section-blocks--studio .field input:focus,
.section-blocks--studio .field textarea:focus {
  outline: none;
  border-bottom-color: var(--sec-accent);
}
.section-label {
  font-weight: 600;
  font-size: 0.95rem;
  color: #1e293b;
}
.section-hint {
  margin: 0 0 10px;
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.4;
}
.btn-add-entry {
  flex-shrink: 0;
  padding: 5px 12px;
  font-size: 0.78rem;
  font-weight: 600;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--sec-accent) 40%, #e5e7eb);
  background: color-mix(in srgb, var(--sec-accent) 8%, #fff);
  color: var(--sec-accent);
  cursor: pointer;
}
.btn-add-entry:hover {
  background: color-mix(in srgb, var(--sec-accent) 14%, #fff);
}
.entry-card {
  background: #fafbff;
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
}
.entry-card--solo {
  background: transparent;
  border: none;
  padding: 0;
  margin-bottom: 0;
}
.entry-card-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.entry-index {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--sec-accent);
}
.entry-actions {
  display: flex;
  gap: 6px;
}
.entry-mini {
  font-size: 0.72rem;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background: #fff;
  cursor: pointer;
}
.entry-mini:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.entry-mini.danger {
  color: #dc2626;
  border-color: #fecaca;
}
.entry-title-field {
  margin-bottom: 8px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field span {
  font-size: 0.78rem;
  color: var(--text-muted, #64748b);
}
.field input,
.field textarea {
  width: 100%;
  border: 1px solid #dbe1ea;
  border-radius: 10px;
  padding: 9px 10px;
  font-size: 0.88rem;
  font-family: inherit;
}
.field textarea {
  resize: vertical;
  min-height: 72px;
}
.field-wide {
  width: 100%;
}
</style>
