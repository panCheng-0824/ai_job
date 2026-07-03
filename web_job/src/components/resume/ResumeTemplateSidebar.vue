<script setup>
import { RESUME_TEMPLATES } from "../../modules/resume/templates";

const props = defineProps({
  modelValue: { type: String, required: true },
  collapsed: { type: Boolean, default: false }
});

const emit = defineEmits(["update:modelValue", "update:collapsed", "upload"]);

function selectTemplate(id) {
  if (id === props.modelValue) return;
  emit("update:modelValue", id);
}
</script>

<template>
  <aside
    class="resume-template-sidebar"
    :class="{ 'resume-template-sidebar--collapsed': collapsed }"
    aria-label="简历模板"
  >
    <div v-if="!collapsed" class="template-sidebar-head">
      <h2 class="template-sidebar-title">简历模板</h2>
      <button
        type="button"
        class="template-sidebar-toggle"
        aria-expanded="true"
        @click="emit('update:collapsed', true)"
      >
        收起
      </button>
    </div>

    <div v-if="collapsed" class="template-sidebar-collapsed">
      <button
        type="button"
        class="template-sidebar-expand"
        title="展开简历模板"
        @click="emit('update:collapsed', false)"
      >
        <span class="template-sidebar-expand-icon" aria-hidden="true">◀</span>
        <span class="template-sidebar-expand-label">模板</span>
      </button>
    </div>

    <div v-else class="template-sidebar-list">
      <button
        v-for="tpl in RESUME_TEMPLATES"
        :key="tpl.id"
        type="button"
        class="template-sidebar-card"
        :class="{ active: modelValue === tpl.id }"
        :style="{ '--tpl-accent': tpl.accent }"
        :aria-pressed="modelValue === tpl.id"
        @click="selectTemplate(tpl.id)"
      >
        <div class="template-sidebar-card-head">
          <strong>{{ tpl.name }}</strong>
          <span class="template-sidebar-badge">{{ tpl.badge }}</span>
        </div>
        <p class="template-sidebar-desc">{{ tpl.description }}</p>
      </button>

      <button type="button" class="template-sidebar-upload" @click="emit('upload')">
        <span class="template-sidebar-upload-icon" aria-hidden="true">↑</span>
        <strong>简历上传</strong>
        <span class="template-sidebar-upload-hint">支持 PDF / Word / 图片，识别后填入表单</span>
        <span class="template-sidebar-badge template-sidebar-badge--muted">自定义</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.resume-template-sidebar {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.resume-template-sidebar--collapsed {
  align-items: center;
}
.template-sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  flex-shrink: 0;
  width: 100%;
}
.template-sidebar-title {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: #334155;
  flex: 1;
  min-width: 0;
}
.template-sidebar-toggle {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}
.template-sidebar-toggle:hover {
  border-color: #c7d2fe;
  color: var(--home-primary, #5b6adf);
}
.template-sidebar-collapsed {
  display: flex;
  justify-content: center;
  width: 100%;
}
.template-sidebar-expand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 6px;
  border-radius: 10px;
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  background: var(--home-card-bg, #fff);
  box-shadow: var(--home-card-shadow, 0 4px 16px rgba(91, 106, 223, 0.06));
  cursor: pointer;
  color: #64748b;
  transition: border-color 0.15s, color 0.15s;
}
.template-sidebar-expand:hover {
  border-color: var(--home-primary, #5b6adf);
  color: var(--home-primary, #5b6adf);
}
.template-sidebar-expand-icon {
  font-size: 0.65rem;
  line-height: 1;
}
.template-sidebar-expand-label {
  font-size: 0.72rem;
  font-weight: 700;
  writing-mode: vertical-rl;
  letter-spacing: 0.12em;
}
.template-sidebar-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: auto;
  padding-right: 4px;
  flex: 1;
  min-height: 0;
}
.template-sidebar-card,
.template-sidebar-upload {
  width: 100%;
  text-align: left;
  border-radius: var(--home-radius, 14px);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  background: var(--home-card-bg, #fff);
  box-shadow: var(--home-card-shadow, 0 4px 16px rgba(91, 106, 223, 0.06));
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.12s;
}
.template-sidebar-card {
  padding: 14px 14px 12px;
}
.template-sidebar-card:hover {
  border-color: rgba(91, 106, 223, 0.28);
  transform: translateY(-1px);
}
.template-sidebar-card.active {
  border-color: var(--tpl-accent, var(--home-primary, #5b6adf));
  box-shadow:
    0 0 0 1px rgba(91, 106, 223, 0.22),
    0 8px 24px rgba(91, 106, 223, 0.12);
}
.template-sidebar-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.template-sidebar-card-head strong {
  font-size: 0.84rem;
  color: #1e293b;
  line-height: 1.35;
}
.template-sidebar-badge {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 700;
  color: #4338ca;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
}
.template-sidebar-badge--muted {
  color: #64748b;
  background: #f8fafc;
  border-color: #e2e8f0;
}
.template-sidebar-desc {
  margin: 0;
  font-size: 0.72rem;
  line-height: 1.45;
  color: #64748b;
}
.template-sidebar-upload {
  padding: 14px 12px;
  border-style: dashed;
  background: #fafbff;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  flex-shrink: 0;
}
.template-sidebar-upload:hover {
  border-color: var(--home-primary, #5b6adf);
  background: #f5f7ff;
}
.template-sidebar-upload-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #eef2ff;
  color: var(--home-primary, #5b6adf);
  font-size: 0.95rem;
  margin-bottom: 2px;
}
.template-sidebar-upload strong {
  font-size: 0.84rem;
  color: #334155;
}
.template-sidebar-upload-hint {
  font-size: 0.68rem;
  color: #94a3b8;
  line-height: 1.4;
}
</style>
