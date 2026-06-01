<script setup>
/**
 * 聊天页 — 正式面试沉浸式遮层。
 *
 * 进度圆点与题干区共用 session.seqNo；支持已答回看（无输入框）。
 */
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import InterviewOverlayComposer from "./InterviewOverlayComposer.vue";
import InterviewOverlayProgressBar from "./InterviewOverlayProgressBar.vue";
import InterviewOverlayQuestionPanel from "./InterviewOverlayQuestionPanel.vue";
import InterviewOverlayThread from "./InterviewOverlayThread.vue";
import {
  findQuestionBySeq,
  phaseLabel,
  pickCurrentQuestionItem,
  resolveQuestionText
} from "../../modules/interview/interviewOverlayHelpers";

const props = defineProps({
  active: { type: Boolean, default: false },
  session: { type: Object, default: null },
  questions: { type: Array, default: () => [] },
  turns: { type: Array, default: () => [] },
  /** live=答题中 review=回看已答 */
  viewMode: { type: String, default: "live" },
  selectedSeqNo: { type: Number, default: null },
  streaming: { type: Boolean, default: false },
  streamingThinking: { type: String, default: "" },
  streamingAnswer: { type: String, default: "" }
});

const emit = defineEmits(["send", "exit", "selectQuestion", "backToLive"]);

const router = useRouter();
const draft = ref("");

const liveSeqNo = computed(() => Number(props.session?.seqNo ?? 0));

const displaySeqNo = computed(() => {
  if (props.viewMode === "review" && props.selectedSeqNo != null) {
    return Number(props.selectedSeqNo);
  }
  return liveSeqNo.value;
});

const displayQuestionItem = computed(() => {
  if (props.viewMode === "review" && props.selectedSeqNo != null) {
    return findQuestionBySeq(props.questions, props.selectedSeqNo);
  }
  return pickCurrentQuestionItem(props.questions, props.session);
});

const questionText = computed(() =>
  resolveQuestionText(props.session, props.questions, displaySeqNo.value)
);

const questionTotal = computed(() => {
  const t = props.session?.questionTotal;
  if (t != null && t > 0) return t;
  return props.questions.length;
});

const showComposer = computed(() => props.viewMode === "live" && props.active);

const canSend = computed(() => showComposer.value && !props.streaming && draft.value.trim().length > 0);

const headerPhase = computed(() => phaseLabel(props.session?.phase));

const threadStreaming = computed(() => props.viewMode === "live" && props.streaming);

function onSendClick(text) {
  emit("send", text);
}

function onDotSelect(payload) {
  emit("selectQuestion", payload);
}

function onExitClick() {
  emit("exit");
}

function onViewRecord() {
  const rid = props.session?.recordId;
  if (!rid) return;
  router.push(`/me/interviews/${encodeURIComponent(rid)}`);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="interview-fade">
      <div v-if="active" class="interview-scene" role="dialog" aria-modal="true" aria-label="正式面试">
        <div class="interview-scene__backdrop" @click="onExitClick" />
        <div class="interview-scene__panel">
          <header class="scene-head">
            <div class="scene-head__brand">
              <span class="scene-head__icon" aria-hidden="true">🎯</span>
              <div>
                <h2 class="scene-head__title">正式面试</h2>
                <p class="scene-head__phase">{{ headerPhase }}</p>
              </div>
            </div>
            <div class="scene-head__actions">
              <button v-if="session?.recordId" type="button" class="btn-ghost" @click="onViewRecord">
                查看记录
              </button>
              <button type="button" class="btn-ghost btn-ghost--exit" @click="onExitClick">退出面试</button>
            </div>
          </header>

          <InterviewOverlayProgressBar
            :live-seq-no="liveSeqNo"
            :selected-seq-no="viewMode === 'review' ? selectedSeqNo : null"
            :total="questionTotal"
            :questions="questions"
            @select="onDotSelect"
          />

          <p v-if="viewMode === 'review'" class="review-banner">
            正在查看第 {{ displaySeqNo + 1 }} 题作答记录（本题已结束）
            <button type="button" class="review-banner__btn" @click="emit('backToLive')">返回当前题</button>
          </p>

          <div class="scene-body">
            <InterviewOverlayQuestionPanel
              :key="`q-${displaySeqNo}-${questionText}`"
              :seq-no="displayQuestionItem?.seq_no ?? displaySeqNo"
              :question-text="questionText"
              :thinking-hint="displayQuestionItem?.thinking_hint || ''"
              :answer-status="displayQuestionItem?.answer_status || session?.evaluatorStatus || 'pending'"
              :phase="viewMode === 'review' ? 'question' : session?.phase || 'question'"
            />
            <InterviewOverlayThread
              :turns="turns"
              :streaming="threadStreaming"
              :streaming-thinking="streamingThinking"
              :streaming-answer="streamingAnswer"
            />
          </div>

          <InterviewOverlayComposer
            v-if="showComposer"
            v-model:draft="draft"
            :streaming="streaming"
            :can-send="canSend"
            @send="onSendClick"
          />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.interview-scene {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 0;
}
.interview-scene__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.72);
  backdrop-filter: blur(4px);
}
.interview-scene__panel {
  position: relative;
  z-index: 1;
  width: min(720px, 100%);
  max-height: 100vh;
  margin: auto 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #fff;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.35);
  padding: 20px 22px 18px;
  overflow: hidden;
}
@media (min-width: 640px) {
  .interview-scene {
    padding: 16px;
  }
  .interview-scene__panel {
    border-radius: 16px;
    max-height: calc(100vh - 32px);
  }
}
.scene-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.scene-head__brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.scene-head__icon {
  font-size: 28px;
  line-height: 1;
}
.scene-head__title {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}
.scene-head__phase {
  margin: 2px 0 0;
  font-size: 13px;
  color: #64748b;
}
.scene-head__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.btn-ghost {
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  color: #334155;
}
.btn-ghost--exit:hover {
  border-color: #fecaca;
  color: #b91c1c;
  background: #fef2f2;
}
.review-banner {
  margin: 0;
  padding: 8px 12px;
  font-size: 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.review-banner__btn {
  border: none;
  background: none;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.scene-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}
.interview-fade-enter-active,
.interview-fade-leave-active {
  transition: opacity 0.2s ease;
}
.interview-fade-enter-from,
.interview-fade-leave-to {
  opacity: 0;
}
</style>
