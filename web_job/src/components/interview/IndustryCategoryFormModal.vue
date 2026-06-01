<script setup>
/**
 * 行业分类新增/编辑弹窗表单。
 */
defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: "create" },
  form: { type: Object, required: true },
  level1Options: { type: Array, default: () => [] },
  error: { type: String, default: "" },
  saving: { type: Boolean, default: false }
});

defineEmits(["close", "submit", "update:form"]);
</script>

<template>
  <div v-if="visible" class="overlay" @click.self="$emit('close')">
    <div class="modal" role="dialog" aria-modal="true">
      <header class="modal-head">
        <h2>{{ mode === "edit" ? "编辑行业分类" : "新增行业分类" }}</h2>
        <button type="button" class="icon-btn" aria-label="关闭" @click="$emit('close')">×</button>
      </header>
      <form class="form" @submit.prevent="$emit('submit')">
        <p v-if="error" class="error">{{ error }}</p>
        <label class="field">
          <span>层级</span>
          <select
            :value="form.level"
            :disabled="mode === 'edit'"
            @change="$emit('update:form', { ...form, level: Number($event.target.value) })"
          >
            <option :value="1">一级类目</option>
            <option :value="2">二级类目（最终层级）</option>
          </select>
        </label>
        <label v-if="form.level === 2" class="field">
          <span>所属一级</span>
          <select
            :value="form.parent_id"
            :disabled="mode === 'edit'"
            @change="$emit('update:form', { ...form, parent_id: $event.target.value })"
          >
            <option value="" disabled>请选择</option>
            <option v-for="p in level1Options" :key="p.category_id" :value="p.category_id">
              {{ p.category_name }}
            </option>
          </select>
        </label>
        <label v-if="mode === 'create'" class="field">
          <span>分类 ID（可选）</span>
          <input
            :value="form.category_id"
            placeholder="留空则按编码自动生成"
            @input="$emit('update:form', { ...form, category_id: $event.target.value })"
          />
        </label>
        <label class="field">
          <span>编码 *</span>
          <input
            :value="form.category_code"
            placeholder="如 backend_dev"
            @input="$emit('update:form', { ...form, category_code: $event.target.value })"
          />
        </label>
        <label class="field">
          <span>名称 *</span>
          <input
            :value="form.category_name"
            @input="$emit('update:form', { ...form, category_name: $event.target.value })"
          />
        </label>
        <label class="field">
          <span>描述</span>
          <textarea
            rows="3"
            :value="form.description"
            @input="$emit('update:form', { ...form, description: $event.target.value })"
          />
        </label>
        <label class="field">
          <span>意图关键词</span>
          <input
            :value="form.intent_keywords"
            placeholder="逗号分隔"
            @input="$emit('update:form', { ...form, intent_keywords: $event.target.value })"
          />
        </label>
        <div class="checks">
          <label><input type="checkbox" :checked="form.enabled_for_intent" @change="$emit('update:form', { ...form, enabled_for_intent: $event.target.checked })" /> 参与意图识别</label>
          <label><input type="checkbox" :checked="form.enabled_for_classify" @change="$emit('update:form', { ...form, enabled_for_classify: $event.target.checked })" /> 参与大纲分类</label>
        </div>
        <label class="field">
          <span>排序</span>
          <input
            type="number"
            :value="form.sort_no"
            @input="$emit('update:form', { ...form, sort_no: Number($event.target.value) })"
          />
        </label>
        <label class="field">
          <span>状态</span>
          <select
            :value="form.status"
            @change="$emit('update:form', { ...form, status: $event.target.value })"
          >
            <option value="active">启用</option>
            <option value="disabled">停用</option>
          </select>
        </label>
        <footer class="actions">
          <button type="button" class="btn ghost" @click="$emit('close')">取消</button>
          <button type="submit" class="btn primary" :disabled="saving">{{ saving ? "保存中…" : "保存" }}</button>
        </footer>
      </form>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 14000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.modal {
  width: min(480px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
}
.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #eceff3;
}
.modal-head h2 {
  font-size: 1rem;
  margin: 0;
}
.icon-btn {
  border: none;
  background: transparent;
  font-size: 1.4rem;
  cursor: pointer;
  color: #6b7280;
}
.form {
  padding: 16px;
  display: grid;
  gap: 12px;
}
.field {
  display: grid;
  gap: 4px;
  font-size: 0.85rem;
}
.field span {
  color: #4b5563;
  font-weight: 600;
}
.field input,
.field textarea,
.field select {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 0.9rem;
}
.checks {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 0.85rem;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}
.btn {
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.88rem;
  cursor: pointer;
  border: none;
}
.btn.ghost {
  background: #f3f4f6;
  color: #374151;
}
.btn.primary {
  background: var(--primary-color, #6366f1);
  color: #fff;
}
.error {
  color: #dc2626;
  font-size: 0.85rem;
}
</style>
