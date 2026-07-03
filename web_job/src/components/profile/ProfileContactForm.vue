<script setup>
import { computed, reactive, watch } from "vue";

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  avatarUrl: { type: String, default: "" }
});

const form = reactive({
  phone: "",
  email: "",
  campus_experience: ""
});

const campusLen = computed(() => form.campus_experience.length);
const CAMPUS_MAX = 500;

watch(
  () => props.modelValue,
  (v) => {
    form.phone = v?.phone || "";
    form.email = v?.email || "";
    form.campus_experience = v?.campus_experience || "";
  },
  { immediate: true, deep: true }
);

function getPayload() {
  return {
    phone: form.phone.trim(),
    email: form.email.trim(),
    campus_experience: form.campus_experience.trim().slice(0, CAMPUS_MAX)
  };
}

defineExpose({ getPayload });
</script>

<template>
  <div class="form-stack">
    <div class="form-notice">
      <span class="form-notice-icon" aria-hidden="true">ℹ️</span>
      <p>学籍字段（学号、专业、绩点等）来自学校系统不可改。头像请点击页面上方头像区域上传。</p>
    </div>

    <section class="form-section">
      <h4 class="form-section-title">联系方式</h4>
      <div v-if="avatarUrl" class="avatar-preview">
        <img :src="avatarUrl" alt="" />
        <div>
          <strong>当前头像</strong>
          <span>如需更换，请关闭窗口后点击页头头像</span>
        </div>
      </div>
      <div class="field-row">
        <label class="field">
          <span>手机</span>
          <input v-model="form.phone" type="tel" placeholder="请输入手机号" autocomplete="tel" />
        </label>
        <label class="field">
          <span>邮箱</span>
          <input v-model="form.email" type="email" placeholder="请输入邮箱" autocomplete="email" />
        </label>
      </div>
    </section>

    <section class="form-section">
      <h4 class="form-section-title">校园经历补充</h4>
      <p class="form-section-desc">官方奖惩记录仍只读展示，此处可补充社团、实习、项目等经历。</p>
      <label class="field">
        <span class="sr-only">校园经历补充</span>
        <textarea
          v-model="form.campus_experience"
          rows="5"
          :maxlength="CAMPUS_MAX"
          placeholder="例如：担任学生会技术部部长，组织 3 场校园招聘宣讲；暑期在某公司完成 Java 后端实习…"
        />
        <span class="field-counter" :class="{ 'field-counter--warn': campusLen >= CAMPUS_MAX * 0.9 }">
          {{ campusLen }} / {{ CAMPUS_MAX }}
        </span>
      </label>
    </section>
  </div>
</template>

<style scoped>
.form-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-notice {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 11px 13px;
  background: #f0f4ff;
  border: 1px solid #e0e7ff;
  border-radius: 12px;
}

.form-notice-icon {
  flex-shrink: 0;
  font-size: 0.9rem;
  line-height: 1.4;
}

.form-notice p {
  margin: 0;
  font-size: 0.76rem;
  color: #475569;
  line-height: 1.55;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-section-title {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 700;
  color: #334155;
}

.form-section-desc {
  margin: -4px 0 0;
  font-size: 0.74rem;
  color: #94a3b8;
  line-height: 1.45;
}

.avatar-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 12px;
}

.avatar-preview img {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #e2e8f0;
}

.avatar-preview strong {
  display: block;
  font-size: 0.78rem;
  color: #334155;
  margin-bottom: 2px;
}

.avatar-preview span {
  font-size: 0.72rem;
  color: #94a3b8;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}

.field span {
  font-size: 0.76rem;
  font-weight: 600;
  color: #475569;
}

.field input,
.field textarea {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.88rem;
  color: #0f172a;
  font-family: inherit;
  background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.field input::placeholder,
.field textarea::placeholder {
  color: #cbd5e1;
}

.field input:focus,
.field textarea:focus {
  outline: none;
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15);
}

.field textarea {
  resize: vertical;
  min-height: 120px;
  line-height: 1.55;
}

.field-counter {
  align-self: flex-end;
  font-size: 0.68rem;
  color: #94a3b8;
}

.field-counter--warn {
  color: #f59e0b;
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

@media (max-width: 480px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
