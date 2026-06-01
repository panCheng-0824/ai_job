<script setup>
/**
 * 基础信息编辑表单 — 分组字段与标签实时预览。
 */
import { computed } from "vue";
import { parseModuleTags } from "../../modules/interview/planBasicMeta";

const props = defineProps({
  form: { type: Object, required: true },
  industryPath: { type: String, default: "" }
});

const emit = defineEmits(["update:form"]);

const tagList = computed(() => parseModuleTags(props.form?.module_tags));

function patch(partial) {
  emit("update:form", { ...props.form, ...partial });
}
</script>

<template>
  <div class="basic-body">
    <div v-if="industryPath" class="industry-bar">
      <span class="industry-label">绑定行业</span>
      <span class="industry-value">{{ industryPath }}</span>
    </div>

    <label class="field field-full">
      <span>标题 <em>*</em></span>
      <input
        :value="form.title"
        placeholder="如：Java 后端校招模拟面试"
        @input="patch({ title: $event.target.value })"
      />
    </label>

    <div class="field-row">
      <label class="field">
        <span>目标岗位</span>
        <input
          :value="form.target_role"
          placeholder="如：Java 开发工程师"
          @input="patch({ target_role: $event.target.value })"
        />
      </label>
      <label class="field">
        <span>状态</span>
        <select :value="form.status" @change="patch({ status: $event.target.value })">
          <option value="draft">草稿</option>
          <option value="published">已发布</option>
          <option value="archived">已归档</option>
        </select>
      </label>

    </div>

    <label class="field field-full">
      <span>适合人群</span>
      <textarea
          rows="2"
          :value="form.suitable_audience"
          placeholder="如：1-3 年经验"
          @input="patch({ suitable_audience: $event.target.value })"
      />
    </label>

    <label class="field field-full">
      <span>简介</span>
      <textarea
        rows="3"
        placeholder="描述本大纲的考察范围与使用场景"
        :value="form.introduction"
        @input="patch({ introduction: $event.target.value })"
      />
    </label>

    <label class="field field-full">
      <span>模块标签</span>
      <input
        :value="form.module_tags"
        placeholder="逗号分隔，如：项目经历, 算法基础, 系统设计"
        @input="patch({ module_tags: $event.target.value })"
      />
      <div v-if="tagList.length" class="tag-preview">
        <span v-for="t in tagList" :key="t" class="tag">{{ t }}</span>
      </div>
    </label>
  </div>
</template>

<style scoped>
.basic-body {
  padding: 14px;
  display: grid;
  gap: 12px;
  border-top: 1px solid #f1f5f9;
}

.industry-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #eef2ff;
  border-radius: 8px;
  font-size: 0.82rem;
}

.industry-label {
  font-weight: 700;
  color: #4338ca;
  flex-shrink: 0;
}

.industry-value {
  color: #3730a3;
  word-break: break-word;
}

.field-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 4px;
  font-size: 0.85rem;
}

.field-full {
  grid-column: 1 / -1;
}

.field span {
  color: #4b5563;
  font-weight: 600;
}

.field span em {
  color: #dc2626;
  font-style: normal;
}

.field input,
.field textarea,
.field select {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 0.9rem;
  font-family: inherit;
}

.field textarea {
  resize: vertical;
  min-height: 72px;
}

.tag-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.tag {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
}

@media (max-width: 720px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
