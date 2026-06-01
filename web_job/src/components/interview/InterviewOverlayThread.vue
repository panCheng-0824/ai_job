<script setup>
/**
 * 面试遮层 — 本题多轮对话流（仅展示当前题内的问答，不重复整段会话历史）。
 */
import { nextTick, ref, watch } from "vue";

const props = defineProps({
  turns: { type: Array, default: () => [] },
  streaming: { type: Boolean, default: false },
  streamingThinking: { type: String, default: "" },
  streamingAnswer: { type: String, default: "" }
});

const listEl = ref(null);

watch(
  () => [props.turns.length, props.streaming, props.streamingAnswer],
  async () => {
    await nextTick();
    if (listEl.value) {
      listEl.value.scrollTop = listEl.value.scrollHeight;
    }
  }
);
</script>

<template>
  <section class="thread" aria-label="本题对话">
    <header class="thread__head">本题对话</header>
    <div ref="listEl" class="thread__list">
      <p v-if="!turns.length && !streaming" class="thread__empty">面试官发言将显示在这里</p>
      <div
        v-for="(t, i) in turns"
        :key="i"
        class="bubble"
        :class="t.role === 'user' ? 'bubble--user' : 'bubble--interviewer'"
      >
        <span class="bubble__role">{{ t.role === "user" ? "你" : "面试官" }}</span>
        <p class="bubble__text">{{ t.text }}</p>
      </div>
      <div v-if="streaming" class="bubble bubble--interviewer bubble--streaming">
        <span class="bubble__role">面试官</span>
        <p v-if="streamingThinking && !streamingAnswer" class="bubble__text bubble__thinking">
          {{ streamingThinking }}
        </p>
        <p v-else-if="streamingAnswer" class="bubble__text">{{ streamingAnswer }}</p>
        <p v-else class="bubble__text bubble__typing">正在思考…</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.thread {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
}
.thread__head {
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-bottom: 1px solid #f1f5f9;
  background: #fafafa;
}
.thread__list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: min(42vh, 360px);
}
.thread__empty {
  margin: auto;
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
}
.bubble {
  max-width: 92%;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.55;
}
.bubble--interviewer {
  align-self: flex-start;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}
.bubble--user {
  align-self: flex-end;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
}
.bubble--streaming {
  opacity: 0.92;
}
.bubble__role {
  display: block;
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 4px;
  color: #64748b;
}
.bubble--user .bubble__role {
  color: #047857;
}
.bubble__text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.bubble__thinking {
  color: #64748b;
  font-size: 13px;
}
.bubble__typing {
  color: #94a3b8;
  font-style: italic;
}
</style>
