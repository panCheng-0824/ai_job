<script setup>
/**
 * 面试中心 — 视频面试房间壳层（对齐设计稿 13）。
 * 左侧视频区 + 右侧聊天；「开始答题」跳转 AI 助手并自动进入正式面试遮层。
 */
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  buildContinueChatQuery,
  formatRecordSchedule,
  recordCompanyLabel,
  recordDisplayTitle
} from "../../modules/interview/recordCenterMeta";
import InterviewerPresence from "./InterviewerPresence.vue";
import InterviewerVoicePanel from "./InterviewerVoicePanel.vue";
import { useInterviewerPresence } from "../../composables/useInterviewerPresence";
import { useRoomVoiceBroadcast } from "../../composables/useRoomVoiceBroadcast";
import {
  loadInterviewLive2dModel,
  saveInterviewLive2dModel
} from "../../config/interviewerPersonas";

const InterviewerLive2D = defineAsyncComponent(() => import("./InterviewerLive2D.vue"));

const props = defineProps({
  record: { type: Object, required: true },
  studentName: { type: String, default: "我" }
});

const emit = defineEmits(["exit"]);

const router = useRouter();

const {
  presenceState,
  presenceLabel,
  speakFor,
  thinkFor,
  bindVoiceActivity,
  stopVoiceActivity,
  setMicEnabled
} = useInterviewerPresence();

const {
  useVoiceOutput,
  ttsVoice,
  broadcast,
  stopBroadcast,
  setTtsVoice,
  setVoiceOutput
} = useRoomVoiceBroadcast({ speakFor });

const micOn = ref(true);
const cameraOn = ref(true);
const chatOpen = ref(true);
const videoSwapped = ref(false);
/** presence = 呼吸动效；live2d = Cubism 数字人 */
const interviewerVisual = ref("presence");
/** 左侧面试官配置（含角色表现）默认收起，主画面优先 */
const configPanelCollapsed = ref(true);
const live2dModel = ref(loadInterviewLive2dModel());
const live2dCommand = ref(null);
const chatInput = ref("");
const chatMessages = ref([
  {
    id: "welcome",
    role: "assistant",
    name: "面试小助手",
    text: "面试已经准时开始，请稍等！"
  }
]);

let mediaStream = null;
const studentVideoPip = ref(null);
const studentVideoMain = ref(null);
const chatListRef = ref(null);

const headerTitle = computed(() => {
  const title = recordDisplayTitle(props.record);
  const company = recordCompanyLabel(props.record);
  return `${title} · ${company}`;
});

const scheduleText = computed(() => formatRecordSchedule(props.record.created_at));

/** 聊天区顶部时间分隔（对齐设计稿） */
const chatSessionLabel = computed(() => {
  const raw = props.record?.created_at;
  if (!raw) return scheduleText.value;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return scheduleText.value;
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const h = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${m}.${day} ${h}:${min}`;
});

const canSendChat = computed(() => Boolean(chatInput.value.trim()));

const canStart = computed(() => Boolean(props.record.interview_session_id));

const startQuery = computed(() => {
  const q = {
    ...buildContinueChatQuery(props.record),
    autointerview: "1",
    record_id: props.record.record_id,
    return: `/interview/center/room/${encodeURIComponent(props.record.record_id)}`
  };
  return q;
});

function scrollChatToBottom() {
  nextTick(() => {
    const el = chatListRef.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

function pushUserMessage(text) {
  chatMessages.value.push({
    id: `u-${Date.now()}`,
    role: "user",
    name: props.studentName || "我",
    text
  });
  scrollChatToBottom();
}

function pushAssistantMessage(text) {
  chatMessages.value.push({
    id: `a-${Date.now()}`,
    role: "assistant",
    name: "面试小助手",
    text
  });
  scrollChatToBottom();
}

function onSendChat() {
  const text = chatInput.value.trim();
  if (!text) return;
  pushUserMessage(text);
  chatInput.value = "";
  thinkFor(480);
  window.setTimeout(() => {
    const reply = "好的，收到。准备好后请点击下方「开始答题」进入正式面试。";
    pushAssistantMessage(reply);
    speakFor(reply);
    void broadcast(reply);
  }, 520);
}

function onSelectPersona({ voiceId, live2dModel: model }) {
  setTtsVoice(voiceId);
  if (live2dModel.value !== model) {
    live2dModel.value = saveInterviewLive2dModel(model);
  }
}

function onLive2dAction(cmd) {
  if (interviewerVisual.value !== "live2d") return;
  live2dCommand.value = { ...cmd, nonce: Date.now() };
}

function onVoiceOutputChange(on) {
  setVoiceOutput(on);
}

function onStartInterview() {
  if (!canStart.value) return;
  thinkFor(700);
  window.setTimeout(() => {
    router.push({ path: "/student-chat", query: startQuery.value });
  }, 720);
}

function onHangUp() {
  stopVoiceActivity();
  stopBroadcast();
  stopCamera();
  emit("exit");
}

function swapViews() {
  videoSwapped.value = !videoSwapped.value;
  nextTick(bindStudentVideo);
}

function bindStudentVideo() {
  if (!mediaStream) return;
  for (const el of [studentVideoPip.value, studentVideoMain.value]) {
    if (el) el.srcObject = mediaStream;
  }
}

function toggleMic() {
  micOn.value = !micOn.value;
  setMicEnabled(micOn.value);
  if (mediaStream) {
    for (const track of mediaStream.getAudioTracks()) {
      track.enabled = micOn.value;
    }
  }
}

function toggleCamera() {
  cameraOn.value = !cameraOn.value;
  if (mediaStream) {
    for (const track of mediaStream.getVideoTracks()) {
      track.enabled = cameraOn.value;
    }
  }
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraOn.value = false;
    return;
  }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    bindStudentVideo();
  } catch {
    cameraOn.value = false;
    micOn.value = false;
  }
}

function stopCamera() {
  stopVoiceActivity();
  if (mediaStream) {
    for (const track of mediaStream.getTracks()) track.stop();
    mediaStream = null;
  }
  for (const el of [studentVideoPip.value, studentVideoMain.value]) {
    if (el) el.srcObject = null;
  }
}

async function initRoom() {
  const welcome = chatMessages.value[0]?.text;
  if (welcome) {
    speakFor(welcome);
    void broadcast(welcome);
  }
  scrollChatToBottom();
  await startCamera();
  if (mediaStream) bindVoiceActivity(mediaStream);
}

onMounted(initRoom);
onBeforeUnmount(stopCamera);
</script>

<template>
  <div class="room-shell" :class="{ 'room-shell--config-collapsed': configPanelCollapsed }">
    <InterviewerVoicePanel
      v-model:collapsed="configPanelCollapsed"
      :voice-id="ttsVoice"
      :live2d-model="live2dModel"
      :interviewer-visual="interviewerVisual"
      @select-persona="onSelectPersona"
      @update:voice-output="onVoiceOutputChange"
      @live2d-action="onLive2dAction"
    />

    <section class="room-video">
      <header class="room-head">
        <div class="room-head-main">
          <h1>{{ headerTitle }}</h1>
          <p class="room-head-meta">
            <span>{{ scheduleText }}</span>
            <span class="room-head-dot" aria-hidden="true">·</span>
            <span class="presence-inline">
              <span class="presence-dot" :class="`presence-dot--${presenceState}`" aria-hidden="true" />
              {{ presenceLabel }}
            </span>
          </p>
        </div>
        <div class="room-head-actions">
          <button
            v-if="configPanelCollapsed"
            type="button"
            class="head-config-btn"
            title="展开面试官配置与角色表现"
            @click="configPanelCollapsed = false"
          >
            面试官配置
          </button>
          <div class="visual-toggle" role="group" aria-label="切换面试官呈现方式">
            <button
              type="button"
              class="visual-toggle-btn"
              :class="{ active: interviewerVisual === 'presence' }"
              @click="interviewerVisual = 'presence'"
            >
              呼吸
            </button>
            <button
              type="button"
              class="visual-toggle-btn"
              :class="{ active: interviewerVisual === 'live2d' }"
              @click="interviewerVisual = 'live2d'"
            >
              数字人
            </button>
          </div>
          <button type="button" class="head-back" @click="onHangUp">← 返回</button>
        </div>
      </header>

      <div
        class="video-stage"
        :class="`video-stage--${presenceState}`"
      >
        <div class="video-stage-ambient" aria-hidden="true" />

        <button
          type="button"
          class="video-main video-swap-target"
          :title="videoSwapped ? '点击切回面试官大画面' : '点击切换为学生大画面'"
          @click="swapViews"
        >
          <template v-if="!videoSwapped">
            <InterviewerLive2D
              v-if="interviewerVisual === 'live2d'"
              :key="`main-${live2dModel}`"
              :model="live2dModel"
              :command="live2dCommand"
              :state="presenceState"
              size="main"
              :status-text="presenceLabel"
            />
            <InterviewerPresence
              v-else
              :state="presenceState"
              size="main"
              :status-text="presenceLabel"
            />
          </template>
          <template v-else>
            <video
              ref="studentVideoMain"
              autoplay
              playsinline
              muted
              class="fill-video"
            />
            <p v-if="!cameraOn" class="cam-off-label">摄像头已关闭</p>
            <p class="role-badge role-badge--self">{{ studentName || "我" }}</p>
          </template>
          <span class="swap-hint">点击互换画面</span>
        </button>

        <button
          type="button"
          class="video-pip video-swap-target"
          :class="{ off: !cameraOn && !videoSwapped }"
          :title="videoSwapped ? '点击切回学生小窗' : '点击切换为面试官小窗'"
          @click.stop="swapViews"
        >
          <template v-if="!videoSwapped">
            <video
              ref="studentVideoPip"
              autoplay
              playsinline
              muted
              class="fill-video fill-video--mirror"
            />
            <p v-if="!cameraOn" class="cam-off-label">摄像头已关闭</p>
            <span class="pip-badge">{{ studentName || "我" }}</span>
          </template>
          <template v-else>
            <InterviewerLive2D
              v-if="interviewerVisual === 'live2d'"
              :key="`pip-${live2dModel}`"
              :model="live2dModel"
              :command="live2dCommand"
              :state="presenceState"
              size="pip"
              :show-meta="false"
              :status-text="presenceLabel"
            />
            <InterviewerPresence
              v-else
              :state="presenceState"
              size="pip"
              :show-meta="false"
              :status-text="presenceLabel"
            />
            <span class="pip-badge pip-badge--ai">AI 面试官</span>
          </template>
          <span class="pip-swap-icon" aria-hidden="true">⇄</span>
        </button>
      </div>

      <div class="control-bar">
        <button
          type="button"
          class="ctrl-btn"
          :class="{ off: !micOn }"
          :title="micOn ? '关闭麦克风' : '开启麦克风'"
          @click="toggleMic"
        >
          <span aria-hidden="true">{{ micOn ? "🎤" : "🔇" }}</span>
        </button>
        <button
          type="button"
          class="ctrl-btn"
          :class="{ off: !cameraOn }"
          :title="cameraOn ? '关闭摄像头' : '开启摄像头'"
          @click="toggleCamera"
        >
          <span aria-hidden="true">{{ cameraOn ? "📷" : "📷" }}</span>
        </button>
        <button type="button" class="ctrl-btn ctrl-btn--disabled" disabled title="暂不支持">
          <span aria-hidden="true">🖥</span>
        </button>
        <button
          type="button"
          class="ctrl-btn"
          :class="{ active: chatOpen }"
          title="聊天"
          @click="chatOpen = !chatOpen"
        >
          <span aria-hidden="true">💬</span>
        </button>
        <button type="button" class="ctrl-btn ctrl-btn--hangup" title="结束并返回" @click="onHangUp">
          <span aria-hidden="true">📞</span>
        </button>
      </div>

      <div class="room-actions">
        <button
          type="button"
          class="start-btn"
          :disabled="!canStart"
          @click="onStartInterview"
        >
          {{ record.session_status === "in_progress" ? "继续答题" : "开始答题" }}
        </button>
      </div>
    </section>

    <aside v-show="chatOpen" class="room-chat">
      <header class="chat-head">
        <div class="chat-head-main">
          <h2>聊天</h2>
          <p class="chat-head-sub">与面试小助手沟通</p>
        </div>
        <button type="button" class="chat-close" title="收起聊天" @click="chatOpen = false">×</button>
      </header>

      <div ref="chatListRef" class="chat-list">
        <p class="chat-time-divider">{{ chatSessionLabel }}</p>

        <article
          v-for="msg in chatMessages"
          :key="msg.id"
          class="chat-msg"
          :class="msg.role === 'user' ? 'chat-msg--user' : 'chat-msg--bot'"
        >
          <div
            class="chat-avatar"
            :class="msg.role === 'user' ? 'chat-avatar--user' : 'chat-avatar--bot'"
            aria-hidden="true"
          >
            <span v-if="msg.role === 'user'">{{ (studentName || "我").slice(0, 1) }}</span>
            <svg v-else viewBox="0 0 24 24" class="chat-bot-icon" aria-hidden="true">
              <rect x="5" y="8" width="14" height="11" rx="3" fill="currentColor" opacity="0.9" />
              <circle cx="9.5" cy="13" r="1.2" fill="#fff" />
              <circle cx="14.5" cy="13" r="1.2" fill="#fff" />
              <path d="M12 4v3" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              <circle cx="12" cy="3" r="1.5" fill="currentColor" />
            </svg>
          </div>
          <div class="chat-body">
            <p class="chat-name">{{ msg.name }}</p>
            <div class="chat-bubble">
              <p class="chat-text">{{ msg.text }}</p>
            </div>
          </div>
        </article>
      </div>

      <footer class="chat-foot">
        <div class="chat-compose">
          <input
            v-model="chatInput"
            type="text"
            class="chat-input"
            placeholder="请输入内容…"
            @keydown.enter.prevent="onSendChat"
          />
          <button type="button" class="chat-emoji" disabled title="表情（即将支持）" aria-label="表情">☺</button>
          <button
            type="button"
            class="chat-send"
            aria-label="发送"
            :disabled="!canSendChat"
            @click="onSendChat"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3.4 20.6 21 12 3.4 3.4l2.8 7.2L16 11 6.2 13.4l-2.8 7.2Z" fill="currentColor" />
            </svg>
          </button>
        </div>
      </footer>
    </aside>
  </div>
</template>

<style scoped>
.room-shell {
  display: grid;
  grid-template-columns: minmax(260px, 300px) minmax(0, 1fr) minmax(280px, 340px);
  gap: 0;
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  max-height: 100%;
  border-radius: var(--home-radius-lg, 16px);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  background: #fff;
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
  overflow: hidden;
  transition: grid-template-columns 0.22s ease;
}

.room-shell--config-collapsed {
  grid-template-columns: 52px minmax(0, 1fr) minmax(280px, 340px);
}

.room-shell:not(.room-shell--config-collapsed) {
  grid-template-columns: minmax(248px, 288px) minmax(0, 1fr) minmax(280px, 320px);
}

.room-shell > :first-child {
  min-height: 0;
  overflow: hidden;
}

.room-shell > .room-chat {
  min-height: 0;
  overflow: hidden;
}

.room-video {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}

.room-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  background: rgba(255, 255, 255, 0.72);
}

.room-head-main {
  min-width: 0;
  flex: 1;
}

.room-head h1 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.room-head-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 4px 0 0;
  font-size: 0.76rem;
  color: #64748b;
}

.room-head-dot {
  opacity: 0.5;
}

.presence-inline {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 600;
  color: #475569;
}

.room-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.head-config-btn,
.head-back {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  flex-shrink: 0;
  white-space: nowrap;
}

.head-config-btn {
  color: #4338ca;
  border-color: #c7d2fe;
  background: #eef2ff;
}

.head-config-btn:hover {
  background: #e0e7ff;
}

.visual-toggle {
  display: inline-flex;
  padding: 3px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}

.visual-toggle-btn {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  padding: 6px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.visual-toggle-btn.active {
  color: #fff;
  background: linear-gradient(135deg, #5b6adf, #6366f1);
  box-shadow: 0 4px 12px rgba(91, 106, 223, 0.28);
}

.video-stage {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
  margin: 12px 16px 0;
  border-radius: 16px;
  overflow: hidden;
  background: #1e293b;
  transition: box-shadow 0.35s ease;
  isolation: isolate;
}

.video-stage-ambient {
  position: absolute;
  inset: 0;
  background: linear-gradient(145deg, #1e293b 0%, #334155 48%, #475569 100%);
  z-index: 0;
}

.video-stage--speaking .video-stage-ambient {
  animation: stage-ambient-speak 5s ease-in-out infinite;
}

.video-stage--listening .video-stage-ambient {
  background: linear-gradient(145deg, #1a2e25 0%, #1e3a2f 48%, #334155 100%);
}

.video-stage--thinking .video-stage-ambient {
  background: linear-gradient(145deg, #2a2418 0%, #334155 48%, #475569 100%);
  animation: stage-ambient-think 2.4s ease-in-out infinite;
}

.video-stage--listening {
  box-shadow: inset 0 0 0 3px rgba(74, 222, 128, 0.38);
}

.video-stage--speaking {
  box-shadow: inset 0 0 0 3px rgba(129, 140, 248, 0.42);
}

.video-stage--thinking {
  box-shadow: inset 0 0 0 3px rgba(251, 191, 36, 0.35);
}

.video-main {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: block;
  overflow: hidden;
  color: #fff;
  text-align: center;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
}

.video-swap-target:hover .swap-hint,
.video-swap-target:focus-visible .swap-hint {
  opacity: 1;
}

.video-swap-target:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.85);
  outline-offset: -4px;
}

.fill-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.fill-video--mirror {
  transform: scaleX(-1);
}

.cam-off-label {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  font-size: 0.88rem;
  color: #94a3b8;
  background: rgba(15, 23, 42, 0.72);
  z-index: 1;
}

.role-badge {
  position: absolute;
  left: 16px;
  bottom: 16px;
  z-index: 2;
  margin: 0;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(6px);
}

.role-badge--self {
  color: #fde68a;
}

.swap-hint {
  position: absolute;
  bottom: 16px;
  right: 16px;
  z-index: 2;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  background: rgba(15, 23, 42, 0.45);
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
}

.interviewer-label {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
}

.presence-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.presence-dot--speaking {
  background: #6366f1;
  animation: presence-dot-pulse 1s ease-in-out infinite;
}

.presence-dot--listening {
  background: #22c55e;
  animation: presence-dot-pulse 1.2s ease-in-out infinite;
}

.presence-dot--thinking {
  background: #f59e0b;
  animation: presence-dot-pulse 0.9s ease-in-out infinite;
}

@keyframes stage-ambient-speak {
  0%,
  100% {
    filter: brightness(1);
  }
  50% {
    filter: brightness(1.08);
  }
}

@keyframes stage-ambient-think {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.88;
  }
}

@keyframes presence-dot-pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.75;
  }
  50% {
    transform: scale(1.25);
    opacity: 1;
  }
}

.video-pip {
  position: absolute;
  top: 18px;
  right: 18px;
  z-index: 3;
  width: min(280px, 38%);
  aspect-ratio: 16 / 10;
  min-height: 168px;
  border-radius: 14px;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.9);
  background: #0f172a;
  box-shadow: 0 10px 32px rgba(0, 0, 0, 0.42);
  padding: 0;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.video-pip:hover {
  transform: scale(1.02);
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.5);
}

.video-pip.off {
  background: #1e293b;
}

.pip-badge {
  position: absolute;
  left: 10px;
  bottom: 10px;
  z-index: 2;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 0.68rem;
  font-weight: 700;
  color: #fde68a;
  background: rgba(15, 23, 42, 0.62);
  max-width: calc(100% - 40px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pip-badge--ai {
  color: #e0e7ff;
}

.pip-swap-icon {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 0.82rem;
  font-weight: 700;
  color: #fff;
  background: rgba(15, 23, 42, 0.55);
  pointer-events: none;
}

.control-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 14px 16px 6px;
  flex-shrink: 0;
}

.ctrl-btn {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
  cursor: pointer;
  font-size: 1.1rem;
  display: grid;
  place-items: center;
  transition: transform 0.15s, background 0.15s;
}

.ctrl-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.ctrl-btn.off {
  background: #fef2f2;
}

.ctrl-btn.active {
  background: #eef2ff;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25);
}

.ctrl-btn--disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ctrl-btn--hangup {
  background: #ef4444;
  color: #fff;
}

.room-actions {
  display: flex;
  justify-content: center;
  padding: 6px 16px 14px;
  flex-shrink: 0;
}

.start-btn {
  border: none;
  border-radius: 999px;
  padding: 10px 28px;
  font-size: 0.88rem;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #5b6adf, #6366f1);
  box-shadow: 0 6px 20px rgba(91, 106, 223, 0.35);
  cursor: pointer;
}

.start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.room-chat {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  border-left: 1px solid #eef2f7;
  background: linear-gradient(180deg, #fafbff 0%, #fff 22%);
}

.chat-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid #eef2f7;
  background: rgba(255, 255, 255, 0.94);
  flex-shrink: 0;
}

.chat-head-main h2 {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 800;
  color: #0f172a;
}

.chat-head-sub {
  margin: 3px 0 0;
  font-size: 0.72rem;
  color: #94a3b8;
}

.chat-close {
  width: 28px;
  height: 28px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  flex-shrink: 0;
}

.chat-close:hover {
  color: #334155;
  border-color: #cbd5e1;
}

.chat-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scroll-behavior: smooth;
}

.chat-list::-webkit-scrollbar {
  width: 6px;
}

.chat-list::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.45);
  border-radius: 999px;
}

.chat-time-divider {
  align-self: center;
  margin: 0;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 600;
  color: #94a3b8;
  background: #f1f5f9;
}

.chat-msg {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  max-width: 100%;
}

.chat-msg--user {
  flex-direction: row-reverse;
}

.chat-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  font-size: 0.76rem;
  font-weight: 800;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}

.chat-avatar--bot {
  background: linear-gradient(145deg, #818cf8, #6366f1);
  color: #fff;
}

.chat-avatar--user {
  background: linear-gradient(145deg, #fde68a, #f59e0b);
  color: #78350f;
}

.chat-bot-icon {
  width: 20px;
  height: 20px;
}

.chat-body {
  min-width: 0;
  max-width: calc(100% - 44px);
}

.chat-msg--user .chat-body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.chat-name {
  margin: 0 0 5px;
  padding: 0 4px;
  font-size: 0.7rem;
  font-weight: 600;
  color: #94a3b8;
}

.chat-bubble {
  position: relative;
  max-width: min(100%, 240px);
}

.chat-text {
  margin: 0;
  padding: 10px 12px;
  border-radius: 14px;
  font-size: 0.84rem;
  line-height: 1.55;
  word-break: break-word;
}

.chat-msg--bot .chat-bubble .chat-text {
  background: #fff;
  color: #334155;
  border: 1px solid #eef2f7;
  border-top-left-radius: 4px;
  box-shadow: 0 2px 10px rgba(91, 106, 223, 0.06);
}

.chat-msg--user .chat-bubble .chat-text {
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  color: #312e81;
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-top-right-radius: 4px;
}

.chat-foot {
  flex-shrink: 0;
  padding: 10px 12px 14px;
  border-top: 1px solid #eef2f7;
  background: rgba(255, 255, 255, 0.96);
}

.chat-compose {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 6px 6px 14px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #fff;
  box-shadow: 0 2px 12px rgba(91, 106, 223, 0.06);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.chat-compose:focus-within {
  border-color: #a5b4fc;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.chat-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 6px 0;
  font-size: 0.84rem;
  color: #0f172a;
  outline: none;
}

.chat-input::placeholder {
  color: #94a3b8;
}

.chat-emoji {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #94a3b8;
  font-size: 1rem;
  cursor: not-allowed;
  opacity: 0.55;
  flex-shrink: 0;
}

.chat-send {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #5b6adf, #6366f1);
  color: #fff;
  cursor: pointer;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(91, 106, 223, 0.28);
  transition: transform 0.12s, opacity 0.12s;
}

.chat-send svg {
  width: 16px;
  height: 16px;
}

.chat-send:hover:not(:disabled) {
  transform: translateY(-1px);
}

.chat-send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

@media (max-width: 1100px) {
  .room-shell,
  .room-shell--config-collapsed,
  .room-shell:not(.room-shell--config-collapsed) {
    grid-template-columns: minmax(0, 1fr) minmax(260px, 300px);
  }

  .room-shell > :first-child {
    display: none;
  }
}

@media (max-width: 900px) {
  .room-shell {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .room-shell > :first-child {
    display: flex;
    border-right: none;
    border-bottom: 1px solid #eef2f7;
    max-height: min(42vh, 420px);
  }

  .room-chat {
    border-left: none;
    border-top: 1px solid #eef2f7;
    max-height: min(42vh, 380px);
  }

  .video-stage {
    min-height: 280px;
  }

  .video-pip {
    width: min(220px, 44%);
    min-height: 132px;
  }
}
</style>
