<script setup>
/**
 * 题目详情抽屉 — 右侧滑出，支持上一题/下一题切换与键盘导航。
 */
import { computed, onUnmounted, watch } from "vue";
import PlanQuestionDetailBody from "./PlanQuestionDetailBody.vue";

const props = defineProps({
  visible: { type: Boolean, default: false },
  question: { type: Object, default: null },
  index: { type: Number, default: 0 },
  total: { type: Number, default: 0 }
});

const emit = defineEmits(["close", "prev", "next"]);

const seqLabel = computed(() => {
  const seq = props.question?.seq_no ?? props.index;
  return typeof seq === "number" ? seq + 1 : props.index + 1;
});

const progressPct = computed(() => {
  if (!props.total) return 0;
  return Math.min(100, Math.round(((props.index + 1) / props.total) * 100));
});

const hasPrev = computed(() => props.index > 0);
const hasNext = computed(() => props.total > 0 && props.index < props.total - 1);

function onKeydown(e) {
  if (!props.visible) return;
  if (e.key === "Escape") {
    emit("close");
    return;
  }
  if (e.key === "ArrowLeft" && hasPrev.value) {
    e.preventDefault();
    emit("prev");
  }
  if (e.key === "ArrowRight" && hasNext.value) {
    e.preventDefault();
    emit("next");
  }
}

function lockBodyScroll(lock) {
  if (typeof document === "undefined") return;
  document.body.style.overflow = lock ? "hidden" : "";
}

watch(
  () => props.visible,
  (open) => {
    lockBodyScroll(open);
    if (open) globalThis.addEventListener("keydown", onKeydown);
    else globalThis.removeEventListener("keydown", onKeydown);
  },
  { immediate: true }
);

onUnmounted(() => {
  lockBodyScroll(false);
  globalThis.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible && question" class="drawer-overlay" @click.self="emit('close')">
        <Transition name="slide" appear>
          <aside
            v-if="visible && question"
            class="drawer"
            role="dialog"
            aria-modal="true"
            :aria-label="`第 ${seqLabel} 题详情`"
          >
            <header class="drawer-head">
              <div class="head-main">
                <p class="head-kicker">题目详情</p>
                <div class="head-row">
                  <span class="q-badge">Q{{ seqLabel }}</span>
                  <span v-if="total" class="q-progress">{{ index + 1 }} / {{ total }}</span>
                </div>
                <p v-if="question.question_id" class="q-id">{{ question.question_id }}</p>
              </div>
              <button type="button" class="close-btn" aria-label="关闭" @click="emit('close')">
                ✕
              </button>
              <div class="progress-bar" :style="{ width: `${progressPct}%` }" />
            </header>

            <div class="drawer-scroll">
              <Transition name="content" mode="out-in">
                <PlanQuestionDetailBody :key="question.iq_row_id || question.question_id || index" :question="question" />
              </Transition>
            </div>

            <footer v-if="total > 1" class="drawer-foot">
              <button type="button" class="nav-btn" :disabled="!hasPrev" @click="emit('prev')">
                ← 上一题
              </button>
              <span class="foot-meta">{{ index + 1 }} / {{ total }}</span>
              <button type="button" class="nav-btn nav-btn-primary" :disabled="!hasNext" @click="emit('next')">
                下一题 →
              </button>
            </footer>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 15000;
  background: rgba(15, 23, 42, 0.48);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: flex-end;
}

.drawer {
  position: relative;
  width: min(520px, 100%);
  height: 100vh;
  background: #f8fafc;
  box-shadow: -12px 0 40px rgba(15, 23, 42, 0.14);
  display: flex;
  flex-direction: column;
}

.drawer-head {
  position: relative;
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 18px 18px 16px;
  background: linear-gradient(180deg, #fff 0%, #fafbff 100%);
  border-bottom: 1px solid #eceff3;
}

.head-kicker {
  margin: 0 0 6px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #6366f1;
  text-transform: uppercase;
}

.head-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.q-badge {
  font-size: 0.88rem;
  font-weight: 800;
  color: #4338ca;
  background: #eef2ff;
  padding: 5px 12px;
  border-radius: 999px;
}

.q-progress {
  font-size: 0.82rem;
  font-weight: 600;
  color: #6b7280;
}

.q-id {
  margin: 8px 0 0;
  font-size: 0.72rem;
  color: #9ca3af;
  font-family: ui-monospace, monospace;
}

.close-btn {
  border: none;
  background: #fff;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  font-size: 0.95rem;
  cursor: pointer;
  color: #6b7280;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  border: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.close-btn:hover {
  background: #f9fafb;
  color: #374151;
}

.progress-bar {
  position: absolute;
  left: 0;
  bottom: 0;
  height: 3px;
  background: linear-gradient(90deg, #6366f1, #818cf8);
  transition: width 0.25s ease;
}

.drawer-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 18px 20px;
  -webkit-overflow-scrolling: touch;
}

.drawer-foot {
  flex-shrink: 0;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0px));
  background: #fff;
  border-top: 1px solid #eceff3;
}

.nav-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  font-family: inherit;
}

.nav-btn:last-child {
  justify-self: end;
}

.nav-btn-primary {
  background: #6366f1;
  border-color: #6366f1;
  color: #fff;
}

.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.foot-meta {
  font-size: 0.78rem;
  color: #9ca3af;
  text-align: center;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

.content-enter-active,
.content-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.content-enter-from {
  opacity: 0;
  transform: translateX(12px);
}

.content-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}

@media (max-width: 640px) {
  .drawer {
    width: 100%;
  }

  .drawer-foot {
    grid-template-columns: 1fr 1fr;
  }

  .foot-meta {
    display: none;
  }

  .nav-btn:last-child {
    justify-self: stretch;
  }
}
</style>
