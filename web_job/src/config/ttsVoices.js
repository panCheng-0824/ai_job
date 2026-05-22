/**
 * Qwen3-TTS CustomVoice 内置发音人（id 与网关一致）。
 * 文案依据官方音色说明做了中文概括，便于按「御姐 / 大叔」等直觉选择。
 */
export const TTS_VOICES = [
  {
    id: "serena",
    gender: "female",
    title: "温柔姐姐",
    accent: "中文",
    blurb: "暖柔年轻女声，亲和稳重"
  },
  {
    id: "vivian",
    gender: "female",
    title: "御姐俐落",
    accent: "中文",
    blurb: "明亮略带棱角，气场清爽利落"
  },
  {
    id: "uncle_fu",
    gender: "male",
    title: "醇厚大叔",
    accent: "中文",
    blurb: "低沉宽厚，成熟稳重"
  },
  {
    id: "dylan",
    gender: "male",
    title: "京腔小哥",
    accent: "北京话",
    blurb: "年轻清爽，京味儿自然"
  },
  {
    id: "eric",
    gender: "male",
    title: "川味小哥",
    accent: "四川话",
    blurb: "活泼略带沙哑亮色"
  },
  {
    id: "ryan",
    gender: "male",
    title: "动感英文",
    accent: "英语",
    blurb: "节奏感强，利落有力"
  },
  {
    id: "aiden",
    gender: "male",
    title: "阳光美式",
    accent: "英语",
    blurb: "清澈中频，美式开朗"
  },
  {
    id: "ono_anna",
    gender: "female",
    title: "俏皮日系",
    accent: "日语",
    blurb: "轻快灵动少女感"
  },
  {
    id: "sohee",
    gender: "female",
    title: "温柔韩语",
    accent: "韩语",
    blurb: "情感饱满柔和"
  }
];

export const TTS_VOICE_IDS = TTS_VOICES.map((v) => v.id);

export const DEFAULT_TTS_VOICE = "serena";

/** @param {string} id */
export function getVoiceById(id) {
  return TTS_VOICES.find((v) => v.id === id) || null;
}

const STORAGE_KEY = "tts_voice";

export function loadTtsVoice() {
  const v = localStorage.getItem(STORAGE_KEY);
  if (v && TTS_VOICE_IDS.includes(v)) return v;
  return DEFAULT_TTS_VOICE;
}

export function saveTtsVoice(v) {
  const next = TTS_VOICE_IDS.includes(v) ? v : DEFAULT_TTS_VOICE;
  localStorage.setItem(STORAGE_KEY, next);
  return next;
}
