<script setup>
import { ref } from "vue";
import ResumeExportMenu from "./ResumeExportMenu.vue";

defineProps({
  name: { type: String, default: "同学" },
  subtitle: { type: String, default: "" },
  phone: { type: String, default: "" },
  email: { type: String, default: "" },
  avatarUrl: { type: String, default: "" },
  versionOpen: { type: Boolean, default: false },
  aiOpen: { type: Boolean, default: false },
  saving: { type: Boolean, default: false }
});

const emit = defineEmits(["change-avatar", "version-preview", "export", "ai-optimize"]);
// export 事件携带格式：pdf | docx | json

const fileInputRef = ref(null);

function openAvatarPicker() {
  fileInputRef.value?.click();
}

function onAvatarFileChange(ev) {
  const file = ev.target?.files?.[0];
  if (!file) return;
  emit("change-avatar", file);
  ev.target.value = "";
}
</script>

<template>
  <section class="resume-editor-hero">
    <div class="hero-profile">
      <button type="button" class="hero-avatar-btn" title="修改头像" @click="openAvatarPicker">
        <img v-if="avatarUrl" :src="avatarUrl" alt="" class="hero-avatar-img" />
        <span v-else class="hero-avatar-fallback">{{ (name || "学").slice(0, 1) }}</span>
      </button>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*"
        class="sr-only"
        @change="onAvatarFileChange"
      />

      <div class="hero-meta">
        <h2 class="hero-name">{{ name || "同学" }}</h2>
        <p v-if="subtitle" class="hero-subtitle">{{ subtitle }}</p>
        <div class="hero-contacts">
          <span class="hero-contact">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M6.5 3h2l1.2 5.2a1 1 0 0 1-.27.95l-1.9 1.9a12.5 12.5 0 0 0 5.6 5.6l1.9-1.9a1 1 0 0 1 .95-.27L19 15.5v2a2 2 0 0 1-2.18 2A16 16 0 0 1 3 6.18 2 2 0 0 1 5 4h1.5Z" stroke="currentColor" stroke-width="1.5" />
            </svg>
            {{ phone || "未填写手机" }}
          </span>
          <span class="hero-contact">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" stroke-width="1.5" />
              <path d="m3 7 9 6 9-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
            </svg>
            {{ email || "未填写邮箱" }}
          </span>
        </div>
      </div>
    </div>

    <div class="hero-actions" role="toolbar" aria-label="简历操作">
      <button type="button" class="hero-action-btn" @click="openAvatarPicker">修改头像</button>
      <button
        type="button"
        class="hero-action-btn"
        :class="{ 'hero-action-btn--active': versionOpen }"
        @click="emit('version-preview')"
      >
        版本预览
      </button>
      <ResumeExportMenu @export="(format) => emit('export', format)" />
      <button
        type="button"
        class="hero-action-btn hero-action-btn--primary"
        :class="{ 'hero-action-btn--active': aiOpen }"
        :disabled="saving"
        @click="emit('ai-optimize')"
      >
        AI 优化
      </button>
    </div>
  </section>
</template>

<style scoped>
.resume-editor-hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px 20px;
  flex-wrap: wrap;
  padding: 12px 20px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #fff;
}
.hero-profile {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  flex: 1 1 280px;
}
.hero-avatar-btn {
  flex-shrink: 0;
  width: 76px;
  height: 76px;
  padding: 0;
  border: 2px solid #eef2ff;
  border-radius: 50%;
  background: linear-gradient(145deg, #eef2ff, #e0e7ff);
  cursor: pointer;
  overflow: hidden;
}
.hero-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.hero-avatar-fallback {
  display: inline-flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--home-primary, #5b6adf);
}
.hero-meta {
  min-width: 0;
}
.hero-name {
  margin: 0;
  font-size: clamp(1.25rem, 2vw, 1.5rem);
  font-weight: 800;
  color: #0f172a;
  line-height: 1.25;
}
.hero-subtitle {
  margin: 8px 0 0;
  font-size: 0.82rem;
  color: #64748b;
  line-height: 1.45;
}
.hero-contacts {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  margin-top: 10px;
}
.hero-contact {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  color: #475569;
}
.hero-contact svg {
  width: 14px;
  height: 14px;
  color: #94a3b8;
  flex-shrink: 0;
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-shrink: 0;
}
.hero-action-btn {
  padding: 8px 14px;
  min-width: 96px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s, box-shadow 0.15s;
  white-space: nowrap;
}
.hero-action-btn:hover:not(:disabled) {
  border-color: #c7d2fe;
  color: var(--home-primary, #5b6adf);
}
.hero-action-btn--active {
  border-color: #c7d2fe;
  background: #eef2ff;
  color: var(--home-primary, #5b6adf);
}
.hero-action-btn--primary {
  border-color: transparent;
  background: linear-gradient(135deg, #6366f1 0%, #5b6adf 52%, #7c3aed 100%);
  color: #fff;
  box-shadow: 0 6px 16px rgba(91, 106, 223, 0.28);
}
.hero-action-btn--primary:hover:not(:disabled),
.hero-action-btn--primary.hero-action-btn--active {
  color: #fff;
  filter: brightness(1.03);
}
.hero-action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}
@media (max-width: 720px) {
  .hero-actions {
    width: 100%;
    justify-content: stretch;
  }
  .hero-action-btn {
    flex: 1 1 calc(50% - 4px);
    min-width: 0;
  }
}
</style>
