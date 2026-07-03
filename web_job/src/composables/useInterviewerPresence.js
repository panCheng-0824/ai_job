/**
 * 面试官呈现状态：idle / listening / speaking / thinking
 * 支持定时强制态 + 麦克风音量检测（学生说话 → listening）
 */
import { computed, onBeforeUnmount, ref } from "vue";

const SPEAK_MS_PER_CHAR = 85;
const MIN_SPEAK_MS = 1800;
const MAX_SPEAK_MS = 6000;

export function estimateSpeakDuration(text) {
  const len = String(text || "").trim().length;
  return Math.min(MAX_SPEAK_MS, Math.max(MIN_SPEAK_MS, len * SPEAK_MS_PER_CHAR));
}

export function useInterviewerPresence() {
  const forcedState = ref(null);
  const studentVoiceActive = ref(false);
  const micEnabled = ref(true);

  let forcedTimer = null;
  let voiceStop = null;

  const presenceState = computed(() => {
    if (forcedState.value) return forcedState.value;
    if (studentVoiceActive.value && micEnabled.value) return "listening";
    return "idle";
  });

  const presenceLabel = computed(() => {
    switch (presenceState.value) {
      case "speaking":
        return "面试官发言中";
      case "listening":
        return "正在聆听";
      case "thinking":
        return "思考中";
      default:
        return "等待开始";
    }
  });

  function clearForcedTimer() {
    if (forcedTimer) {
      clearTimeout(forcedTimer);
      forcedTimer = null;
    }
  }

  /** 强制进入某状态，到期后恢复自动判定 */
  function pushState(state, ms = 2000) {
    clearForcedTimer();
    forcedState.value = state;
    forcedTimer = setTimeout(() => {
      forcedState.value = null;
      forcedTimer = null;
    }, ms);
  }

  function speakFor(text, ms) {
    pushState("speaking", ms ?? estimateSpeakDuration(text));
  }

  function thinkFor(ms = 900) {
    pushState("thinking", ms);
  }

  function bindVoiceActivity(stream) {
    stopVoiceActivity();
    if (!stream || typeof window === "undefined") return;

    let audioCtx = null;
    let rafId = 0;
    let activeUntil = 0;

    try {
      audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const buf = new Uint8Array(analyser.frequencyBinCount);
      const threshold = 18;

      const tick = () => {
        analyser.getByteFrequencyData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i += 1) sum += buf[i];
        const avg = sum / buf.length;

        if (avg > threshold && micEnabled.value) {
          activeUntil = Date.now() + 280;
        }
        studentVoiceActive.value = Date.now() < activeUntil;
        rafId = requestAnimationFrame(tick);
      };

      rafId = requestAnimationFrame(tick);

      voiceStop = () => {
        cancelAnimationFrame(rafId);
        studentVoiceActive.value = false;
        source.disconnect();
        analyser.disconnect();
        audioCtx?.close?.();
        audioCtx = null;
        voiceStop = null;
      };
    } catch {
      studentVoiceActive.value = false;
    }
  }

  function stopVoiceActivity() {
    voiceStop?.();
    studentVoiceActive.value = false;
  }

  function setMicEnabled(on) {
    micEnabled.value = on;
    if (!on) studentVoiceActive.value = false;
  }

  onBeforeUnmount(() => {
    clearForcedTimer();
    stopVoiceActivity();
  });

  return {
    presenceState,
    presenceLabel,
    pushState,
    speakFor,
    thinkFor,
    bindVoiceActivity,
    stopVoiceActivity,
    setMicEnabled,
    estimateSpeakDuration
  };
}
