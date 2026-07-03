<script setup>
/**
 * 面试官动态呈现 — 阶段一：呼吸待机 / 说话声波 / 聆听光环 / 思考脉冲
 */
defineProps({
  state: {
    type: String,
    default: "idle",
    validator: (v) => ["idle", "listening", "speaking", "thinking"].includes(v)
  },
  size: {
    type: String,
    default: "main",
    validator: (v) => ["main", "pip"].includes(v)
  },
  showMeta: { type: Boolean, default: true },
  statusText: { type: String, default: "" }
});
</script>

<template>
  <div
    class="presence"
    :class="[`presence--${state}`, `presence--${size}`]"
    role="img"
    :aria-label="statusText || 'AI 面试官'"
  >
    <div class="presence-bg" aria-hidden="true" />
    <div class="presence-ring presence-ring--outer" aria-hidden="true" />
    <div class="presence-ring presence-ring--inner" aria-hidden="true" />

    <div class="presence-avatar">
      <span class="presence-face">AI</span>
      <div v-if="state === 'speaking'" class="sound-bars" aria-hidden="true">
        <i /><i /><i /><i /><i />
      </div>
      <div v-if="state === 'thinking'" class="thinking-orbit" aria-hidden="true">
        <span /><span /><span />
      </div>
    </div>

    <template v-if="showMeta && size === 'main'">
      <p class="presence-title">AI 面试官</p>
      <p class="presence-status">{{ statusText }}</p>
      <p v-if="state === 'idle'" class="presence-hint">
        请保持网络畅通，准备好后点击下方开始答题
      </p>
    </template>
  </div>
</template>

<style scoped>
.presence {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  text-align: center;
}

.presence--pip {
  position: absolute;
  inset: 0;
  gap: 0;
}

.presence-bg {
  position: absolute;
  inset: -30%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(129, 140, 248, 0.35) 0%, transparent 68%);
  opacity: 0.65;
  animation: presence-glow 4.2s ease-in-out infinite;
}

.presence--speaking .presence-bg {
  animation: presence-glow-active 1.4s ease-in-out infinite;
}

.presence--listening .presence-bg {
  background: radial-gradient(circle, rgba(74, 222, 128, 0.28) 0%, transparent 68%);
  animation: presence-glow-listen 2.2s ease-in-out infinite;
}

.presence--thinking .presence-bg {
  background: radial-gradient(circle, rgba(251, 191, 36, 0.22) 0%, transparent 68%);
  animation: presence-glow-think 1.8s ease-in-out infinite;
}

.presence-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.18);
  pointer-events: none;
}

.presence-ring--outer {
  width: 148px;
  height: 148px;
  animation: presence-breathe 3.6s ease-in-out infinite;
}

.presence-ring--inner {
  width: 128px;
  height: 128px;
  border-color: rgba(255, 255, 255, 0.1);
  animation: presence-breathe 3.6s ease-in-out infinite reverse;
}

.presence--pip .presence-ring--outer {
  width: 78px;
  height: 78px;
}

.presence--pip .presence-ring--inner {
  width: 64px;
  height: 64px;
}

.presence--listening .presence-ring--outer {
  border-color: rgba(74, 222, 128, 0.75);
  animation: presence-listen-pulse 1.6s ease-in-out infinite;
}

.presence--speaking .presence-ring--outer {
  border-color: rgba(165, 180, 252, 0.85);
}

.presence-avatar {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(145deg, #818cf8 0%, #6366f1 55%, #4f46e5 100%);
  display: grid;
  place-items: center;
  box-shadow:
    0 12px 40px rgba(99, 102, 241, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
  animation: presence-breathe-avatar 3.6s ease-in-out infinite;
  z-index: 1;
}

.presence--pip .presence-avatar {
  width: 64px;
  height: 64px;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
}

.presence--speaking .presence-avatar {
  animation: presence-speak-bob 0.85s ease-in-out infinite;
}

.presence-face {
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.presence--pip .presence-face {
  font-size: 1rem;
}

.sound-bars {
  position: absolute;
  bottom: -22px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 18px;
}

.presence--pip .sound-bars {
  bottom: -14px;
  height: 12px;
  gap: 2px;
}

.sound-bars i {
  display: block;
  width: 4px;
  border-radius: 999px;
  background: linear-gradient(180deg, #c7d2fe, #818cf8);
  animation: sound-bar 0.9s ease-in-out infinite;
}

.presence--pip .sound-bars i {
  width: 3px;
}

.sound-bars i:nth-child(1) {
  animation-delay: 0s;
}
.sound-bars i:nth-child(2) {
  animation-delay: 0.12s;
}
.sound-bars i:nth-child(3) {
  animation-delay: 0.24s;
}
.sound-bars i:nth-child(4) {
  animation-delay: 0.36s;
}
.sound-bars i:nth-child(5) {
  animation-delay: 0.48s;
}

.thinking-orbit {
  position: absolute;
  inset: -8px;
}

.thinking-orbit span {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fde68a;
  box-shadow: 0 0 10px rgba(253, 224, 71, 0.8);
  animation: think-dot 1.2s ease-in-out infinite;
}

.thinking-orbit span:nth-child(1) {
  top: 0;
  left: 50%;
  transform: translateX(-50%);
}
.thinking-orbit span:nth-child(2) {
  bottom: 8px;
  left: 6px;
  animation-delay: 0.2s;
}
.thinking-orbit span:nth-child(3) {
  bottom: 8px;
  right: 6px;
  animation-delay: 0.4s;
}

.presence-title {
  margin: 8px 0 0;
  font-size: 1.1rem;
  font-weight: 700;
  z-index: 1;
}

.presence-status {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.88);
  z-index: 1;
}

.presence-hint {
  margin: 0;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.65);
  max-width: 320px;
  z-index: 1;
}

@keyframes presence-breathe {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.55;
  }
  50% {
    transform: scale(1.06);
    opacity: 0.9;
  }
}

@keyframes presence-breathe-avatar {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.03);
  }
}

@keyframes presence-glow {
  0%,
  100% {
    opacity: 0.45;
    transform: scale(0.95);
  }
  50% {
    opacity: 0.85;
    transform: scale(1.05);
  }
}

@keyframes presence-glow-active {
  0%,
  100% {
    opacity: 0.65;
  }
  50% {
    opacity: 1;
  }
}

@keyframes presence-glow-listen {
  0%,
  100% {
    opacity: 0.5;
  }
  50% {
    opacity: 0.95;
  }
}

@keyframes presence-glow-think {
  0%,
  100% {
    opacity: 0.4;
  }
  50% {
    opacity: 0.8;
  }
}

@keyframes presence-listen-pulse {
  0%,
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.35);
  }
  50% {
    transform: scale(1.04);
    box-shadow: 0 0 0 10px rgba(74, 222, 128, 0);
  }
}

@keyframes presence-speak-bob {
  0%,
  100% {
    transform: scale(1) translateY(0);
  }
  50% {
    transform: scale(1.02) translateY(-2px);
  }
}

@keyframes sound-bar {
  0%,
  100% {
    height: 6px;
  }
  50% {
    height: 16px;
  }
}

@keyframes think-dot {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.85);
  }
  50% {
    opacity: 1;
    transform: scale(1.1);
  }
}
</style>
