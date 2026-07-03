<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { loadCubismCoreScript } from "../../lib/cubism/loadCubismCore.js";

const props = defineProps({
  state: {
    type: String,
    default: "idle",
    validator: (v) => ["idle", "listening", "speaking", "thinking"].includes(v)
  },
  model: { type: String, default: "Haru" },
  size: {
    type: String,
    default: "main",
    validator: (v) => ["main", "pip"].includes(v)
  },
  statusText: { type: String, default: "" },
  showMeta: { type: Boolean, default: true },
  command: { type: Object, default: null }
});

const canvasRef = ref(null);
const loadError = ref("");
const ready = ref(false);

let runtime = null;

async function boot() {
  loadError.value = "";
  ready.value = false;
  if (!canvasRef.value) return;

  runtime?.stop();
  runtime = null;

  try {
    await loadCubismCoreScript();
    const { InterviewCubismRuntime } = await import("../../lib/cubism/interviewCubismRuntime.ts");
    runtime = new InterviewCubismRuntime(canvasRef.value);
    const ok = await runtime.start();
    if (!ok) {
      loadError.value = "数字人初始化失败，请检查浏览器 WebGL 支持";
      return;
    }
    ready.value = true;
    runtime.setModel(props.model);
    runtime.applyPresenceState(props.state);
  } catch (err) {
    loadError.value = err?.message || "数字人加载失败";
  }
}

watch(
  () => props.state,
  (state) => {
    runtime?.applyPresenceState(state);
  }
);

watch(
  () => props.model,
  (model) => {
    runtime?.setModel(model);
  }
);

watch(
  () => props.command?.nonce,
  () => {
    if (!props.command || !runtime) return;
    runtime.executeCommand(props.command);
  }
);

onMounted(boot);
onBeforeUnmount(() => {
  runtime?.stop();
  runtime = null;
});
</script>

<template>
  <div
    class="live2d-presence"
    :class="[`live2d-presence--${state}`, `live2d-presence--${size}`]"
    role="img"
    :aria-label="statusText || 'AI 数字人面试官'"
  >
    <canvas ref="canvasRef" class="live2d-canvas" />

    <div v-if="loadError" class="live2d-overlay live2d-fallback">
      <p>{{ loadError }}</p>
    </div>

    <div v-else-if="!ready" class="live2d-overlay live2d-loading">
      <span class="live2d-spinner" aria-hidden="true" />
      <p>数字人加载中…</p>
    </div>

    <div v-if="showMeta && size === 'main' && ready" class="live2d-meta">
      <p class="live2d-title">AI 数字人面试官</p>
      <p class="live2d-status">{{ statusText }}</p>
    </div>
  </div>
</template>

<style scoped>
.live2d-presence {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  color: #fff;
  text-align: center;
}

.live2d-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
}

.live2d-overlay,
.live2d-meta {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  pointer-events: none;
}

.live2d-loading,
.live2d-fallback {
  top: 50%;
  transform: translate(-50%, -50%);
  display: grid;
  place-items: center;
  gap: 8px;
  padding: 16px;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.88);
}

.live2d-meta {
  bottom: 72px;
  width: min(100%, 360px);
  padding: 0 16px;
}

.live2d-spinner {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.25);
  border-top-color: #a5b4fc;
  animation: live2d-spin 0.8s linear infinite;
}

.live2d-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
}

.live2d-status {
  margin: 4px 0 0;
  font-size: 0.82rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.88);
}

.live2d-presence--speaking {
  filter: drop-shadow(0 0 18px rgba(129, 140, 248, 0.35));
}

.live2d-presence--listening {
  filter: drop-shadow(0 0 16px rgba(74, 222, 128, 0.28));
}

.live2d-presence--thinking {
  filter: drop-shadow(0 0 14px rgba(251, 191, 36, 0.25));
}

@keyframes live2d-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
