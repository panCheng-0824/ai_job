<script setup>
/**
 * 用户消息中的上下文引用卡片（岗位 / 企业 / 简历）。
 */
defineProps({
  card: { type: Object, required: true },
  compact: { type: Boolean, default: false },
  removable: { type: Boolean, default: false },
  /** 拖入后正在请求详情接口 */
  loading: { type: Boolean, default: false }
});

defineEmits(["remove"]);

const variantClass = {
  job: "ctx-ref--job",
  company: "ctx-ref--company",
  resume: "ctx-ref--resume",
  fav: "ctx-ref--job",
  fol: "ctx-ref--company"
};

function cardClass(card) {
  const t = card?.type || card?.variant || "job";
  return variantClass[t] || "ctx-ref--job";
}

function badgeLabel(card) {
  if (card.type === "resume" || card.variant === "resume") return "简历";
  if (card.type === "company" || card.variant === "fol") return "企业";
  return "岗位";
}
</script>

<template>
  <div
    class="ctx-ref"
    :class="[
      cardClass(card),
      compact ? 'ctx-ref--compact' : '',
      loading ? 'ctx-ref--loading' : ''
    ]"
    :aria-busy="loading ? 'true' : 'false'"
  >
    <span v-if="loading" class="ctx-ref-spinner" aria-hidden="true" />
    <span class="ctx-ref-badge">{{ badgeLabel(card) }}</span>
    <div class="ctx-ref-body">
      <span class="ctx-ref-title">{{ card.title || card.ref_id }}</span>
      <span v-if="card.subtitle || loading" class="ctx-ref-sub">
        {{ loading && !card.subtitle ? "正在加载详情…" : card.subtitle }}
      </span>
    </div>
    <button
      v-if="removable"
      type="button"
      class="ctx-ref-remove"
      :title="loading ? '取消加载并移除' : '移除'"
      :aria-label="loading ? '取消加载并移除' : '移除'"
      @click.stop="$emit('remove')"
    >
      ×
    </button>
  </div>
</template>

<style scoped>
.ctx-ref {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.25);
  background: #fff;
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}
.ctx-ref--compact {
  padding: 6px 8px;
}
.ctx-ref--loading {
  border-color: rgba(99, 102, 241, 0.55);
  animation: ctx-ref-pulse 1.4s ease-in-out infinite;
}
.ctx-ref--loading::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    105deg,
    transparent 0%,
    rgba(255, 255, 255, 0.55) 45%,
    transparent 90%
  );
  transform: translateX(-120%);
  animation: ctx-ref-shimmer 1.2s ease-in-out infinite;
  pointer-events: none;
}
@keyframes ctx-ref-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.12);
  }
  50% {
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.18);
  }
}
@keyframes ctx-ref-shimmer {
  100% {
    transform: translateX(120%);
  }
}
.ctx-ref-spinner {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  margin-top: 2px;
  border: 2px solid rgba(99, 102, 241, 0.25);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: ctx-ref-spin 0.75s linear infinite;
}
@keyframes ctx-ref-spin {
  to {
    transform: rotate(360deg);
  }
}
.ctx-ref--job {
  border-color: rgba(245, 158, 11, 0.45);
  background: linear-gradient(145deg, #fffbeb, #fff7ed);
}
.ctx-ref--company {
  border-color: rgba(16, 185, 129, 0.4);
  background: linear-gradient(145deg, #ecfdf5, #f0fdf4);
}
.ctx-ref--resume {
  border-color: rgba(99, 102, 241, 0.4);
  background: linear-gradient(145deg, #eef2ff, #f5f3ff);
}
.ctx-ref-badge {
  flex-shrink: 0;
  font-size: 0.65rem;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  color: #374151;
}
.ctx-ref-body {
  min-width: 0;
  flex: 1;
}
.ctx-ref-title {
  display: block;
  font-size: 0.82rem;
  font-weight: 700;
  color: #111827;
  line-height: 1.35;
  word-break: break-word;
}
.ctx-ref-sub {
  display: block;
  margin-top: 2px;
  font-size: 0.72rem;
  color: #6b7280;
  line-height: 1.35;
  word-break: break-word;
}
.ctx-ref--loading .ctx-ref-sub {
  color: #6366f1;
  font-style: italic;
}
.ctx-ref-remove {
  flex-shrink: 0;
  border: none;
  background: rgba(0, 0, 0, 0.06);
  color: #6b7280;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  position: relative;
  z-index: 1;
}
.ctx-ref-remove:hover {
  background: rgba(220, 38, 38, 0.12);
  color: #dc2626;
}
</style>
