import { computed, onBeforeUnmount, ref } from "vue";
import { apiPostVoiceTranscribe } from "../api/client";
import { VOICE_ASR_SEGMENT } from "../config/voiceAsrSegment";

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * @param {() => string} getModelLevel ASR 档位
 * @param {(text: string) => void} onTranscript 每识别完一段追加文本
 * @param {{
 *   onAutoSend?: () => void | Promise<void>;
 *   beforeTranscript?: () => void | Promise<void>;
 * }} [options]
 */
export function useVoiceRecorder(getModelLevel, onTranscript, options = {}) {
  const recording = ref(false);
  const busy = ref(false);
  const hint = ref("");
  const cfg = VOICE_ASR_SEGMENT;
  const onAutoSend = typeof options.onAutoSend === "function" ? options.onAutoSend : null;
  const beforeTranscript =
    typeof options.beforeTranscript === "function" ? options.beforeTranscript : null;

  let mediaStream = null;
  let mediaRecorder = null;
  let audioContext = null;
  let analyser = null;
  let timeDomainData = null;
  let rafId = 0;

  let sessionActive = false;
  let userStopRequested = false;
  let pendingAutoSend = false;
  let chunks = [];
  let segmentStartPerf = 0;
  let hadVoiceInSegment = false;
  let hadSpeechEver = false;
  let silenceRunStart = null;
  let lastVoiceAt = 0;
  let mimeType = "";
  let lastAsrAt = 0;

  function pickMimeType() {
    const cands = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
    for (const c of cands) {
      if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(c)) {
        return c;
      }
    }
    return "";
  }

  function extForMime(mime) {
    if (!mime) return "webm";
    if (mime.includes("mp4")) return "m4a";
    return "webm";
  }

  function stopMonitor() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }
  }

  function teardownStreamAndContext() {
    stopMonitor();
    if (audioContext) {
      audioContext.close().catch(() => {});
      audioContext = null;
    }
    analyser = null;
    timeDomainData = null;
    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop());
      mediaStream = null;
    }
    mediaRecorder = null;
  }

  function computeRms() {
    if (!analyser || !timeDomainData) return 0;
    analyser.getByteTimeDomainData(timeDomainData);
    let sum = 0;
    for (let i = 0; i < timeDomainData.length; i++) {
      const x = (timeDomainData[i] - 128) / 128;
      sum += x * x;
    }
    return Math.sqrt(sum / timeDomainData.length);
  }

  function scheduleMonitorFrame() {
    rafId = requestAnimationFrame(monitorFrame);
  }

  function monitorFrame() {
    if (!sessionActive || userStopRequested) return;

    const now = performance.now();
    const rms = computeRms();
    const loud = rms >= cfg.silenceRmsThreshold;

    if (loud) {
      hadSpeechEver = true;
      hadVoiceInSegment = true;
      lastVoiceAt = now;
      silenceRunStart = null;
    } else if (hadVoiceInSegment) {
      if (silenceRunStart === null) silenceRunStart = now;
      const silenceDur = now - silenceRunStart;
      if (silenceDur >= cfg.silenceCutMs && mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        return;
      }
    }

    if (
      cfg.autoSendOnSilence &&
      onAutoSend &&
      hadSpeechEver &&
      lastVoiceAt > 0 &&
      now - lastVoiceAt >= cfg.silenceSendMs &&
      mediaRecorder &&
      mediaRecorder.state === "recording"
    ) {
      pendingAutoSend = true;
      stopMonitor();
      hint.value = cfg.continuousListening ? "静音超时，识别并发送…" : "静音超时，正在识别并发送…";
      if (!cfg.continuousListening) {
        userStopRequested = true;
        sessionActive = false;
      }
      mediaRecorder.stop();
      return;
    }

    if (
      hadVoiceInSegment &&
      now - segmentStartPerf >= cfg.maxSegmentMs &&
      mediaRecorder &&
      mediaRecorder.state === "recording"
    ) {
      mediaRecorder.stop();
      return;
    }

    scheduleMonitorFrame();
  }

  async function transcribeBlob(blob, ext) {
    const level = typeof getModelLevel === "function" ? getModelLevel() || "mid" : "mid";
    const gap = cfg.minAsrIntervalMs - (performance.now() - lastAsrAt);
    if (gap > 0) await sleep(gap);
    const data = await apiPostVoiceTranscribe(blob, `seg.${ext}`, level);
    lastAsrAt = performance.now();
    return (data.text || "").trim();
  }

  async function handleRecorderStop(forceLastSegment, snapChunks, snapMime, snapElapsed) {
    const blob = new Blob(snapChunks, { type: snapMime || mimeType || "audio/webm" });
    const ext = extForMime(snapMime || mimeType);

    const tooSmall =
      !forceLastSegment &&
      (blob.size < cfg.minSegmentBytes || snapElapsed < cfg.minSegmentMs);

    if (!tooSmall && blob.size > 0) {
      busy.value = true;
      hint.value = "识别本段…";
      try {
        const t = await transcribeBlob(blob, ext);
        if (t) {
          if (beforeTranscript) await beforeTranscript();
          onTranscript(t);
          hint.value = pendingAutoSend
            ? "识别完成"
            : cfg.continuousListening
              ? "聆听中，停顿自动切段"
              : "录音中，停顿将自动切段";
        } else if (!pendingAutoSend) {
          hint.value = "本段未识别到内容";
        }
      } catch (err) {
        hint.value = err.message || "识别失败";
      } finally {
        busy.value = false;
      }
    }

    if (pendingAutoSend) {
      pendingAutoSend = false;
      const stayOpen = !!(cfg.continuousListening && sessionActive && !userStopRequested);
      try {
        await onAutoSend?.();
      } catch (_) {}
      if (stayOpen && sessionActive && !userStopRequested) {
        hint.value = "聆听中，说完停顿后将发送";
        beginSegment();
        scheduleMonitorFrame();
        return;
      }
    }

    if (!sessionActive || userStopRequested) {
      recording.value = false;
      teardownStreamAndContext();
      hint.value = String(hint.value).includes("失败") ? hint.value : "已关闭话筒";
      return;
    }

    beginSegment();
    hint.value = cfg.continuousListening ? "聆听中，说完停顿后将发送" : "录音中，停顿将自动切段";
    scheduleMonitorFrame();
  }

  function beginSegment() {
    if (!sessionActive || userStopRequested || !mediaStream) return;
    chunks = [];
    segmentStartPerf = performance.now();
    hadVoiceInSegment = false;
    silenceRunStart = null;

    try {
      mediaRecorder = mimeType
        ? new MediaRecorder(mediaStream, { mimeType })
        : new MediaRecorder(mediaStream);
    } catch (_) {
      hint.value = "无法启动分段录音";
      sessionActive = false;
      recording.value = false;
      teardownStreamAndContext();
      return;
    }

    mediaRecorder.ondataavailable = (ev) => {
      if (ev.data && ev.data.size > 0) chunks.push(ev.data);
    };
    mediaRecorder.onstop = () => {
      const force = !!(userStopRequested || pendingAutoSend);
      const snapChunks = chunks.slice();
      const snapMime = (mediaRecorder && mediaRecorder.mimeType) || mimeType;
      const snapElapsed = performance.now() - segmentStartPerf;
      void handleRecorderStop(force, snapChunks, snapMime, snapElapsed);
    };
    mediaRecorder.start(200);
  }

  async function startRecording() {
    hint.value = "";
    if (recording.value || busy.value) return;
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (_) {
      hint.value = "无法访问麦克风，请检查浏览器权限";
      return;
    }

    mimeType = pickMimeType();
    try {
      audioContext = new AudioContext();
      await audioContext.resume();
      const source = audioContext.createMediaStreamSource(mediaStream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.4;
      source.connect(analyser);
      timeDomainData = new Uint8Array(analyser.fftSize);
    } catch (_) {
      if (mediaStream) {
        mediaStream.getTracks().forEach((t) => t.stop());
        mediaStream = null;
      }
      hint.value = "无法启动音频分析（分段识别不可用）";
      return;
    }

    sessionActive = true;
    userStopRequested = false;
    pendingAutoSend = false;
    hadSpeechEver = false;
    lastVoiceAt = 0;
    recording.value = true;
    hint.value = cfg.continuousListening ? "聆听中，说完停顿后将发送" : "录音中，停顿将自动切段";

    beginSegment();
    scheduleMonitorFrame();
  }

  function toggleRecord() {
    if (!recording.value) {
      if (busy.value) return;
      startRecording();
      return;
    }
    userStopRequested = true;
    sessionActive = false;
    pendingAutoSend = false;
    stopMonitor();
    hint.value = "关闭话筒…";
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    } else {
      recording.value = false;
      teardownStreamAndContext();
      hint.value = "已关闭话筒";
    }
  }

  const micLabel = computed(() =>
    recording.value ? (cfg.continuousListening ? "关闭话筒" : "停止") : cfg.continuousListening ? "开话筒" : "说话"
  );

  onBeforeUnmount(() => {
    userStopRequested = true;
    sessionActive = false;
    pendingAutoSend = false;
    stopMonitor();
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    teardownStreamAndContext();
  });

  return { recording, busy, hint, toggleRecord, micLabel };
}
