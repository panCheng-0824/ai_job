<script setup>
/** 岗位网格占位卡：空闲态「待匹配」；等待态带骨架闪烁。 */
defineProps({
  loading: { type: Boolean, default: false },
  /** 用于错峰动画（1–9） */
  stagger: { type: Number, default: 0 }
});
</script>

<template>
  <div
    class="job-placeholder"
    :class="{ 'job-placeholder--loading': loading }"
    :style="loading && stagger ? { '--stagger': `${stagger * 0.08}s` } : undefined"
    :aria-hidden="loading ? undefined : 'true'"
    :aria-busy="loading ? 'true' : undefined"
  >
    <template v-if="loading">
      <div class="job-placeholder-skeleton">
        <span class="sk-row sk-row--title" />
        <span class="sk-row sk-row--meta" />
        <span class="sk-row sk-row--desc" />
        <span class="sk-row sk-row--desc sk-row--short" />
        <div class="sk-row sk-row--footer">
          <span class="sk-chip" />
          <span class="sk-chip sk-chip--sm" />
        </div>
      </div>
    </template>
    <div v-else class="job-placeholder-inner">
      <span class="job-placeholder-icon">+</span>
      <span class="job-placeholder-text">待匹配岗位</span>
    </div>
  </div>
</template>

<style scoped>
.job-placeholder {
  border: 1px dashed rgba(91, 106, 223, 0.22);
  border-radius: 14px;
  background: repeating-linear-gradient(
    -45deg,
    rgba(248, 250, 252, 0.9),
    rgba(248, 250, 252, 0.9) 8px,
    rgba(241, 245, 249, 0.9) 8px,
    rgba(241, 245, 249, 0.9) 16px
  );
  min-height: 168px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.job-placeholder--loading {
  border-style: solid;
  border-color: rgba(99, 102, 241, 0.14);
  background: #fff;
  align-items: stretch;
  padding: 14px 12px;
  animation: card-breathe 2.2s ease-in-out infinite;
  animation-delay: var(--stagger, 0s);
}
@keyframes card-breathe {
  0%,
  100% {
    box-shadow: 0 0 0 rgba(99, 102, 241, 0);
  }
  50% {
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.08);
  }
}
.job-placeholder-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #cbd5e1;
  user-select: none;
}
.job-placeholder-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px dashed #cbd5e1;
  display: grid;
  place-items: center;
  font-size: 1rem;
  line-height: 1;
}
.job-placeholder-text {
  font-size: 0.72rem;
  font-weight: 500;
}
.job-placeholder-skeleton {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sk-row {
  display: block;
  height: 10px;
  border-radius: 6px;
  background: linear-gradient(90deg, #e8ecff 0%, #f8fafc 45%, #e8ecff 100%);
  background-size: 200% 100%;
  animation: sk-shimmer 1.35s ease-in-out infinite;
  animation-delay: var(--stagger, 0s);
}
.sk-row--title {
  height: 14px;
  width: 78%;
}
.sk-row--meta {
  width: 52%;
}
.sk-row--desc {
  width: 100%;
}
.sk-row--short {
  width: 86%;
}
.sk-row--footer {
  display: flex;
  gap: 6px;
  margin-top: 4px;
  height: auto;
  background: none;
  animation: none;
}
.sk-chip {
  width: 48px;
  height: 22px;
  border-radius: 999px;
  background: linear-gradient(90deg, #e0e7ff 0%, #f1f5f9 50%, #e0e7ff 100%);
  background-size: 200% 100%;
  animation: sk-shimmer 1.35s ease-in-out infinite;
  animation-delay: var(--stagger, 0s);
}
.sk-chip--sm {
  width: 36px;
}
@keyframes sk-shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
</style>
