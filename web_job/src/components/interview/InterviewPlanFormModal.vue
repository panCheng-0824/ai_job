<script setup>
/**
 * 题目大纲新增/编辑弹窗 — 统一外层滚动，基础信息与题目列表均可折叠。
 */
import { ref } from "vue";
import PlanBasicFormSection from "./PlanBasicFormSection.vue";
import PlanQuestionEditorCards from "./PlanQuestionEditorCards.vue";

defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: "create" },
  form: { type: Object, required: true },
  industryPath: { type: String, default: "" },
  error: { type: String, default: "" },
  success: { type: String, default: "" },
  saving: { type: Boolean, default: false },
  loading: { type: Boolean, default: false }
});

defineEmits(["close", "submit", "update:form"]);

/** 弹窗内容区滚动容器，供题目列表下滑加载哨兵使用 */
const formScrollRef = ref(null);
</script>

<template>
  <div v-if="visible" class="overlay" @click.self="$emit('close')">
    <div class="modal" role="dialog" aria-modal="true">
      <header class="modal-head">
        <div>
          <h2>{{ mode === "edit" ? "编辑大纲" : "新增题目大纲" }}</h2>
          <p v-if="mode === 'edit' && form.plan_id" class="plan-meta">
            ID {{ form.plan_id }}
            <template v-if="form.version != null"> · 当前 v{{ form.version }}</template>
            <template v-else> · 保存后将生成新版本</template>
          </p>
        </div>
        <button type="button" class="icon-btn" aria-label="关闭" @click="$emit('close')">×</button>
      </header>

      <form class="modal-form" @submit.prevent="$emit('submit')">
        <div ref="formScrollRef" class="form-scroll">
          <p v-if="success" class="success">{{ success }}</p>
          <p v-else-if="error" class="error">{{ error }}</p>

          <PlanBasicFormSection
            :form="form"
            :mode="mode"
            :industry-path="industryPath"
            @update:form="$emit('update:form', $event)"
          />

          <div v-if="loading" class="loading-box">加载题目中…</div>
          <PlanQuestionEditorCards
            v-else
            :questions="form.questions"
            :scroll-root="formScrollRef"
            @update:questions="$emit('update:form', { ...form, questions: $event })"
          />
        </div>

        <footer class="actions">
          <button type="button" class="plan-btn plan-btn-ghost" @click="$emit('close')">取消</button>
          <button type="submit" class="plan-btn plan-btn-primary" :disabled="saving || loading">
            {{ saving ? "保存中…" : mode === "edit" ? "编辑/保存" : "保存" }}
          </button>
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
  width: min(920px, 100%);
  max-height: 92vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid #eceff3;
  flex-shrink: 0;
}

.modal-head h2 {
  margin: 0;
  font-size: 1.05rem;
}

.plan-meta {
  margin: 4px 0 0;
  font-size: 0.76rem;
  color: #6b7280;
  font-family: ui-monospace, monospace;
}

.icon-btn {
  border: none;
  background: transparent;
  font-size: 1.4rem;
  cursor: pointer;
  color: #6b7280;
}

.modal-form {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.form-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 18px;
  display: grid;
  gap: 12px;
  align-content: start;
  -webkit-overflow-scrolling: touch;
}

.loading-box {
  text-align: center;
  color: #6b7280;
  font-size: 0.88rem;
  padding: 32px;
  border: 1px dashed #e5e7eb;
  border-radius: 12px;
}

.actions {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid #eceff3;
  background: #fff;
}

.plan-btn {
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  font-family: inherit;
}

.plan-btn-ghost {
  background: #f3f4f6;
  color: #374151;
}

.plan-btn-primary {
  background: #6366f1;
  color: #fff;
}

.plan-btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.error {
  color: #dc2626;
  font-size: 0.85rem;
  margin: 0;
}

.success {
  color: #15803d;
  font-size: 0.85rem;
  margin: 0;
  font-weight: 600;
}
</style>
