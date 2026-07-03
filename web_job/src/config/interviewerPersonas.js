import {
  DEFAULT_TTS_VOICE,
  TTS_VOICES,
  loadTtsVoice,
  saveTtsVoice
} from "./ttsVoices";

/** Cubism SDK 示例角色（与 public/cubism/Resources 目录名一致） */
export const LIVE2D_MODELS = ["Haru", "Hiyori", "Mark", "Natori", "Rice", "Mao", "Wanko", "Ren"];

/** TTS 发音人 → Live2D 数字人 */
export const VOICE_TO_LIVE2D = {
  serena: "Haru",
  vivian: "Hiyori",
  uncle_fu: "Natori",
  dylan: "Ren",
  eric: "Mark",
  ryan: "Natori",
  aiden: "Wanko",
  ono_anna: "Rice",
  sohee: "Mao"
};

/** Live2D 模型展示名 */
export const LIVE2D_MODEL_LABELS = {
  Haru: "Haru · 商务女声",
  Hiyori: "Hiyori · 活泼少女",
  Mark: "Mark · 休闲男生",
  Natori: "Natori · 正装男士",
  Rice: "Rice · 和风少女",
  Mao: "Mao · 猫耳少女",
  Wanko: "Wanko · 萌犬",
  Ren: "Ren · 少年"
};

/** 各模型表情映射（无 Expressions 的模型可省略） */
export const LIVE2D_EXPRESSIONS = {
  Haru: { idle: "F01", listening: "F02", thinking: "F03" },
  Mao: { idle: "exp_01", listening: "exp_02", thinking: "exp_03" },
  Ren: { idle: "exp_01", listening: "exp_02", thinking: "exp_03" },
  Natori: { idle: "Normal", listening: "Smile", thinking: "Surprised" }
};

const LIVE2D_STORAGE_KEY = "interview_live2d_model";
const ROOM_VOICE_OUTPUT_KEY = "room_voice_output";

export const DEFAULT_LIVE2D_MODEL = "Haru";

export function getLive2dModelForVoice(voiceId) {
  return VOICE_TO_LIVE2D[voiceId] || DEFAULT_LIVE2D_MODEL;
}

export function getLive2dModelLabel(model) {
  return LIVE2D_MODEL_LABELS[model] || model;
}

/** 带数字人信息的语音角色列表（与 AI 助手 TTS 列表一致） */
export function buildInterviewerPersonas() {
  return TTS_VOICES.map((voice) => ({
    ...voice,
    live2dModel: getLive2dModelForVoice(voice.id),
    live2dLabel: getLive2dModelLabel(getLive2dModelForVoice(voice.id))
  }));
}

export const INTERVIEWER_PERSONAS = buildInterviewerPersonas();

export function loadInterviewLive2dModel() {
  const v = localStorage.getItem(LIVE2D_STORAGE_KEY);
  if (v && LIVE2D_MODELS.includes(v)) return v;
  return getLive2dModelForVoice(loadTtsVoice());
}

export function saveInterviewLive2dModel(model) {
  const next = LIVE2D_MODELS.includes(model) ? model : DEFAULT_LIVE2D_MODEL;
  localStorage.setItem(LIVE2D_STORAGE_KEY, next);
  return next;
}

export function loadRoomVoiceOutput() {
  const room = localStorage.getItem(ROOM_VOICE_OUTPUT_KEY);
  if (room === "0" || room === "1") return room === "1";
  return localStorage.getItem("chat_voice_output") === "1";
}

export function saveRoomVoiceOutput(on) {
  localStorage.setItem(ROOM_VOICE_OUTPUT_KEY, on ? "1" : "0");
  localStorage.setItem("chat_voice_output", on ? "1" : "0");
  return on;
}

export function selectInterviewerPersona(voiceId) {
  const voice = saveTtsVoice(voiceId || DEFAULT_TTS_VOICE);
  const model = saveInterviewLive2dModel(getLive2dModelForVoice(voice));
  return { voiceId: voice, live2dModel: model };
}
