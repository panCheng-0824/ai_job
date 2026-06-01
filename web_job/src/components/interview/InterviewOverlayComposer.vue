<script setup>
/**
 * 面试遮层 — 本题回答输入区（仅答题中展示）。
 */
const props = defineProps({
  streaming: { type: Boolean, default: false },
  canSend: { type: Boolean, default: false }
});

const emit = defineEmits(["send"]);

const draft = defineModel("draft", { type: String, default: "" });

function onSendClick() {
  const text = draft.value.trim();
  if (!text || props.streaming) return;
  emit("send", text);
  draft.value = "";
}

function onKeydown(ev) {
  if (ev.key === "Enter" && !ev.shiftKey) {
    ev.preventDefault();
    onSendClick();
  }
}
</script>

<template>
  <footer class="scene-foot">
    <textarea
      v-model="draft"
      class="scene-foot__input"
      rows="3"
      :placeholder="streaming ? '面试官正在回复…' : '输入本题回答（Enter 发送，Shift+Enter 换行）'"
      :disabled="streaming"
      @keydown="onKeydown"
    />
    <div class="scene-foot__bar">
      <span class="scene-foot__tip">完整对话同步保存在下方会话框；此处仅展示本题多轮问答</span>
      <button type="button" class="btn-send" :disabled="!canSend" @click="onSendClick">
        {{ streaming ? "等待面试官…" : "发送回答" }}
      </button>
    </div>
  </footer>
</template>

<style scoped>
.scene-foot {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: 1px solid #f1f5f9;
  padding-top: 14px;
}
.scene-foot__input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 14px;
  resize: none;
  min-height: 72px;
  font-family: inherit;
}
.scene-foot__input:focus {
  outline: none;
  border-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
}
.scene-foot__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.scene-foot__tip {
  flex: 1;
  font-size: 11px;
  color: #94a3b8;
  min-width: 160px;
}
.btn-send {
  padding: 8px 22px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #059669, #047857);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}
.btn-send:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
