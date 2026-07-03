import { onBeforeUnmount, ref } from "vue";
import { apiPostVoiceSpeech } from "../api/client";
import { loadTtsVoice } from "../config/ttsVoices";
import { loadRoomVoiceOutput, saveRoomVoiceOutput } from "../config/interviewerPersonas";

/**
 * 视频面试房间语音播报：TTS 合成 + 与 presence speaking 态联动
 */
export function useRoomVoiceBroadcast({ speakFor }) {
  const useVoiceOutput = ref(loadRoomVoiceOutput());
  const ttsVoice = ref(loadTtsVoice());

  let playingAudio = null;
  let audioUrl = "";

  function stopBroadcast() {
    if (playingAudio) {
      playingAudio.pause();
      playingAudio = null;
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      audioUrl = "";
    }
  }

  async function broadcast(text) {
    const content = String(text || "").trim();
    if (!content) return;

    stopBroadcast();
    speakFor(content);

    if (!useVoiceOutput.value) return;

    try {
      const blob = await apiPostVoiceSpeech({
        text: content,
        voice: ttsVoice.value
      });
      audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      playingAudio = audio;
      audio.addEventListener(
        "ended",
        () => {
          stopBroadcast();
        },
        { once: true }
      );
      audio.addEventListener(
        "error",
        () => {
          stopBroadcast();
        },
        { once: true }
      );
      await audio.play();
    } catch {
      /* 合成失败时保留 speakFor 动效 */
    }
  }

  function setTtsVoice(voiceId) {
    ttsVoice.value = voiceId;
  }

  function setVoiceOutput(on) {
    useVoiceOutput.value = saveRoomVoiceOutput(on);
    if (!on) stopBroadcast();
  }

  onBeforeUnmount(stopBroadcast);

  return {
    useVoiceOutput,
    ttsVoice,
    broadcast,
    stopBroadcast,
    setTtsVoice,
    setVoiceOutput
  };
}
