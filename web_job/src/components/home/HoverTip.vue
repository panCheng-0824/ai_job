<script setup>
/**
 * 轻量 CSS tooltip 包裹器：hover / focus-visible 时显示说明气泡。
 */
defineProps({
  tip: { type: String, required: true },
  /** top | bottom */
  place: { type: String, default: "top" }
});
</script>

<template>
  <span
    class="hover-tip"
    :class="`hover-tip--${place}`"
    :aria-label="tip"
    tabindex="0"
  >
    <slot />
    <span class="hover-tip-bubble" role="tooltip">{{ tip }}</span>
  </span>
</template>

<style scoped>
.hover-tip {
  position: relative;
  display: inline-flex;
  max-width: 100%;
  outline: none;
}

.hover-tip-bubble {
  position: absolute;
  left: 50%;
  z-index: 20;
  width: max-content;
  max-width: 200px;
  padding: 6px 10px;
  border-radius: 8px;
  background: #1e293b;
  color: #f8fafc;
  font-size: 0.68rem;
  font-weight: 500;
  line-height: 1.45;
  text-align: center;
  white-space: normal;
  pointer-events: none;
  opacity: 0;
  transform: translateX(-50%) translateY(4px) scale(0.96);
  transition: opacity 0.16s ease, transform 0.16s ease;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.22);
}

.hover-tip--top .hover-tip-bubble {
  bottom: calc(100% + 8px);
  transform: translateX(-50%) translateY(4px) scale(0.96);
}

.hover-tip--bottom .hover-tip-bubble {
  top: calc(100% + 8px);
  transform: translateX(-50%) translateY(-4px) scale(0.96);
}

.hover-tip:hover .hover-tip-bubble,
.hover-tip:focus-visible .hover-tip-bubble {
  opacity: 1;
  transform: translateX(-50%) translateY(0) scale(1);
}

.hover-tip--top:hover .hover-tip-bubble,
.hover-tip--top:focus-visible .hover-tip-bubble {
  transform: translateX(-50%) translateY(0) scale(1);
}

@media (prefers-reduced-motion: reduce) {
  .hover-tip-bubble {
    transition: none;
  }
}
</style>
