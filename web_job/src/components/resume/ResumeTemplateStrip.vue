<script setup>
import { RESUME_TEMPLATES } from "../../modules/resume/templates";

defineProps({
  modelValue: { type: String, required: true }
});

const emit = defineEmits(["update:modelValue"]);
</script>

<template>
  <div class="template-strip" role="tablist" aria-label="简历模板">
    <button
      v-for="tpl in RESUME_TEMPLATES"
      :key="tpl.id"
      type="button"
      class="template-strip-item"
      :class="{ active: modelValue === tpl.id }"
      :style="{ '--tpl-accent': tpl.accent }"
      :aria-selected="modelValue === tpl.id"
      @click="emit('update:modelValue', tpl.id)"
    >
      <span class="template-strip-name">{{ tpl.name }}</span>
      <span class="template-strip-badge">{{ tpl.badge }}</span>
    </button>
  </div>
</template>

<style scoped>
.template-strip {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 4px 2px 10px;
  scrollbar-width: thin;
}
.template-strip-item {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.template-strip-item:hover {
  border-color: #c7d2fe;
}
.template-strip-item.active {
  border-color: var(--tpl-accent, var(--home-primary, #5b6adf));
  background: #eef2ff;
}
.template-strip-name {
  font-size: 0.78rem;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
}
.template-strip-badge {
  font-size: 0.62rem;
  font-weight: 700;
  color: #6366f1;
  white-space: nowrap;
}
</style>
