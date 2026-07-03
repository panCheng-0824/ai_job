<script setup>
/**
 * 学生画像编辑弹窗：桌面居中对话框，移动端底部抽屉；支持 ESC 关闭与滚动锁定。
 */
import { onBeforeUnmount, watch } from "vue";

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: "编辑" },
  subtitle: { type: String, default: "" },
  saving: { type: Boolean, default: false }
});

const emit = defineEmits(["close", "save"]);

function onKeydown(ev) {
  if (ev.key === "Escape" && props.open && !props.saving) {
    emit("close");
  }
}

watch(
  () => props.open,
  (open) => {
    if (typeof document === "undefined") return;
    document.body.style.overflow = open ? "hidden" : "";
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  if (typeof document !== "undefined") {
    document.body.style.overflow = "";
  }
});
</script>

<template>
  <Teleport to="body">
    <Transition name="profile-drawer">
      <div v-if="open" class="drawer-root" role="presentation">
        <button
          type="button"
          class="drawer-backdrop"
          aria-label="关闭"
          :disabled="saving"
          @click="emit('close')"
        />
        <div
          class="drawer-panel"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          @keydown="onKeydown"
        >
          <div class="drawer-handle" aria-hidden="true" />
          <header class="drawer-head">
            <div class="drawer-head-text">
              <h3>{{ title }}</h3>
              <p v-if="subtitle" class="drawer-subtitle">{{ subtitle }}</p>
            </div>
            <button
              type="button"
              class="drawer-close"
              aria-label="关闭"
              :disabled="saving"
              @click="emit('close')"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
              </svg>
            </button>
          </header>
          <div class="drawer-body">
            <slot />
          </div>
          <footer class="drawer-foot">
            <button type="button" class="btn-ghost" :disabled="saving" @click="emit('close')">取消</button>
            <button type="button" class="btn-primary" :disabled="saving" @click="emit('save')">
              <span v-if="saving" class="btn-spinner" aria-hidden="true" />
              {{ saving ? "保存中…" : "保存" }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-root {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 0;
}

.drawer-backdrop {
  position: absolute;
  inset: 0;
  border: none;
  background: rgba(15, 23, 42, 0.48);
  backdrop-filter: blur(4px);
  cursor: pointer;
}

.drawer-panel {
  position: relative;
  width: 100%;
  max-height: 92vh;
  background: #fff;
  border-radius: 20px 20px 0 0;
  display: flex;
  flex-direction: column;
  box-shadow: 0 -12px 40px rgba(15, 23, 42, 0.14);
}

.drawer-handle {
  width: 36px;
  height: 4px;
  margin: 10px auto 0;
  border-radius: 999px;
  background: #e2e8f0;
  flex-shrink: 0;
}

.drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px 12px;
  border-bottom: 1px solid #f1f5f9;
}

.drawer-head-text {
  min-width: 0;
}

.drawer-head h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.drawer-subtitle {
  margin: 4px 0 0;
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.45;
}

.drawer-close {
  flex-shrink: 0;
  border: none;
  background: #f1f5f9;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  cursor: pointer;
  color: #64748b;
  display: grid;
  place-items: center;
  transition: background 0.15s, color 0.15s;
}

.drawer-close:hover:not(:disabled) {
  background: #e2e8f0;
  color: #334155;
}

.drawer-body {
  padding: 16px 18px 8px;
  overflow-y: auto;
  flex: 1;
  overscroll-behavior: contain;
}

.drawer-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 18px calc(14px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid #f1f5f9;
  background: #fafbfc;
  border-radius: 0 0 20px 20px;
}

.btn-ghost {
  padding: 9px 18px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.btn-ghost:hover:not(:disabled) {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 20px;
  border-radius: 10px;
  border: none;
  background: var(--home-primary, #5b6adf);
  color: #fff;
  font-size: 0.84rem;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.92;
}

.btn-primary:active:not(:disabled) {
  transform: scale(0.98);
}

.btn-primary:disabled,
.btn-ghost:disabled,
.drawer-close:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 桌面端：居中对话框 */
@media (min-width: 640px) {
  .drawer-root {
    align-items: center;
    padding: 24px;
  }

  .drawer-panel {
    width: min(520px, 100%);
    max-height: min(88vh, 720px);
    border-radius: 16px;
    box-shadow: 0 24px 48px rgba(15, 23, 42, 0.18);
  }

  .drawer-handle {
    display: none;
  }

  .drawer-head {
    padding: 18px 20px 14px;
  }

  .drawer-body {
    padding: 4px 20px 12px;
  }

  .drawer-foot {
    padding: 14px 20px;
    border-radius: 0 0 16px 16px;
  }
}

/* 动画 */
.profile-drawer-enter-active,
.profile-drawer-leave-active {
  transition: opacity 0.22s ease;
}

.profile-drawer-enter-active .drawer-panel,
.profile-drawer-leave-active .drawer-panel {
  transition: transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}

.profile-drawer-enter-from,
.profile-drawer-leave-to {
  opacity: 0;
}

.profile-drawer-enter-from .drawer-panel,
.profile-drawer-leave-to .drawer-panel {
  transform: translateY(100%);
}

@media (min-width: 640px) {
  .profile-drawer-enter-from .drawer-panel,
  .profile-drawer-leave-to .drawer-panel {
    transform: translateY(16px) scale(0.97);
  }
}
</style>
