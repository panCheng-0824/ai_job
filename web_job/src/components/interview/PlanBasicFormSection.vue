<script setup>
/**
 * 大纲基础信息编辑区 — 可折叠，收起时摘要、展开时分组表单。
 */
import { computed, ref, watch } from "vue";
import { parseModuleTags, planStatusMeta } from "../../modules/interview/planBasicMeta";
import PlanBasicFormFields from "./PlanBasicFormFields.vue";
import PlanBasicFormSummary from "./PlanBasicFormSummary.vue";

const props = defineProps({
  form: { type: Object, required: true },
  industryPath: { type: String, default: "" },
  mode: { type: String, default: "create" }
});

const emit = defineEmits(["update:form"]);

const basicOpen = ref(true);

watch(
  () => [props.mode, props.form?.questions?.length],
  ([mode, qLen]) => {
    basicOpen.value = mode !== "edit" || (qLen || 0) <= 6;
  },
  { immediate: true }
);

const status = computed(() => planStatusMeta(props.form?.status));
const tagList = computed(() => parseModuleTags(props.form?.module_tags));

const summaryLine = computed(() => {
  const parts = [];
  if (props.form?.target_role) parts.push(props.form.target_role);
  if (props.industryPath) parts.push(props.industryPath);
  if (tagList.value.length) parts.push(`${tagList.value.length} 个标签`);
  return parts.join(" · ") || "点击展开填写基础信息";
});
</script>

<template>
  <section class="basic-section">
    <button type="button" class="section-toggle" @click="basicOpen = !basicOpen">
      <div class="toggle-main">
        <span class="toggle-title">基础信息</span>
        <span v-if="!basicOpen" class="toggle-hint">{{ form.title || "未填写标题" }}</span>
      </div>
      <span class="toggle-icon">{{ basicOpen ? "▾" : "▸" }}</span>
    </button>

    <PlanBasicFormSummary
      v-if="!basicOpen"
      :title="form.title"
      :summary-line="summaryLine"
      :introduction="form.introduction"
      :tags="tagList"
      :status-label="status.label"
      :status-tone="status.tone"
    />

    <PlanBasicFormFields
      v-show="basicOpen"
      :form="form"
      :industry-path="industryPath"
      @update:form="emit('update:form', $event)"
    />
  </section>
</template>

<style scoped>
.basic-section {
  border: 1px solid #eceff3;
  border-radius: 12px;
  background: #fff;
}

.section-toggle {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: none;
  background: #f8fafc;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}

.toggle-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toggle-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: #374151;
}

.toggle-hint {
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
</style>
