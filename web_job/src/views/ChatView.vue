<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiPost, apiPostSse, apiDelete, fetchTtsPostStream, playTtsStreamFromResponse, getStudentId } from "../api/client";
import {
  hydrateSessionResumeRenderCache,
  mergePersistedHistory,
  saveSessionResumeRenderCache,
  hasResumeRenderPayload
} from "../utils/mergeHistoryContextCards";
import { hydrateInterviewPlanStartHistory } from "../modules/interview/interviewStartCache";
import {
  hydrateSessionInterviewPlanPreviewCache,
  saveSessionInterviewPlanPreviewCache
} from "../modules/interview/interviewPlanPreviewCache";
import { DEFAULT_TTS_VOICE, TTS_VOICES, loadTtsVoice, saveTtsVoice } from "../config/ttsVoices";
import { useVoiceRecorder } from "../composables/useVoiceRecorder";
import { chatSidebarVisibleRef as chatSidebarVisible, toggleChatSidebarVisible } from "../composables/useChatSidebarVisible";
import {
  contextRailVisibleRef,
  toggleContextRailVisible
} from "../composables/useChatPlannerRailVisible";
import JobRecommendPanel from "../components/JobRecommendPanel.vue";
import ChatInterviewPlanStartBar from "../components/interview/ChatInterviewPlanStartBar.vue";
import ChatInterviewOverlay from "../components/interview/ChatInterviewOverlay.vue";
import ChatPlannerContextRail from "../components/ChatPlannerContextRail.vue";
import ContextRefCard from "../components/ContextRefCard.vue";
import { fetchContextDetail } from "../api/contextDetail";
import { CONTEXT_DRAG_MIME } from "../constants/contextDrag";
import { RESUME_OPTIMIZER_USERCODE } from "../constants/resumeOptimizer";
import { MOCK_INTERVIEWER_USERCODE } from "../constants/mockInterviewer";
import { dispatchResumeRender } from "../composables/useResumeRenderBridge";
import { useStreamWaitTimer } from "../composables/useStreamWaitTimer";
import { renderChatMarkdown } from "../utils/markdown";
import {
  resolvePlanIdFromMessage,
  resolvePlanVersionFromMessage,
  shouldShowInterviewPlanActionBar
} from "../modules/interview/planStart";
import {
  buildCtxKey,
  buildInterviewAnswerContext,
  buildInterviewStartContext,
  mergeProgressIntoSession
} from "../modules/interview/interviewModeContext";
import {
  buildReviewTurnsFromAnswerItem,
  findQuestionBySeq,
  hasInterviewProgress,
  pickFirstIncompleteQuestion,
  reconcileQuestionStatuses
} from "../modules/interview/interviewOverlayHelpers";
import { fetchInterviewRecordAnswers } from "../modules/interview/api";

const JOB_PLANNER_USERCODE = "ROLE001";

const route = useRoute();
const router = useRouter();

/** 登录学号（只读，来自 localStorage，与登录页一致） */
const loggedInStudentId = computed(() => getStudentId());
const usercode = ref(localStorage.getItem("usercode") || "");
const currentSessionId = ref(localStorage.getItem("session_id") || "");
const models = ref([]);
const sessions = ref([]);
const history = ref([]);
const message = ref("");
/** 输入区附加上下文（送入模型，界面不展示全文） */
const composerHiddenContext = ref("");
/** 输入区引用卡片 { card, message_context } */
const composerAttachments = ref([]);
const composerDropActive = ref(false);
/** 遮层正式面试模式 */
const interviewModeActive = ref(false);
const interviewModeSession = ref(null);
/** 遮层题目列表（含题干、状态） */
const interviewOverlayQuestions = ref([]);
/** 本题多轮对话（遮层内展示，与会话框全量历史分离） */
const interviewOverlayTurns = ref([]);
/** 遮层视图：live=答题中 review=回看已答 */
const interviewOverlayViewMode = ref("live");
const interviewOverlaySelectedSeq = ref(null);
const interviewOverlayReviewTurns = ref([]);
const error = ref("");
const thinkingText = ref("");
/** 当前轮是否收到过 reasoning/thinking 流（用于先展示思考、再解锁回答气泡） */
const streamingHasThinking = ref(false);
/** 当前轮是否已开始输出正文 delta（thinking 结束后） */
const streamingHasAnswer = ref(false);
const isStreaming = ref(false);
const streamWait = useStreamWaitTimer();
const { elapsedLabel: streamWaitLabel, isRunning: streamWaitRunning, start: startStreamWait, stop: stopStreamWait } =
  streamWait;
const useRolePipeline = ref(localStorage.getItem("use_role_pipeline") !== "0");
const useAdversarialHarness = ref(localStorage.getItem("use_adversarial_harness") === "1");
const useVoiceInput = ref(localStorage.getItem("chat_voice_input") === "1");
const useVoiceOutput = ref(localStorage.getItem("chat_voice_output") === "1");
const ttsVoice = ref(loadTtsVoice());
/** TTS 音色列表折叠：默认仅展示当前卡片 */
const ttsVoicesExpanded = ref(false);
const currentTtsVoiceMeta = computed(() => {
  const id = ttsVoice.value || DEFAULT_TTS_VOICE;
  return TTS_VOICES.find((v) => v.id === id) ?? TTS_VOICES[0];
});
const review = ref("");
const rounds = ref(0);
const advHistory = ref([]);
const chatListEl = ref(null);
const studentName = ref("");
const rawContent = ref("等待创建会话...");
const menuVisible = ref(false);
const menuX = ref(0);
const menuY = ref(0);
const menuText = ref("");
let eventSource = null;
/** POST 流式（携带卡片/长上下文）时用于中止 */
let streamAbortController = null;
let playingAudio = null;
const ttsAbortRef = ref(null);
/** 语音播报开启时：最后一条助手气泡显示「播报」动效（占位 / 同步出字 / 合成中） */
const voiceAssistantAnimating = ref(false);

/** 首条 thinking/delta 到达后停止等待计时 */
watch([streamingHasThinking, streamingHasAnswer], ([hasThink, hasAnswer]) => {
  if (hasThink || hasAnswer) stopStreamWait();
});

/** 语音播报模式下 SSE 阶段占位，避免用户先读完再听 */
const VOICE_SSE_PLACEHOLDER = "「语音播报」回答生成中…";

/** 大块 SSE delta 时用 rAF 渐进展示，减轻「一段一段」跳跃感（仅非语音播报模式） */
let cancelAnswerStreamReveal = () => {};

let voiceRevealStop = null;

function stopVoiceReveal() {
  if (voiceRevealStop) {
    voiceRevealStop();
    voiceRevealStop = null;
  }
}

/** 按音频进度（无 duration 时用估算）流式露出朗读稿；结束或出错后恢复完整回答。 */
function attachSyncedTextReveal(audio, spoken, updateContent, fullAnswerRestore, onComplete) {
  stopVoiceReveal();
  let stopped = false;
  let rafId = 0;
  let durationMode = false;

  const applyRatio = (ratio) => {
    const r = Math.min(1, Math.max(0, ratio));
    const n = Math.floor(spoken.length * r);
    updateContent(spoken.slice(0, n));
  };

  const onTimeUpdate = () => {
    const d = audio.duration;
    if (d && Number.isFinite(d) && d > 0) {
      durationMode = true;
      applyRatio(audio.currentTime / d);
    }
  };

  audio.addEventListener("timeupdate", onTimeUpdate);

  const startedAt = performance.now();
  const estMs = Math.max(4500, spoken.length * 90);

  const fallbackLoop = () => {
    if (stopped) return;
    if (durationMode) return;
    const d = audio.duration;
    if (d && Number.isFinite(d) && d > 0) return;
    const elapsed = performance.now() - startedAt;
    applyRatio(elapsed / estMs);
    if (!stopped) rafId = requestAnimationFrame(fallbackLoop);
  };

  rafId = requestAnimationFrame(fallbackLoop);

  const cleanup = () => {
    if (stopped) return;
    stopped = true;
    audio.removeEventListener("timeupdate", onTimeUpdate);
    cancelAnimationFrame(rafId);
  };

  voiceRevealStop = cleanup;

  const finish = () => {
    cleanup();
    voiceRevealStop = null;
    updateContent(fullAnswerRestore);
    onComplete?.();
  };

  audio.addEventListener("ended", finish, { once: true });
  audio.addEventListener("error", finish, { once: true });
}

function isVoiceLiveBubble(idx, item) {
  return (
    useVoiceOutput.value &&
    voiceAssistantAnimating.value &&
    item.role === "assistant" &&
    idx === history.value.length - 1
  );
}

/** 打断助手侧输出：流式生成、朗读稿同步、TTS 播放；便于话筒优先 */
async function interruptAssistantOutput() {
  stopVoiceReveal();
  cancelAnswerStreamReveal();
  ttsAbortRef.value?.abort();
  if (playingAudio) {
    playingAudio.pause();
    playingAudio = null;
  }
  voiceAssistantAnimating.value = false;
  if (!isStreaming.value || !currentSessionId.value) return;
  const student = loggedInStudentId.value;
  if (!student) return;
  try {
    await apiPost(
      `/api/chat-sessions/${encodeURIComponent(currentSessionId.value)}/messages/stop?student_id=${encodeURIComponent(student)}`,
      {}
    );
  } catch (_) {}
  eventSource?.close();
  eventSource = null;
  streamAbortController?.abort();
  streamAbortController = null;
  isStreaming.value = false;
  stopStreamWait();
}

const currentModel = computed(() => models.value.find((m) => m.usercode === usercode.value));

/** 跳转简历编辑器：写入 pending + history.state，避免进入页后被默认简历覆盖 */
function openResumeEditorWithRender(payload, event) {
  if (payload && typeof payload === "object") {
    dispatchResumeRender(payload);
  }
  if (route.path === "/resume/create") return;
  const q = loggedInStudentId.value ? { student_id: loggedInStudentId.value } : {};
  if (event?.preventDefault) event.preventDefault();
  router.push({
    path: "/resume/create",
    query: q,
    state: payload && typeof payload === "object" ? { resumeRender: { ...payload } } : {}
  });
}

const isJobPlannerRole = computed(() => {
  if (usercode.value === JOB_PLANNER_USERCODE) return true;
  const name = currentModel.value?.role_name || "";
  return /岗位规划师|job.?planner/i.test(name);
});

const isResumeOptimizerRole = computed(() => {
  if (usercode.value === RESUME_OPTIMIZER_USERCODE) return true;
  const name = currentModel.value?.role_name || "";
  return /简历优化|resume.?optim/i.test(name);
});

const isMockInterviewerRole = computed(() => {
  if (usercode.value === MOCK_INTERVIEWER_USERCODE) return true;
  const name = currentModel.value?.role_name || "";
  return /模拟面试|mock.?interview/i.test(name);
});

/** 遮层内流式展示的助手正文（与会话框最后一气泡同步） */
const interviewStreamingAnswer = computed(() => {
  if (!interviewModeActive.value || !isStreaming.value) return "";
  let streamText = "";
  for (let i = history.value.length - 1; i >= 0; i--) {
    if (history.value[i].role === "assistant") {
      streamText = String(history.value[i].content || "").trim();
      break;
    }
  }
  if (!streamText) return "";
  // interview_turn 若已写入 turns，不再重复展示流式气泡
  const last = interviewOverlayTurns.value[interviewOverlayTurns.value.length - 1];
  if (last?.role === "interviewer" && last.text === streamText) return "";
  return streamText;
});

/** 遮层展示用对话流（回看已答 / 当前题） */
const interviewOverlayDisplayTurns = computed(() => {
  if (interviewOverlayViewMode.value === "review") {
    return interviewOverlayReviewTurns.value;
  }
  return interviewOverlayTurns.value;
});

function resetInterviewOverlayView() {
  interviewOverlayViewMode.value = "live";
  interviewOverlaySelectedSeq.value = null;
  interviewOverlayReviewTurns.value = [];
}

/** 单条消息是否为规划预览（刷新后 usercode 未同步时仍可展示操作条） */
function isInterviewPlanPreviewMessage(item) {
  return shouldShowInterviewPlanActionBar(item) && Boolean(resolvePlanIdFromMessage(item));
}

function shouldShowPlanStartBar(item) {
  return (isMockInterviewerRole.value || isInterviewPlanPreviewMessage(item)) && currentSessionId.value;
}

/** 岗位规划师、简历优化师、模拟面试官均展示右侧「我的资料」 */
const hasContextRailRole = computed(
  () =>
    isJobPlannerRole.value || isResumeOptimizerRole.value || isMockInterviewerRole.value
);

const contextRailVisible = computed(() => contextRailVisibleRef(usercode.value).value);

const { recording, busy: voiceBusy, hint: voiceHint, toggleRecord, micLabel } = useVoiceRecorder(
  () => currentModel.value?.model_level || "mid",
  (t) => {
    message.value = message.value ? `${message.value.trim()} ${t}` : t;
  },
  {
    beforeTranscript: interruptAssistantOutput,
    onAutoSend: async () => {
      if (!currentSessionId.value || !message.value.trim()) return;
      await interruptAssistantOutput();
      sendMessage();
    }
  }
);
const selectedStudentMeta = computed(() => {
  const sid = loggedInStudentId.value;
  if (!sid) return "未登录：请先在登录页填写学号";
  if (!studentName.value) return `student_id：${sid}（未匹配学生）`;
  return `学号：${sid}\n姓名：${studentName.value}`;
});
const sessionInfo = computed(() => {
  if (!currentSessionId.value) return "";
  return `session_id: ${currentSessionId.value}` + (usercode.value ? ` | usercode: ${usercode.value}` : "");
});

async function loadModels() {
  models.value = await apiGet("/api/user-models");
  if (!usercode.value && models.value.length) usercode.value = models.value[0].usercode;
}

async function loadSessions() {
  if (!loggedInStudentId.value) return (sessions.value = []);
  sessions.value = await apiGet(
    `/api/chat-sessions?student_id=${encodeURIComponent(loggedInStudentId.value)}`
  );
}

async function loadStudentMeta() {
  const sid = loggedInStudentId.value;
  if (!sid) {
    studentName.value = "";
    return;
  }
  try {
    const data = await apiGet(`/api/students/${encodeURIComponent(sid)}`);
    studentName.value = data?.["学生基本信息"]?.["姓名"] || "";
  } catch (_) {
    studentName.value = "";
  }
}

function requireLoggedInStudentId() {
  const sid = loggedInStudentId.value;
  if (!sid) {
    throw new Error("请先在登录页登录学号");
  }
  return sid;
}

async function openSession(sid) {
  const student = requireLoggedInStudentId();
  currentSessionId.value = sid;
  localStorage.setItem("session_id", sid);
  const matched = (sessions.value || []).find((s) => s.session_id === sid);
  if (matched?.usercode) {
    usercode.value = matched.usercode;
    localStorage.setItem("usercode", matched.usercode);
  }
  const data = await apiGet(
    `/api/chat-sessions/${encodeURIComponent(sid)}/history?student_id=${encodeURIComponent(student)}`
  );
  history.value = hydrateSessionResumeRenderCache(sid, data.history || []);
  history.value = hydrateSessionInterviewPlanPreviewCache(sid, history.value);
  history.value = await hydrateInterviewPlanStartHistory(sid, student, history.value);
  thinkingText.value = "";
  rawContent.value = JSON.stringify(data, null, 2);
}

function generateSessionId() {
  return `${loggedInStudentId.value}-${Date.now()}`;
}

async function createSession() {
  const sid = loggedInStudentId.value;
  if (!sid || !usercode.value.trim()) {
    error.value = sid ? "请选择对话角色" : "请先在登录页登录学号";
    return;
  }
  const payload = await apiPost("/api/chat-sessions/init", {
    session_id: generateSessionId(),
    student_id: sid,
    usercode: usercode.value.trim()
  });
  localStorage.setItem("usercode", usercode.value.trim());
  await openSession(payload.session.session_id);
  await loadSessions();
  rawContent.value = JSON.stringify(payload, null, 2);
}

async function resetSession() {
  currentSessionId.value = "";
  localStorage.removeItem("session_id");
  history.value = [];
  thinkingText.value = "";
  review.value = "";
  rounds.value = 0;
  advHistory.value = [];
  rawContent.value = "等待创建会话...";
}

async function removeSession(sid) {
  const student = requireLoggedInStudentId();
  await apiDelete(
    `/api/chat-sessions/${encodeURIComponent(sid)}?student_id=${encodeURIComponent(student)}`
  );
  if (sid === currentSessionId.value) await resetSession();
  await loadSessions();
}

async function stopStreaming() {
  await interruptAssistantOutput();
}

function rebuildComposerHiddenContext() {
  composerHiddenContext.value = composerAttachments.value
    .map((a) => a.message_context)
    .filter(Boolean)
    .join("\n\n---\n\n");
}

function removeComposerAttachment(index) {
  composerAttachments.value.splice(index, 1);
  rebuildComposerHiddenContext();
}

function hasUserContextCards(item) {
  return Array.isArray(item?.context_cards) && item.context_cards.length > 0;
}

function placeholderCardFromRef(ref) {
  return {
    type: ref.type,
    ref_id: ref.ref_id,
    title: ref.title || ref.ref_id,
    subtitle: ref.subtitle || "",
    variant: ref.variant
  };
}

async function addComposerAttachmentFromRef(ref) {
  if (!ref?.ref_id) return;
  const dup = composerAttachments.value.some(
    (a) => a.card?.type === ref.type && a.card?.ref_id === ref.ref_id
  );
  if (dup) return;

  const placeholder = {
    card: placeholderCardFromRef(ref),
    message_context: "",
    loading: true
  };
  composerAttachments.value.push(placeholder);
  const slotIndex = composerAttachments.value.length - 1;
  error.value = "";

  try {
    const { card, message_context } = await fetchContextDetail(ref, loggedInStudentId.value);
    if (slotIndex >= composerAttachments.value.length) return;
    const current = composerAttachments.value[slotIndex];
    if (current?.card?.type !== ref.type || current?.card?.ref_id !== ref.ref_id) return;
    composerAttachments.value[slotIndex] = { card, message_context, loading: false };
    rebuildComposerHiddenContext();
  } catch (e) {
    if (
      slotIndex < composerAttachments.value.length &&
      composerAttachments.value[slotIndex]?.card?.ref_id === ref.ref_id
    ) {
      composerAttachments.value.splice(slotIndex, 1);
    }
    error.value = e.message || "加载引用详情失败";
  }
}

function onComposerDragOver(ev) {
  if (ev.dataTransfer?.types?.includes(CONTEXT_DRAG_MIME)) {
    ev.preventDefault();
    composerDropActive.value = true;
    ev.dataTransfer.dropEffect = "copy";
  }
}

function onComposerDragLeave() {
  composerDropActive.value = false;
}

async function onComposerDrop(ev) {
  ev.preventDefault();
  composerDropActive.value = false;
  const raw = ev.dataTransfer?.getData(CONTEXT_DRAG_MIME);
  if (!raw) return;
  try {
    const ref = JSON.parse(raw);
    await addComposerAttachmentFromRef(ref);
  } catch (_) {
    error.value = "无法解析拖入的引用";
  }
}

async function sendMessage(override = {}) {
  if (isStreaming.value) {
    await stopStreaming();
    return;
  }
  const userText = String(override.message ?? message.value).trim();
  const interviewHidden = String(override.interviewHiddenContext ?? "").trim();
  const readyAttachments = composerAttachments.value.filter((a) => !a.loading);
  const hasLoadingCards = composerAttachments.value.some((a) => a.loading);
  const hasCards = readyAttachments.length > 0;
  if (hasLoadingCards) {
    error.value = "请等待资料卡片加载完成后再发送";
    return;
  }
  if (!currentSessionId.value || (!userText && !hasCards && !interviewHidden)) {
    error.value = "请先进入会话并输入消息，或拖入资料卡片";
    return;
  }
  const student = loggedInStudentId.value;
  if (!student) {
    error.value = "请先在登录页登录学号";
    return;
  }
  const contextCards = readyAttachments.map((a) => a.card);
  let hiddenContext = readyAttachments
    .map((a) => a.message_context)
    .filter(Boolean)
    .join("\n\n---\n\n");
  if (interviewHidden) {
    hiddenContext = hiddenContext
      ? `${hiddenContext}\n\n---\n\n${interviewHidden}`
      : interviewHidden;
  }
  if (!override.keepComposer) {
    message.value = "";
    composerAttachments.value = [];
    composerHiddenContext.value = "";
  }
  error.value = "";
  thinkingText.value = "";
  streamingHasThinking.value = false;
  streamingHasAnswer.value = false;
  review.value = "";
  rounds.value = 0;
  advHistory.value = [];
  voiceAssistantAnimating.value = false;
  isStreaming.value = true;
  startStreamWait();
  history.value.push({
    role: "user",
    content: userText,
    context_cards: contextCards.length ? contextCards : undefined
  });
  history.value.push({ role: "assistant", content: "" });
  if (useVoiceOutput.value) {
    voiceAssistantAnimating.value = true;
  }
  const localHistorySnapshot = history.value.map((t) => ({ ...t }));
  const adversarialDescText =
    "你是严格审查员，优先检查答非所问、事实错误、逻辑漏洞和不可执行建议。";
  const usePostStream = hasCards || Boolean(hiddenContext);
  /** SSE 正常结束时服务端会关连接，浏览器仍可能触发 error，不能与真实失败混淆 */
  let streamEndedOk = false;

  const closeStreamTransport = () => {
    eventSource?.close();
    eventSource = null;
    if (streamAbortController) {
      streamAbortController.abort();
      streamAbortController = null;
    }
  };

  cancelAnswerStreamReveal();
  let answerTextBuffer = "";
  let answerDisplayedLen = 0;
  let answerStreamRaf = 0;

  const stopAnswerRevealLoop = () => {
    if (answerStreamRaf) {
      cancelAnimationFrame(answerStreamRaf);
      answerStreamRaf = 0;
    }
  };
  cancelAnswerStreamReveal = stopAnswerRevealLoop;

  const tickAnswerReveal = () => {
    const idx = history.value.length - 1;
    if (idx < 0 || history.value[idx].role !== "assistant") {
      stopAnswerRevealLoop();
      return;
    }
    const backlog = answerTextBuffer.length - answerDisplayedLen;
    if (backlog <= 0) {
      answerStreamRaf = 0;
      return;
    }
    const step = Math.min(backlog, Math.max(1, Math.ceil(backlog / 14) + 2));
    answerDisplayedLen += step;
    history.value[idx].content = answerTextBuffer.slice(0, answerDisplayedLen);
    if (chatListEl.value) {
      chatListEl.value.scrollTop = chatListEl.value.scrollHeight;
    }
    answerStreamRaf = requestAnimationFrame(tickAnswerReveal);
  };

  const scheduleAnswerReveal = () => {
    if (!answerStreamRaf) {
      answerStreamRaf = requestAnimationFrame(tickAnswerReveal);
    }
  };

  const handleStreamDone = async (data) => {
    cancelAnswerStreamReveal();
    cancelAnswerStreamReveal = () => {};
    streamEndedOk = true;
    const preDoneLocal = history.value.map((t) => ({ ...t }));
    history.value = mergePersistedHistory(data.history || [], preDoneLocal, {
      resume_render: data.resume_render,
      job_recommend: data.job_recommend
    });
    if (data.job_recommend) {
      attachJobRecommendToAssistant(data.job_recommend);
    }
    if (data.resume_render) {
      attachResumeRenderToAssistant(data.resume_render);
      dispatchResumeRender(data.resume_render);
    }
    saveSessionResumeRenderCache(currentSessionId.value, history.value);
    saveSessionInterviewPlanPreviewCache(currentSessionId.value, history.value);
    const finalThink = String(data.thinking != null ? data.thinking : thinkingText.value || "").trim();
    streamingHasThinking.value = false;
    streamingHasAnswer.value = false;
    if (finalThink) {
      for (let i = history.value.length - 1; i >= 0; i--) {
        if (history.value[i].role === "assistant") {
          history.value[i] = { ...history.value[i], thinking: finalThink };
          break;
        }
      }
    }
    thinkingText.value = "";
    review.value = data.adversarial_review || "";
    rounds.value = data.adversarial_rounds_used || 0;
    advHistory.value = Array.isArray(data.adversarial_history) ? data.adversarial_history : [];
    rawContent.value = JSON.stringify(data, null, 2);
    isStreaming.value = false;
    stopStreamWait();
    closeStreamTransport();
    await loadSessions();
    await nextTick();
    if (chatListEl.value) chatListEl.value.scrollTop = chatListEl.value.scrollHeight;

    let aiIdx = -1;
    for (let i = history.value.length - 1; i >= 0; i--) {
      if (history.value[i].role === "assistant") {
        aiIdx = i;
        break;
      }
    }
    let fullAnswer = String(data.answer || "").trim();
    if (!fullAnswer && aiIdx >= 0) {
      fullAnswer = String(history.value[aiIdx]?.content || "").trim();
    }

    if (interviewModeActive.value && fullAnswer) {
      pushInterviewOverlayTurn("interviewer", fullAnswer);
    }

    if (useVoiceOutput.value && aiIdx >= 0) {
      voiceAssistantAnimating.value = true;
      history.value[aiIdx].content = "「语音播报」正在准备朗读稿与音频…";
      await nextTick();
      await runVoiceBroadcastPipeline(fullAnswer, aiIdx);
    } else {
      voiceAssistantAnimating.value = false;
    }
  };

  const onStreamEvent = async (eventName, data) => {
    if (eventName === "job_recommend") {
      attachJobRecommendToAssistant(data);
      streamingHasAnswer.value = true;
      if (chatListEl.value) {
        chatListEl.value.scrollTop = chatListEl.value.scrollHeight;
      }
      return;
    }
    if (eventName === "resume_render") {
      attachResumeRenderToAssistant(data);
      dispatchResumeRender(data);
      streamingHasAnswer.value = true;
      if (chatListEl.value) {
        chatListEl.value.scrollTop = chatListEl.value.scrollHeight;
      }
      return;
    }
    if (eventName === "interview_plan_preview") {
      attachInterviewPlanPreviewToAssistant(data);
      if (chatListEl.value) {
        chatListEl.value.scrollTop = chatListEl.value.scrollHeight;
      }
      return;
    }
    if (eventName === "interview_progress") {
      applyInterviewProgress(data);
      if (chatListEl.value) {
        chatListEl.value.scrollTop = chatListEl.value.scrollHeight;
      }
      return;
    }
    if (eventName === "interview_turn") {
      applyInterviewTurn(data);
      if (chatListEl.value) {
        chatListEl.value.scrollTop = chatListEl.value.scrollHeight;
      }
      return;
    }
    if (eventName === "thinking") {
      const piece = data.content || "";
      if (!piece) return;
      streamingHasThinking.value = true;
      thinkingText.value += piece;
      if (useVoiceOutput.value) {
        const idx = history.value.length - 1;
        if (idx >= 0 && history.value[idx].role === "assistant" && !streamingHasAnswer.value) {
          history.value[idx].content = "「语音播报」深度思考中…";
        }
      }
      return;
    }
    if (eventName === "delta") {
      const piece = data.content || "";
      if (!piece) return;
      const firstAnswerChunk = !streamingHasAnswer.value;
      streamingHasAnswer.value = true;
      const idx = history.value.length - 1;
      answerTextBuffer += piece;
      if (useVoiceOutput.value) {
        history.value[idx].content = VOICE_SSE_PLACEHOLDER;
      } else {
        if (streamingHasThinking.value && firstAnswerChunk) {
          answerDisplayedLen = 0;
        }
        scheduleAnswerReveal();
      }
      return;
    }
    if (eventName === "done") {
      await handleStreamDone(data);
      return;
    }
    if (eventName === "error") {
      cancelAnswerStreamReveal();
      cancelAnswerStreamReveal = () => {};
      if (!streamEndedOk) {
        isStreaming.value = false;
        voiceAssistantAnimating.value = false;
        streamingHasThinking.value = false;
        streamingHasAnswer.value = false;
        error.value = data.detail || "流式发送失败";
        stopStreamWait();
      }
      closeStreamTransport();
    }
  };

  const failStream = () => {
    cancelAnswerStreamReveal();
    cancelAnswerStreamReveal = () => {};
    if (streamEndedOk) return;
    isStreaming.value = false;
    voiceAssistantAnimating.value = false;
    streamingHasThinking.value = false;
    streamingHasAnswer.value = false;
    error.value = "流式发送失败";
    stopStreamWait();
    closeStreamTransport();
  };

  if (usePostStream) {
    streamAbortController = new AbortController();
    const streamBody = {
      message: userText,
      message_context: hiddenContext,
      context_cards: contextCards,
      student_id: student,
      use_role_pipeline: useRolePipeline.value,
      use_adversarial_harness: useAdversarialHarness.value,
      adversarial_desc: adversarialDescText
    };
    void apiPostSse(
      `/api/chat-sessions/${encodeURIComponent(currentSessionId.value)}/messages/stream`,
      streamBody,
      {
        signal: streamAbortController.signal,
        onEvent: (name, data) => {
          void onStreamEvent(name, data);
        }
      }
    )
      .catch((e) => {
        if (e?.name === "AbortError") return;
        error.value = e.message || "流式发送失败";
        failStream();
      })
      .finally(() => {
        if (streamAbortController) streamAbortController = null;
      });
    return;
  }

  const streamParams = new URLSearchParams({
    message: userText,
    student_id: student,
    use_role_pipeline: useRolePipeline.value ? "true" : "false",
    use_adversarial_harness: useAdversarialHarness.value ? "true" : "false",
    adversarial_desc: adversarialDescText
  });
  const streamUrl = `/api/chat-sessions/${encodeURIComponent(currentSessionId.value)}/messages/stream?${streamParams}`;
  eventSource = new EventSource(streamUrl);
  eventSource.addEventListener("job_recommend", (evt) => {
    try {
      void onStreamEvent("job_recommend", JSON.parse(evt.data || "{}"));
    } catch (_) {
      /* ignore */
    }
  });
  eventSource.addEventListener("resume_render", (evt) => {
    try {
      void onStreamEvent("resume_render", JSON.parse(evt.data || "{}"));
    } catch (_) {
      /* ignore */
    }
  });
  eventSource.addEventListener("interview_plan_preview", (evt) => {
    try {
      void onStreamEvent("interview_plan_preview", JSON.parse(evt.data || "{}"));
    } catch (_) {
      /* ignore */
    }
  });
  eventSource.addEventListener("thinking", (evt) => {
    void onStreamEvent("thinking", JSON.parse(evt.data || "{}"));
  });
  eventSource.addEventListener("delta", (evt) => {
    void onStreamEvent("delta", JSON.parse(evt.data || "{}"));
  });
  eventSource.addEventListener("done", (evt) => {
    try {
      void onStreamEvent("done", JSON.parse(evt.data || "{}"));
    } catch (_) {
      isStreaming.value = false;
      stopStreamWait();
      voiceAssistantAnimating.value = false;
      error.value = "流式结果解析失败";
      closeStreamTransport();
    }
  });
  eventSource.addEventListener("error", () => {
    failStream();
  });
}

function onContextMenu(evt) {
  const selected = String(window.getSelection ? window.getSelection().toString() : "").trim();
  if (evt.target?.closest?.(".session-raw-panel")) {
    const full = String(rawContent.value ?? "").trim();
    const text = selected || full;
    if (!text) return;
    evt.preventDefault();
    menuText.value = text;
    menuVisible.value = true;
    menuX.value = evt.clientX;
    menuY.value = evt.clientY;
    return;
  }
  const bubble = String(evt.target?.closest(".msg")?.innerText || "").trim();
  const text = selected || bubble;
  if (!text) return;
  evt.preventDefault();
  menuText.value = text;
  menuVisible.value = true;
  menuX.value = evt.clientX;
  menuY.value = evt.clientY;
}

function hideMenu() {
  menuVisible.value = false;
  menuText.value = "";
}

async function copyMenuText() {
  if (!menuText.value) return hideMenu();
  try {
    await navigator.clipboard.writeText(menuText.value);
  } catch (_) {
    error.value = "复制失败，请手动复制";
  } finally {
    hideMenu();
  }
}

function persistFlags() {
  localStorage.setItem("use_role_pipeline", useRolePipeline.value ? "1" : "0");
  localStorage.setItem("use_adversarial_harness", useAdversarialHarness.value ? "1" : "0");
}

/** 助手消息上的思考正文：流式用 thinkingText，完成后用条目上的 thinking */
function assistantThinkingDisplay(idx, item) {
  if (item.role !== "assistant") return "";
  const last = history.value.length - 1;
  if (idx === last && isStreaming.value && thinkingText.value) return thinkingText.value;
  return String(item.thinking || "").trim();
}

/** 流式阶段：有思考且尚无正文时，回答气泡显示占位 */
function assistantBubblePlaceholder(idx, item) {
  if (item.role !== "assistant" || idx !== history.value.length - 1 || !isStreaming.value) return "";
  if (streamingHasThinking.value || streamingHasAnswer.value) {
    return useVoiceOutput.value ? "「语音播报」深度思考中…" : "深度思考中…";
  }
  const wait = streamWaitRunning.value ? streamWaitLabel.value : "";
  return wait ? `等待回复中… ${wait}` : "等待回复中…";
}

/** 助手正文：Markdown → 安全 HTML（用户消息仍用纯文本） */
function assistantMessageHtml(content) {
  return renderChatMarkdown(content);
}

function assistantMessageMdClass(content) {
  return ["msg-body-md"];
}

function hasJobRecommend(item) {
  const jr = item?.job_recommend;
  if (!jr || typeof jr !== "object") return false;
  if (Array.isArray(jr.jobs) && jr.jobs.length) return true;
  const rec = jr.recommendation;
  if (rec && Array.isArray(rec.recommended_jobs) && rec.recommended_jobs.length) return true;
  return Boolean(rec?.no_match_detail);
}

function attachJobRecommendToAssistant(payload) {
  if (!payload || typeof payload !== "object") return;
  const idx = history.value.length - 1;
  if (idx < 0 || history.value[idx].role !== "assistant") return;
  history.value[idx] = {
    ...history.value[idx],
    job_recommend: payload
  };
}

function hasResumeRender(item) {
  return hasResumeRenderPayload(item?.resume_render);
}

function attachResumeRenderToAssistant(payload) {
  if (!payload || typeof payload !== "object") return;
  const idx = history.value.length - 1;
  if (idx < 0 || history.value[idx].role !== "assistant") return;
  history.value[idx] = {
    ...history.value[idx],
    resume_render: payload
  };
  saveSessionResumeRenderCache(currentSessionId.value, history.value);
}

/** 规划预览结构化载荷（含 plan_id），供「开始」按钮创建面试记录 */
function attachInterviewPlanPreviewToAssistant(payload) {
  if (!payload || typeof payload !== "object") return;
  const idx = history.value.length - 1;
  if (idx < 0 || history.value[idx].role !== "assistant") return;
  history.value[idx] = {
    ...history.value[idx],
    interview_plan_preview: payload
  };
  saveSessionInterviewPlanPreviewCache(currentSessionId.value, history.value);
}

function onInterviewPlanStarted(itemIdx, data) {
  if (itemIdx < 0 || !history.value[itemIdx]) return;
  history.value[itemIdx] = {
    ...history.value[itemIdx],
    interview_session_started: true,
    interview_start_result: data
  };
}

function pushInterviewOverlayTurn(role, text) {
  const t = String(text || "").trim();
  if (!t || t === "开始正式面试") return;
  const last = interviewOverlayTurns.value[interviewOverlayTurns.value.length - 1];
  if (last && last.role === role && last.text === t) return;
  interviewOverlayTurns.value.push({ role, text: t });
}

async function loadInterviewOverlayQuestions(studentId, recordId) {
  try {
    const resp = await fetchInterviewRecordAnswers(studentId, recordId);
    return Array.isArray(resp?.items) ? resp.items : [];
  } catch {
    return [];
  }
}

function syncCurrentQuestionFromList() {
  const session = interviewModeSession.value;
  if (!session) return;
  const items = interviewOverlayQuestions.value;
  if (!items.length) return;
  const seq = session.seqNo;
  const hit =
    (seq != null ? findQuestionBySeq(items, seq) : null) ||
    (session.questionId ? items.find((q) => q.question_id === session.questionId) : null) ||
    pickFirstIncompleteQuestion(items) ||
    items[0];
  if (hit) {
    interviewModeSession.value = {
      ...session,
      seqNo: hit.seq_no ?? session.seqNo,
      questionId: hit.question_id || session.questionId,
      currentQuestionIndex: hit.seq_no ?? session.currentQuestionIndex,
      currentQuestionText: hit.question_text || session.currentQuestionText,
      questionTotal: items.length
    };
  }
}

function onInterviewProgressDotSelect({ seqNo, kind }) {
  if (kind === "pending") return;
  const item = findQuestionBySeq(interviewOverlayQuestions.value, seqNo);
  if (!item) return;
  if (kind === "done") {
    interviewOverlayViewMode.value = "review";
    interviewOverlaySelectedSeq.value = Number(seqNo);
    interviewOverlayReviewTurns.value = buildReviewTurnsFromAnswerItem(item);
    return;
  }
  resetInterviewOverlayView();
  syncCurrentQuestionFromList();
}

function onInterviewBackToLive() {
  resetInterviewOverlayView();
}

/** 规划预览气泡点击「进入」：打开遮层并发送 start 指令 */
async function onInterviewPlanEnter(payload) {
  const studentId = loggedInStudentId.value;
  const recordId = String(payload?.record_id || "").trim();
  const interviewSessionId = String(payload?.interview_session_id || "").trim();
  const planId = String(payload?.plan_id || "").trim();
  const chatSessionId = String(payload?.chat_session_id || currentSessionId.value || "").trim();
  if (!studentId || !recordId) {
    error.value = "缺少面试记录信息，无法进入";
    return;
  }
  const ctxKey = String(payload?.ctx_key || buildCtxKey(studentId, recordId));
  const questions = await loadInterviewOverlayQuestions(studentId, recordId);
  interviewOverlayQuestions.value = questions;
  interviewOverlayTurns.value = [];
  resetInterviewOverlayView();
  const active = pickFirstIncompleteQuestion(questions) || questions[0];
  const resuming = hasInterviewProgress(questions);
  interviewModeSession.value = {
    studentId,
    recordId,
    interviewSessionId,
    planId,
    chatSessionId,
    ctxKey,
    questionTotal: questions.length || null,
    questionAnswered: questions.filter((q) =>
      ["completed", "answered", "summarized"].includes(String(q.answer_status || "").toLowerCase())
    ).length,
    currentQuestionIndex: active?.seq_no ?? 0,
    seqNo: active?.seq_no ?? 0,
    questionId: active?.question_id || "",
    currentQuestionText: active?.question_text || "",
    phase: resuming ? "question" : "ready"
  };
  interviewOverlayQuestions.value = reconcileQuestionStatuses(
    interviewOverlayQuestions.value,
    interviewModeSession.value
  );
  interviewModeActive.value = true;
  const hidden = buildInterviewStartContext({
    studentId,
    recordId,
    interviewSessionId,
    chatSessionId,
    planId,
    ctxKey
  });
  await sendMessage({
    message: resuming ? "继续正式面试" : "开始正式面试",
    interviewHiddenContext: hidden,
    keepComposer: true
  });
}

/** 遮层内发送单题回答 */
async function onInterviewOverlaySend(answerText) {
  if (!interviewModeSession.value) return;
  pushInterviewOverlayTurn("user", answerText);
  const hidden = buildInterviewAnswerContext(interviewModeSession.value, answerText);
  await sendMessage({
    message: answerText,
    interviewHiddenContext: hidden,
    keepComposer: true
  });
}

function onInterviewOverlayExit() {
  interviewModeActive.value = false;
  interviewModeSession.value = null;
  interviewOverlayQuestions.value = [];
  interviewOverlayTurns.value = [];
  resetInterviewOverlayView();
}

function applyInterviewTurn(data) {
  if (!interviewModeActive.value || !data || data.mode !== "interview") return;
  // 遮层本题对话在 stream done 时统一写入 turns；此处仅同步题干，避免与 delta 流式气泡重复
  const qText = String(data.interviewer?.question_text || "").trim();
  if (qText && interviewModeSession.value) {
    interviewModeSession.value = {
      ...interviewModeSession.value,
      currentQuestionText: qText
    };
  }
}

function applyInterviewProgress(progress) {
  if (!progress || progress.mode !== "interview") return;
  const prevSeq = interviewModeSession.value?.seqNo;
  interviewModeSession.value = mergeProgressIntoSession(interviewModeSession.value, progress);
  if (progress.current_question_text) {
    interviewModeSession.value = {
      ...interviewModeSession.value,
      currentQuestionText: progress.current_question_text
    };
  }
  interviewOverlayQuestions.value = reconcileQuestionStatuses(
    interviewOverlayQuestions.value,
    interviewModeSession.value
  );
  syncCurrentQuestionFromList();

  const nextSeq = interviewModeSession.value?.seqNo;
  const seqChanged =
    progress.question_advanced === true ||
    (prevSeq != null && nextSeq != null && Number(prevSeq) !== Number(nextSeq));
  if (seqChanged) {
    interviewOverlayTurns.value = [];
    resetInterviewOverlayView();
  }
  if (progress.evaluator_status === "complete" || progress.question_advanced) {
    void refreshInterviewOverlayQuestions().then(() => {
      interviewOverlayQuestions.value = reconcileQuestionStatuses(
        interviewOverlayQuestions.value,
        interviewModeSession.value
      );
      syncCurrentQuestionFromList();
    });
  }
  if (progress.phase === "completed" && progress.evaluator_status === "complete") {
    interviewModeActive.value = false;
  }
}

async function refreshInterviewOverlayQuestions() {
  const session = interviewModeSession.value;
  if (!session?.studentId || !session?.recordId) return;
  interviewOverlayQuestions.value = await loadInterviewOverlayQuestions(
    session.studentId,
    session.recordId
  );
}

function persistVoiceFlags() {
  localStorage.setItem("chat_voice_input", useVoiceInput.value ? "1" : "0");
  localStorage.setItem("chat_voice_output", useVoiceOutput.value ? "1" : "0");
  if (!useVoiceOutput.value) {
    voiceAssistantAnimating.value = false;
    ttsVoicesExpanded.value = false;
  }
}

function toggleChatSidebar() {
  toggleChatSidebarVisible();
}

function toggleContextRail() {
  toggleContextRailVisible(usercode.value);
}

const showContextRail = computed(() => hasContextRailRole.value && contextRailVisible.value);

function selectTtsVoice(id) {
  ttsVoice.value = saveTtsVoice(id);
  ttsVoicesExpanded.value = false;
}

/** 语音播报：先请求朗读稿 → 再仅流式 TTS；界面文字与音频进度大致同步，结束后恢复完整回答。 */
async function runVoiceBroadcastPipeline(fullAnswer, assistantIdx) {
  if (!useVoiceOutput.value) {
    voiceAssistantAnimating.value = false;
    return;
  }
  const answer = String(fullAnswer || "").trim();
  if (!answer) {
    voiceAssistantAnimating.value = false;
    return;
  }

  stopVoiceReveal();
  if (playingAudio) {
    playingAudio.pause();
    playingAudio = null;
  }
  ttsAbortRef.value?.abort();
  ttsAbortRef.value = new AbortController();
  const chatLevel = currentModel.value?.model_level || "mid";

  try {
    history.value[assistantIdx].content = "「语音播报」正在生成朗读稿…";
    const pr = await apiPost("/api/voice/spoken-summary/text", {
      answer_text: answer,
      chat_model_level: chatLevel
    });
    const spoken = String(pr.text || "").trim();
    if (!spoken) throw new Error("朗读稿为空");

    history.value[assistantIdx].content = "「语音播报」正在合成语音…";
    const resp = await fetchTtsPostStream(
      "/api/voice/speech/stream",
      {
        text: spoken,
        model_level: "mid",
        voice: ttsVoice.value || DEFAULT_TTS_VOICE
      },
      { signal: ttsAbortRef.value.signal }
    );

    history.value[assistantIdx].content = "";
    const audio = await playTtsStreamFromResponse(resp);
    playingAudio = audio;

    attachSyncedTextReveal(
      audio,
      spoken,
      (slice) => {
        history.value[assistantIdx].content = slice;
      },
      answer,
      () => {
        voiceAssistantAnimating.value = false;
        if (playingAudio === audio) playingAudio = null;
      }
    );
  } catch (err) {
    voiceAssistantAnimating.value = false;
    if (err?.name === "AbortError") return;
    history.value[assistantIdx].content = answer;
    error.value = err.message || "语音播报失败";
  }
}

onMounted(async () => {
  try {
    await loadModels();
    await loadStudentMeta();
    await loadSessions();
    if (currentSessionId.value && loggedInStudentId.value) {
      await openSession(currentSessionId.value);
    }
  } catch (err) {
    error.value = err.message || "加载失败";
  }
  document.addEventListener("click", hideMenu);
});

onBeforeUnmount(() => {
  eventSource?.close();
  streamAbortController?.abort();
  streamAbortController = null;
  stopVoiceReveal();
  cancelAnswerStreamReveal();
  ttsAbortRef.value?.abort();
  voiceAssistantAnimating.value = false;
  if (playingAudio) {
    playingAudio.pause();
    playingAudio = null;
  }
  document.removeEventListener("click", hideMenu);
});
</script>

<template>
  <div
    class="app"
    :class="{
      'app-sidebar-hidden': !chatSidebarVisible,
      'app-planner-rail': showContextRail
    }"
  >
    <aside v-show="chatSidebarVisible" class="sidebar">
      <div class="sidebar-toolbar">
        <span class="sidebar-toolbar-label">会话与列表</span>
        <button type="button" class="secondary sidebar-hide-btn" @click="toggleChatSidebar">收起侧栏</button>
      </div>
      <div class="section-title">会话配置</div>
      <div class="row">
        <label>学号</label>
        <input
          class="readonly-field"
          :value="loggedInStudentId"
          readonly
          placeholder="请先在登录页登录"
        />
      </div>
      <p v-if="!loggedInStudentId" class="session-meta">
        未登录，请前往 <router-link to="/login">登录页</router-link> 填写学号。
      </p>
      <div class="selected-model-meta" style="white-space: pre-line;">{{ selectedStudentMeta }}</div>
      <div class="row">
        <label>对话内置角色</label>
        <select v-model="usercode">
          <option v-for="m in models" :key="m.usercode" :value="m.usercode">{{ m.role_name || m.username }} ({{ m.usercode }})</option>
        </select>
      </div>
      <div class="row input-line">
        <button @click="createSession">创建 / 进入会话</button>
        <button class="secondary" @click="resetSession">新建会话</button>
      </div>
      <div class="selected-model-meta">
        角色：{{ currentModel?.role_name || "-" }}<br />
        模型档位：{{ currentModel?.model_level || "-" }}
      </div>
      <div v-if="useVoiceOutput" class="row voice-row">
        <label>TTS 发音人</label>
        <button type="button" class="tts-voice-fold-trigger" @click="ttsVoicesExpanded = !ttsVoicesExpanded">
          <div
            class="voice-card voice-card-preview"
            :class="[
              currentTtsVoiceMeta.gender === 'male' ? 'voice-male' : 'voice-female',
              'active'
            ]"
          >
            <span class="voice-card-title">{{ currentTtsVoiceMeta.title }}</span>
            <span class="voice-card-accent">{{ currentTtsVoiceMeta.accent }}</span>
            <span class="voice-card-blurb">{{ currentTtsVoiceMeta.blurb }}</span>
            <span class="voice-card-id">{{ currentTtsVoiceMeta.id }}</span>
          </div>
          <span class="tts-fold-meta">{{ ttsVoicesExpanded ? "收起" : "展开全部" }}</span>
          <span class="tts-fold-chevron" :class="{ open: ttsVoicesExpanded }" aria-hidden="true">▼</span>
        </button>
        <div v-show="ttsVoicesExpanded" class="tts-voice-fold-panel">
          <p class="voice-legend">
            <span class="leg leg-female">粉 · 女声</span>
            <span class="leg leg-male">蓝 · 男声</span>
          </p>
          <div class="voice-card-grid">
            <button
              v-for="v in TTS_VOICES"
              :key="v.id"
              type="button"
              class="voice-card"
              :class="[
                v.gender === 'male' ? 'voice-male' : 'voice-female',
                { active: ttsVoice === v.id }
              ]"
              @click="selectTtsVoice(v.id)"
            >
              <span class="voice-card-title">{{ v.title }}</span>
              <span class="voice-card-accent">{{ v.accent }}</span>
              <span class="voice-card-blurb">{{ v.blurb }}</span>
              <span class="voice-card-id">{{ v.id }}</span>
            </button>
          </div>
        </div>
      </div>
      <div class="section-title">会话列表</div>
      <div class="session-list">
        <div v-for="s in sessions" :key="s.session_id" class="session-item" :class="{ active: s.session_id === currentSessionId }">
          <div class="session-main" @click="openSession(s.session_id)">
            <div><strong>{{ s.session_id }}</strong></div>
            <div class="session-meta">{{ s.role_name || s.usercode }} | {{ s.model_level || "-" }}</div>
          </div>
          <div class="session-actions">
            <button class="secondary" @click="removeSession(s.session_id)">删除</button>
          </div>
        </div>
      </div>
      <p class="session-meta">{{ sessionInfo }}</p>
      <p class="error">{{ error }}</p>
      <details class="adv-toggle session-raw-toggle">
        <summary>展开会话内容</summary>
        <div class="msg-body session-raw-panel" @contextmenu="onContextMenu">
          <pre class="session-raw-pre">{{ rawContent }}</pre>
        </div>
      </details>
    </aside>

    <section class="main">
      <div class="main-header">
        <div>
          <div class="brand">{{ currentModel?.role_name || "请选择角色" }}</div>
          <div class="header-meta">
            角色：{{ currentModel?.role_name || "未进入" }} | 会话：{{ currentSessionId || "未进入" }} | 模型：{{ currentModel?.username || "未进入" }}
            <span v-if="isStreaming && streamWaitRunning" class="stream-wait-pill">等待 {{ streamWaitLabel }}</span>
          </div>
        </div>
        <div class="main-header-actions">
          <button
            v-if="!chatSidebarVisible"
            type="button"
            class="secondary sidebar-show-btn"
            @click="toggleChatSidebar"
          >
            展开侧栏
          </button>
          <button
            v-if="hasContextRailRole && !contextRailVisible"
            type="button"
            class="secondary planner-rail-show-btn"
            @click="toggleContextRail"
          >
            展开我的资料
          </button>
        </div>
      </div>

      <div ref="chatListEl" class="chat-list" @contextmenu="onContextMenu">
        <p v-if="!history.length" class="empty-tip">创建会话后开始聊天</p>
        <template v-for="(item, idx) in history" :key="idx">
          <div v-if="item.role === 'user'" class="msg msg-user msg-user--with-refs">
            <div v-if="hasUserContextCards(item)" class="msg-context-cards">
              <ContextRefCard
                v-for="(c, ci) in item.context_cards"
                :key="c.type + '-' + c.ref_id + '-' + ci"
                :card="c"
                compact
              />
            </div>
            <div v-if="item.content" class="msg-body">{{ item.content }}</div>
          </div>
          <div v-else class="assistant-turn-wrap">
            <details v-if="assistantThinkingDisplay(idx, item)" class="msg msg-think-fold">
              <summary class="think-summary">
                <span class="think-icon" aria-hidden="true">◈</span>
                <span class="think-summary-label">思考过程</span>
                <span class="think-summary-hint">点击展开</span>
              </summary>
              <div class="msg-body think-inner">{{ assistantThinkingDisplay(idx, item) }}</div>
            </details>
            <div
              class="msg"
              :class="[
                'msg-assistant',
                isVoiceLiveBubble(idx, item) ? 'msg-voice-live' : '',
                hasJobRecommend(item) ? 'msg-assistant--job-rec' : ''
              ]"
            >
              <div v-if="isVoiceLiveBubble(idx, item)" class="msg-voice-head" aria-hidden="true">
                <span class="voice-wave">
                  <i></i><i></i><i></i><i></i><i></i>
                </span>
                <span class="voice-live-label">播报中</span>
              </div>
              <div
                v-if="assistantBubblePlaceholder(idx, item)"
                class="msg-body msg-body-thinking-placeholder"
              >
                {{ assistantBubblePlaceholder(idx, item) }}
              </div>
              <div
                v-else-if="isVoiceLiveBubble(idx, item)"
                class="msg-body msg-body-voice-out"
              >
                {{ item.content }}
              </div>
              <div
                v-else-if="hasJobRecommend(item)"
                class="msg-body msg-body-job-rec"
              >
                <p v-if="item.content" class="msg-rec-intro">{{ item.content }}</p>
                <JobRecommendPanel
                  :jobs="item.job_recommend.jobs || []"
                  :recommendation="item.job_recommend.recommendation"
                  :rag="item.job_recommend.rag"
                  :cache="item.job_recommend.cache"
                  compact
                />
              </div>
              <div
                v-else-if="hasResumeRender(item)"
                class="msg-body msg-body-resume-render"
              >
                <div
                  v-if="item.content"
                  class="msg-rec-intro"
                  :class="assistantMessageMdClass(item.content)"
                  v-html="assistantMessageHtml(item.content)"
                />
                <p class="resume-render-hint">
                  结构化简历已写入
                  <a
                    href="/resume/create"
                    class="resume-render-link"
                    @click.prevent="openResumeEditorWithRender(item.resume_render, $event)"
                  >简历编辑器</a>
                  （页面已打开时会自动填入左侧表单）。
                  <button
                    type="button"
                    class="resume-render-apply-btn"
                    @click="openResumeEditorWithRender(item.resume_render)"
                  >再次填入</button>
                </p>
              </div>
              <div
                v-else
                class="msg-body"
                :class="assistantMessageMdClass(item.content)"
                v-html="assistantMessageHtml(item.content)"
              />
              <ChatInterviewPlanStartBar
                v-if="
                  shouldShowPlanStartBar(item) &&
                  shouldShowInterviewPlanActionBar(item) &&
                  resolvePlanIdFromMessage(item)
                "
                :plan-id="resolvePlanIdFromMessage(item)"
                :plan-version="resolvePlanVersionFromMessage(item)"
                :student-id="loggedInStudentId"
                :chat-session-id="currentSessionId"
                :disabled="isStreaming && idx === history.length - 1"
                @started="onInterviewPlanStarted(idx, $event)"
                @enter="onInterviewPlanEnter"
              />
            </div>
          </div>
        </template>
        <details v-if="useAdversarialHarness && (review || advHistory.length)" class="msg msg-adversarial adv-toggle">
          <summary>深度思考轮次：{{ rounds }}（点击展开/收起）</summary>
          <div class="msg-body">{{ review }}</div>
          <details v-if="advHistory.length" class="adv-toggle adv-rounds-details">
            <summary>展开逐轮对抗详情</summary>
            <div class="msg-body adv-rounds-scrollable">
              <template v-for="(a, i) in advHistory" :key="i">
                <div><strong>Round {{ a.round || i + 1 }} - 回答：</strong></div>
                <div>{{ a.answer || "（空）" }}</div>
                <div><strong>Round {{ a.round || i + 1 }} - 审查：</strong></div>
                <div>{{ a.review || "（空）" }}</div>
                <br />
              </template>
            </div>
          </details>
        </details>
      </div>

      <div class="composer">
        <div class="composer-top">
          <button
            type="button"
            class="toggle-wrap"
            :class="{ active: useRolePipeline }"
            title="开启：对用户问题做降噪，并压缩历史对话再送给模型，减少跑题与冗长上下文干扰。"
            @click="useRolePipeline = !useRolePipeline; persistFlags();"
          >
            纯净思考：{{ useRolePipeline ? "开" : "关" }}
          </button>
          <button
            type="button"
            class="toggle-wrap"
            :class="{ active: useAdversarialHarness }"
            title="开启：用「审查员」多轮审回答、再改稿，更偏严谨；关闭则单轮直出，速度更快。"
            @click="useAdversarialHarness = !useAdversarialHarness; persistFlags();"
          >
            深度思考：{{ useAdversarialHarness ? "开" : "关" }}
          </button>
          <button
            type="button"
            class="toggle-wrap"
            :class="{ active: useVoiceInput }"
            title="开启后可用麦克风持续识别并写入输入框；助手正在回复时，新识别会打断当前生成与播报。"
            @click="useVoiceInput = !useVoiceInput; persistVoiceFlags();"
          >
            语音输入：{{ useVoiceInput ? "开" : "关" }}
          </button>
          <button
            type="button"
            class="toggle-wrap"
            :class="{ active: useVoiceOutput }"
            title="开启后：回复结束后生成朗读稿并 TTS 播报；播报时正文可与音频进度大致同步，播完显示全文。"
            @click="useVoiceOutput = !useVoiceOutput; persistVoiceFlags();"
          >
            语音播报：{{ useVoiceOutput ? "开" : "关" }}
          </button>
        </div>
        <div
          class="composer-drop-zone"
          :class="{ 'composer-drop-zone--active': composerDropActive }"
          @dragover="onComposerDragOver"
          @dragleave="onComposerDragLeave"
          @drop="onComposerDrop"
        >
          <input type="hidden" name="message_context" :value="composerHiddenContext" />
          <div v-if="composerAttachments.length" class="composer-attachments">
            <ContextRefCard
              v-for="(att, ai) in composerAttachments"
              :key="att.card.type + '-' + att.card.ref_id + '-' + ai"
              :card="att.card"
              :loading="Boolean(att.loading)"
              compact
              removable
              @remove="removeComposerAttachment(ai)"
            />
          </div>
          <p v-else-if="hasContextRailRole" class="composer-ref-hint">可将右侧「我的资料」卡片拖入此处</p>
          <div class="composer-input-row">
            <textarea
              v-model="message"
              placeholder="文字输入，或拖入右侧资料卡片…"
              @keydown.enter.exact.prevent="sendMessage"
            />
            <div v-if="useVoiceInput" class="voice-input-side">
            <button
              type="button"
              class="mic-chat"
              :class="{ on: recording, disabled: voiceBusy && !recording }"
              :disabled="voiceBusy && !recording"
              @click="toggleRecord"
            >
              🎤 {{ micLabel }}
            </button>
            <p v-if="voiceHint" class="voice-input-hint">{{ voiceHint }}</p>
          </div>
          </div>
        </div>
        <div class="composer-actions">
          <span>
            开语音播报时：助手文字先占位，朗读稿就绪后随音频进度显示，播完恢复全文。语音输入默认持续聆听（手动关闭话筒）
          </span>
          <button
            type="button"
            class="send-btn"
            :class="{ 'stop-mode': isStreaming }"
            :aria-label="isStreaming ? '生成中，点击停止' : '发送消息'"
            @click="sendMessage"
          >
            <span v-if="isStreaming" class="stop-btn-inner">
              <span class="stop-btn-icon" aria-hidden="true" />
              <span class="stop-btn-label">
                <span class="stop-btn-main">
                  生成中<span class="stop-btn-dots" aria-hidden="true"><i /><i /><i /></span>
                </span>
                <span class="stop-btn-sub">
                  <span v-if="streamWaitRunning">已等待 {{ streamWaitLabel }} · </span>点击停止
                </span>
              </span>
            </span>
            <span v-else>发送</span>
          </button>
        </div>
      </div>
    </section>

    <ChatPlannerContextRail
      v-if="showContextRail"
      :student-id="loggedInStudentId"
      :usercode="usercode"
      class="planner-context-rail"
    />

    <div v-if="menuVisible" class="bubble-context-menu" :style="{ left: `${menuX}px`, top: `${menuY}px` }">
      <button type="button" @click.stop="copyMenuText">复制</button>
    </div>

    <ChatInterviewOverlay
      :active="interviewModeActive"
      :session="interviewModeSession"
      :questions="interviewOverlayQuestions"
      :turns="interviewOverlayDisplayTurns"
      :view-mode="interviewOverlayViewMode"
      :selected-seq-no="interviewOverlaySelectedSeq"
      :streaming="isStreaming"
      :streaming-thinking="thinkingText"
      :streaming-answer="interviewStreamingAnswer"
      @send="onInterviewOverlaySend"
      @exit="onInterviewOverlayExit"
      @select-question="onInterviewProgressDotSelect"
      @back-to-live="onInterviewBackToLive"
    />
  </div>
</template>

<style scoped>
.app {
  height: 100vh;
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 14px;
  padding: 14px;
  max-width: 1300px;
  margin: 0 auto;
  background: radial-gradient(circle at top right, #eef2ff, transparent), radial-gradient(circle at top left, #f5f3ff, transparent), var(--bg-color);
}
.app.app-planner-rail {
  max-width: min(1680px, 100%);
  grid-template-columns: 320px 1fr minmax(248px, 288px);
}
.app.app-planner-rail.app-sidebar-hidden {
  grid-template-columns: 1fr minmax(248px, 288px);
}
.planner-context-rail {
  min-height: 0;
}
.app.app-sidebar-hidden:not(.app-planner-rail) {
  grid-template-columns: 1fr;
}
.app.app-sidebar-hidden {
  grid-template-rows: 1fr;
  max-width: min(1920px, 100%);
  width: 100%;
  padding: 8px 12px;
  gap: 0;
  box-sizing: border-box;
  height: 100dvh;
  min-height: 100vh;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.08), transparent),
    var(--bg-color);
}
.app.app-sidebar-hidden .main {
  min-height: 0;
  height: 100%;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(15, 23, 42, 0.06);
  --msg-bubble-max-height: min(46vh, 420px);
}
.app.app-sidebar-hidden .main-header {
  padding: 12px clamp(16px, 3vw, 40px);
  flex-wrap: wrap;
  row-gap: 8px;
}
.app.app-sidebar-hidden .brand {
  font-size: 1.05rem;
}
.app.app-sidebar-hidden .header-meta {
  font-size: 12px;
  line-height: 1.45;
  max-width: 100%;
}
.app.app-sidebar-hidden .chat-list {
  padding: 18px clamp(16px, 3.5vw, 56px) 24px;
  background: linear-gradient(180deg, #fafbff 0%, #f4f6fb 55%, #f1f5f9 100%);
}
.app.app-sidebar-hidden .msg,
.app.app-sidebar-hidden .assistant-turn-wrap {
  max-width: min(85%, 920px);
}
.app.app-sidebar-hidden .msg {
  font-size: 14px;
  line-height: 1.55;
  padding: 12px 14px;
}
.app.app-sidebar-hidden .msg-body {
  line-height: 1.55;
}
.app.app-sidebar-hidden .composer {
  padding: 14px clamp(16px, 3.5vw, 56px) 16px;
  background: rgba(255, 255, 255, 0.96);
  border-top-color: #e8eaf0;
}
.app.app-sidebar-hidden .composer-top {
  margin-bottom: 10px;
}
.app.app-sidebar-hidden textarea {
  min-height: 80px;
  max-height: min(36vh, 360px);
}
.app.app-sidebar-hidden .empty-tip {
  margin-top: min(12vh, 120px);
  font-size: 14px;
}
.sidebar { background: rgba(255, 255, 255, 0.82); border: 1px solid var(--line); border-radius: 18px; box-shadow: 0 18px 34px rgba(0, 0, 0, 0.06); padding: 14px; overflow: auto; min-width: 0; }
.sidebar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: -2px 0 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}
.sidebar-toolbar-label { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.sidebar-hide-btn { flex-shrink: 0; font-size: 11px; padding: 5px 10px; white-space: nowrap; }
.readonly-field {
  background: #f3f4f6;
  color: var(--text-muted);
  cursor: not-allowed;
}
.main-header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-shrink: 0;
}
.sidebar-show-btn,
.planner-rail-show-btn {
  flex-shrink: 0;
  font-size: 12px;
  padding: 6px 12px;
  white-space: nowrap;
}
.sidebar .session-raw-toggle { margin-top: 10px; }
.sidebar .session-raw-panel {
  margin-top: 6px;
  max-height: min(42vh, 320px);
  overflow: auto;
  overflow-wrap: anywhere;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafafa;
  min-height: 0;
  -webkit-overflow-scrolling: touch;
}
.sidebar .session-raw-pre {
  margin: 0;
  padding: 8px 10px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 11px;
  line-height: 1.4;
  color: #374151;
  user-select: text;
}
.main {
  background: rgba(255,255,255,.9);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: 0 18px 34px rgba(0,0,0,.06);
  display: grid;
  grid-template-rows: auto 1fr auto;
  overflow: hidden;
  /* 对话气泡与输入区共用最大可视高度 */
  --msg-bubble-max-height: min(40vh, 320px);
}
.main-header { padding: 14px 16px; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; gap: 10px; background: rgba(255, 255, 255, 0.86); }
.brand { font-weight: 700; background: linear-gradient(to right, var(--primary-color), var(--secondary-color)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.header-meta { margin-top: 4px; color: var(--text-muted); font-size: 12px; }
.stream-wait-pill {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #fef3c7;
  color: #b45309;
  font-weight: 600;
  font-size: 11px;
}
.section-title { margin: 8px 0 8px; color: var(--text-muted); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
.row { margin: 11px 0; }
label { display: block; margin-bottom: 6px; color: var(--text-muted); font-weight: 600; font-size: 12px; }
input, select, textarea, button { font-size: 14px; border-radius: 10px; border: 1px solid #d1d5db; }
input, select, textarea { width: 100%; padding: 10px 12px; }
button { padding: 10px 14px; border: none; background: var(--primary-color); color: #fff; cursor: pointer; font-weight: 600; }
.secondary { background: #fff; color: var(--text-main); border: 1px solid #d1d5db; }
.input-line { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.selected-model-meta { margin-top: 8px; padding: 8px 10px; border: 1px dashed #d9d9de; border-radius: 10px; color: #6e6e73; font-size: 12px; line-height: 1.45; background: #fafafc; }
.session-list { margin-top: 6px; display: grid; gap: 8px; }
.session-item { border: 1px solid #e5e5ea; background: #fff; border-radius: 12px; padding: 8px; }
.session-item.active { border-color: rgba(99, 102, 241, .45); box-shadow: 0 0 0 3px rgba(99, 102, 241, .11); }
.session-main { cursor: pointer; font-size: 12px; color: #1d1d1f; line-height: 1.4; }
.session-meta { color: #6e6e73; font-size: 11px; margin-top: 4px; }
.session-actions { display: flex; justify-content: flex-end; margin-top: 6px; }
.chat-list {
  padding: 16px;
  overflow: auto;
  background: linear-gradient(180deg, #fbfbff 0%, #f8fafc 100%);
}
.empty-tip { color: var(--text-muted); text-align: center; margin-top: 80px; }
.msg { margin: 7px 0; width: fit-content; max-width: min(76%, 860px); padding: 10px 12px; border-radius: 18px; font-size: 13px; line-height: 1.45; }
.msg.msg-user,
.msg.msg-assistant {
  display: flex;
  flex-direction: column;
  max-height: var(--msg-bubble-max-height);
  overflow: hidden;
  min-height: 0;
}
.msg.msg-user .msg-body,
.msg.msg-assistant .msg-body {
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  flex: 1 1 auto;
  -webkit-overflow-scrolling: touch;
}
.msg-user { margin-left: auto; background: linear-gradient(180deg, #7c83f7 0%, #6366f1 100%); color: #fff; border-bottom-right-radius: 8px; }
.msg-user--with-refs .msg-context-cards {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 8px;
}
.msg-user--with-refs .ctx-ref {
  border-color: rgba(255, 255, 255, 0.35);
}
.msg-user--with-refs .ctx-ref-title {
  color: #f8fafc;
}
.msg-user--with-refs .ctx-ref-sub {
  color: rgba(255, 255, 255, 0.82);
}
.msg-user--with-refs .ctx-ref-badge {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}
.composer-drop-zone {
  border: 1px dashed transparent;
  border-radius: 12px;
  padding: 8px;
  transition: border-color 0.15s, background 0.15s;
}
.composer-drop-zone--active {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.06);
}
.composer-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.composer-ref-hint {
  margin: 0 0 8px;
  font-size: 0.75rem;
  color: #9ca3af;
}
.composer-ref-hint.muted {
  color: #9ca3af;
}
.msg-assistant { margin-right: auto; background: #fff; border: 1px solid #e6e6eb; border-bottom-left-radius: 8px; }
.msg-assistant.msg-assistant--job-rec {
  width: 100%;
  max-width: min(96%, 920px);
  max-height: min(70vh, 560px);
}
.msg-body.msg-body-job-rec {
  white-space: normal;
  padding: 2px 0 0;
  touch-action: pan-y;
  overscroll-behavior: contain;
}
.msg-assistant .msg-rec-intro {
  flex-shrink: 0;
  margin: 0 0 10px;
  font-size: 0.9rem;
  line-height: 1.5;
  color: #374151;
}
.msg-body.msg-body-resume-render {
  white-space: normal;
}
.resume-render-hint {
  margin: 10px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  font-size: 0.88rem;
  color: #065f46;
  line-height: 1.5;
}
.resume-render-link {
  color: #047857;
  font-weight: 600;
  text-decoration: underline;
}
.resume-render-apply-btn {
  margin-left: 8px;
  padding: 2px 10px;
  font-size: 0.8rem;
  border-radius: 8px;
  border: 1px solid #6ee7b7;
  background: #fff;
  color: #047857;
  cursor: pointer;
}
.assistant-turn-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  width: 100%;
  max-width: min(76%, 860px);
}
.assistant-turn-wrap:has(.msg-assistant--job-rec) {
  max-width: min(96%, 920px);
}
.msg-think-fold {
  margin: 0;
  margin-right: auto;
  width: 100%;
  max-width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  border-radius: 0;
}
.msg-think-fold .think-summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 10px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
  user-select: none;
  border: 1px solid #e5e7eb;
  width: fit-content;
  max-width: 100%;
}
.msg-think-fold .think-summary::-webkit-details-marker { display: none; }
.msg-think-fold .think-icon { color: #9ca3af; font-size: 10px; }
.msg-think-fold .think-summary-hint { font-weight: 500; color: #9ca3af; font-size: 11px; }
.msg-think-fold[open] .think-summary {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #4f46e5;
}
.msg-think-fold[open] .think-summary-hint { color: #6366f1; }
.msg-think-fold .think-inner {
  margin-top: 6px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fafafa;
  border: 1px solid #ececf0;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.5;
  max-height: var(--msg-bubble-max-height);
  overflow-x: hidden;
  overflow-y: auto;
  min-height: 0;
  -webkit-overflow-scrolling: touch;
}
.msg-body-thinking-placeholder {
  color: #9ca3af;
  font-style: italic;
}
.msg-voice-live {
  border-color: rgba(99, 102, 241, 0.5);
  animation: voiceBubblePulse 1.35s ease-in-out infinite;
}
@keyframes voiceBubblePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.18); }
  50% { box-shadow: 0 0 14px 2px rgba(99, 102, 241, 0.16); }
}
.msg-voice-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-shrink: 0;
}
.voice-live-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #4f46e5;
  text-transform: uppercase;
}
.voice-wave {
  display: inline-flex;
  align-items: flex-end;
  gap: 3px;
  height: 18px;
}
.voice-wave i {
  display: block;
  width: 4px;
  min-height: 6px;
  border-radius: 2px;
  background: linear-gradient(180deg, #818cf8, #6366f1);
  transform-origin: bottom center;
  animation: voiceBar 0.85s ease-in-out infinite;
}
.voice-wave i:nth-child(1) { animation-delay: 0s; }
.voice-wave i:nth-child(2) { animation-delay: 0.1s; }
.voice-wave i:nth-child(3) { animation-delay: 0.2s; }
.voice-wave i:nth-child(4) { animation-delay: 0.15s; }
.voice-wave i:nth-child(5) { animation-delay: 0.05s; }
@keyframes voiceBar {
  0%, 100% { transform: scaleY(0.38); opacity: 0.65; }
  50% { transform: scaleY(1); opacity: 1; }
}
.msg-body-voice-out {
  animation: voiceTextGlow 1.15s ease-in-out infinite alternate;
}
@keyframes voiceTextGlow {
  from { text-shadow: none; color: #111827; }
  to { text-shadow: 0 0 12px rgba(99, 102, 241, 0.38); color: #312e81; }
}
.msg-adversarial { margin-right: auto; background: #f7f8ff; border: 1px solid #cfd7ff; border-bottom-left-radius: 8px; }
.msg.msg-adversarial > .msg-body {
  max-height: var(--msg-bubble-max-height);
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  -webkit-overflow-scrolling: touch;
}
.msg.msg-adversarial .adv-toggle {
  display: flex;
  flex-direction: column;
  max-height: var(--msg-bubble-max-height);
  overflow: hidden;
  min-height: 0;
  margin-top: 8px;
}
.msg.msg-adversarial .adv-toggle > summary {
  flex-shrink: 0;
}
.msg.msg-adversarial .adv-toggle > .msg-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
}
/* 逐轮对抗：嵌套 details 内给内容区固定上限，保证气泡内可滚动、不被裁切 */
.msg.msg-adversarial .adv-rounds-details {
  min-height: 0;
}
.msg.msg-adversarial .adv-rounds-scrollable {
  max-height: min(56vh, 480px);
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}
.adv-toggle { margin-top: 6px; border: 1px solid #d9dffb; border-radius: 10px; background: #fff; padding: 6px 8px; }
.adv-toggle > summary { cursor: pointer; color: #2f4eb3; font-size: 12px; font-weight: 600; }
.msg-body { white-space: pre-wrap; word-break: break-word; line-height: 1.3; }

/* 助手 Markdown 渲染（岗位推荐 / 规划师回复） */
.msg-body.msg-body-md {
  white-space: normal;
  line-height: 1.55;
  font-size: 14px;
  color: #1f2937;
}
.msg-body.msg-body-md :deep(h1),
.msg-body.msg-body-md :deep(h2),
.msg-body.msg-body-md :deep(h3) {
  margin: 0.75em 0 0.4em;
  font-weight: 700;
  line-height: 1.35;
  color: #111827;
}
.msg-body.msg-body-md :deep(h1) { font-size: 1.15rem; }
.msg-body.msg-body-md :deep(h2) { font-size: 1.05rem; }
.msg-body.msg-body-md :deep(h3) { font-size: 0.98rem; color: #374151; }
.msg-body.msg-body-md :deep(h1:first-child),
.msg-body.msg-body-md :deep(h2:first-child),
.msg-body.msg-body-md :deep(h3:first-child) {
  margin-top: 0;
}
.msg-body.msg-body-md :deep(p) {
  margin: 0.45em 0;
}
.msg-body.msg-body-md :deep(ul),
.msg-body.msg-body-md :deep(ol) {
  margin: 0.35em 0 0.5em;
  padding-left: 1.35em;
}
.msg-body.msg-body-md :deep(li) {
  margin: 0.25em 0;
}
.msg-body.msg-body-md :deep(li > p) {
  margin: 0.15em 0;
}
.msg-body.msg-body-md :deep(strong) {
  color: #111827;
  font-weight: 650;
}
.msg-body.msg-body-md :deep(em) {
  color: #4b5563;
}
.msg-body.msg-body-md :deep(a) {
  color: #4f46e5;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.msg-body.msg-body-md :deep(code) {
  font-size: 0.88em;
  padding: 0.1em 0.35em;
  border-radius: 4px;
  background: #f3f4f6;
  color: #4338ca;
}
.msg-body.msg-body-md :deep(pre) {
  margin: 0.5em 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  overflow-x: auto;
  font-size: 12px;
  line-height: 1.45;
}
.msg-body.msg-body-md :deep(pre code) {
  padding: 0;
  background: transparent;
  color: #1e293b;
}
.msg-body.msg-body-md :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.35em 0 0.35em 12px;
  border-left: 3px solid #c7d2fe;
  color: #6b7280;
}
.msg-body.msg-body-md :deep(hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 0.75em 0;
}
.msg-body.msg-body-md--job-rec :deep(h2:first-of-type) {
  padding-bottom: 0.35em;
  border-bottom: 1px solid #e0e7ff;
  color: #4338ca;
}
.msg-body.msg-body-md--job-rec :deep(ol > li) {
  list-style: none;
  margin: 0.65em 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f9fafb;
  border: 1px solid #ececf0;
}
.msg-body.msg-body-md--job-rec :deep(ol) {
  padding-left: 0;
}

.composer { border-top: 1px solid var(--line); padding: 12px; background: rgba(255,255,255,.92); }
.composer-top { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }
.toggle-wrap { background: #fff; color: #6b7280; border: 1px solid #e0e0e6; border-radius: 999px; font-size: 12px; padding: 6px 10px; }
.toggle-wrap.active { border-color: rgba(99, 102, 241, .45); box-shadow: 0 0 0 3px rgba(99, 102, 241, .12); background: #f3f4ff; color: #4f46e5; }
.composer-input-row { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: start; }
.voice-input-side { display: flex; flex-direction: column; align-items: stretch; gap: 6px; min-width: 108px; }
.mic-chat {
  border: 1px solid #e0e0e6;
  border-radius: 999px;
  padding: 10px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  background: #fff;
  color: #4f46e5;
}
.mic-chat.on { background: #dc2626; color: #fff; border-color: #dc2626; box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.25); }
.mic-chat:disabled { opacity: 0.5; cursor: not-allowed; }
.voice-input-hint { margin: 0; font-size: 11px; color: #6e6e73; line-height: 1.35; max-width: 120px; }
textarea {
  width: 100%;
  min-height: 70px;
  max-height: var(--msg-bubble-max-height);
  resize: vertical;
}
.composer-actions { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 8px; color: #6e6e73; font-size: 12px; }
.composer-actions .send-btn {
  flex-shrink: 0;
  min-width: 96px;
  border-radius: 12px;
  transition: transform 0.18s ease, box-shadow 0.22s ease, background 0.22s ease;
}
.composer-actions .send-btn:not(.stop-mode):hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.28);
}
.composer-actions .send-btn.stop-mode {
  position: relative;
  overflow: hidden;
  min-width: 132px;
  padding: 9px 14px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 48%, #b91c1c 100%);
  background-size: 200% 200%;
  color: #fff;
  box-shadow:
    0 0 0 1px rgba(220, 38, 38, 0.2),
    0 4px 14px rgba(220, 38, 38, 0.35),
    0 0 24px rgba(239, 68, 68, 0.22);
  animation: stop-btn-glow 2.4s ease-in-out infinite;
}
.composer-actions .send-btn.stop-mode::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    105deg,
    transparent 28%,
    rgba(255, 255, 255, 0.18) 46%,
    transparent 64%
  );
  transform: translateX(-120%);
  animation: stop-btn-shimmer 2.2s ease-in-out infinite;
  pointer-events: none;
}
.composer-actions .send-btn.stop-mode:hover {
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px rgba(220, 38, 38, 0.28),
    0 8px 20px rgba(220, 38, 38, 0.42),
    0 0 32px rgba(239, 68, 68, 0.3);
}
.composer-actions .send-btn.stop-mode:active {
  transform: translateY(0) scale(0.98);
}
.stop-btn-inner {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.stop-btn-icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  background: #fff;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.35);
  animation: stop-btn-pulse 1.4s ease-in-out infinite;
}
.stop-btn-label {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  line-height: 1.15;
  text-align: left;
}
.stop-btn-main {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.stop-btn-sub {
  font-size: 10px;
  font-weight: 600;
  opacity: 0.88;
  letter-spacing: 0.04em;
}
.stop-btn-dots {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: 1px;
}
.stop-btn-dots i {
  display: block;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.35;
  animation: stop-dot-bounce 1.1s ease-in-out infinite;
}
.stop-btn-dots i:nth-child(2) { animation-delay: 0.15s; }
.stop-btn-dots i:nth-child(3) { animation-delay: 0.3s; }
@keyframes stop-btn-glow {
  0%, 100% {
    background-position: 0% 50%;
    box-shadow:
      0 0 0 1px rgba(220, 38, 38, 0.2),
      0 4px 14px rgba(220, 38, 38, 0.32),
      0 0 20px rgba(239, 68, 68, 0.18);
  }
  50% {
    background-position: 100% 50%;
    box-shadow:
      0 0 0 1px rgba(220, 38, 38, 0.28),
      0 6px 18px rgba(220, 38, 38, 0.42),
      0 0 28px rgba(239, 68, 68, 0.28);
  }
}
@keyframes stop-btn-shimmer {
  0%, 100% { transform: translateX(-120%); }
  45%, 55% { transform: translateX(120%); }
}
@keyframes stop-btn-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(0.88); opacity: 0.82; }
}
@keyframes stop-dot-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
  30% { transform: translateY(-3px); opacity: 1; }
}
.error { color: var(--danger); min-height: 20px; font-size: 13px; font-weight: 600; margin-top: 8px; }
.bubble-context-menu { position: fixed; z-index: 1200; background: #fff; border: 1px solid #d9d9de; border-radius: 10px; box-shadow: 0 12px 26px rgba(0, 0, 0, 0.16); padding: 6px; min-width: 96px; }
.bubble-context-menu button { width: 100%; border-radius: 8px; border: 1px solid transparent; background: #fff; color: #1d1d1f; font-size: 12px; font-weight: 600; padding: 7px 10px; text-align: left; cursor: pointer; }
.bubble-context-menu button:hover { background: #f3f4ff; border-color: rgba(99, 102, 241, .28); }

.voice-row label { margin-bottom: 2px; }
.tts-voice-fold-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  margin-top: 4px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fafafa;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.tts-voice-fold-trigger:hover {
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
}
.tts-voice-fold-trigger .voice-card-preview {
  flex: 1;
  min-width: 0;
  cursor: inherit;
  margin: 0;
}
.tts-fold-meta {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
}
.tts-fold-chevron {
  flex-shrink: 0;
  font-size: 10px;
  color: #9ca3af;
  transition: transform 0.2s ease;
}
.tts-fold-chevron.open {
  transform: rotate(-180deg);
}
.tts-voice-fold-panel {
  margin-top: 10px;
}
.voice-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 11px;
  margin: 2px 0 8px;
}
.voice-legend .leg-female { color: #be185d; font-weight: 600; }
.voice-legend .leg-male { color: #1d4ed8; font-weight: 600; }
.voice-card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.voice-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 12px;
  border: 2px solid transparent;
  cursor: pointer;
  text-align: left;
  font-size: 12px;
  line-height: 1.35;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.voice-card.voice-female {
  background: linear-gradient(145deg, #fdf2f8 0%, #fce7f3 100%);
  border-color: #f9a8d4;
  color: #831843;
}
.voice-card.voice-female.active {
  border-color: #db2777;
  box-shadow: 0 0 0 3px rgba(219, 39, 119, 0.22);
}
.voice-card.voice-male {
  background: linear-gradient(145deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #93c5fd;
  color: #1e3a8a;
}
.voice-card.voice-male.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.22);
}
.voice-card-title { font-weight: 700; font-size: 13px; }
.voice-card-accent { font-size: 10px; opacity: 0.88; font-weight: 600; }
.voice-card-blurb { font-size: 11px; opacity: 0.92; }
.voice-card-id {
  font-size: 10px;
  opacity: 0.55;
  font-family: ui-monospace, monospace;
  margin-top: 2px;
}

@media (max-width: 960px) {
  .app { grid-template-columns: 1fr; height: auto; min-height: 100vh; }
  .msg { max-width: 92%; }
  .voice-card-grid { grid-template-columns: 1fr; }
}
</style>
