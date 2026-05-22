import { ref } from "vue";

export const RESUME_AI_RAIL_LS_KEY = "resume_ai_rail_visible";

/** 创建简历页右侧「AI 简历优化」栏是否展开 */
export const resumeAiRailVisibleRef = ref(
  typeof localStorage !== "undefined" ? localStorage.getItem(RESUME_AI_RAIL_LS_KEY) !== "0" : false
);

function persist(v) {
  try {
    localStorage.setItem(RESUME_AI_RAIL_LS_KEY, v ? "1" : "0");
  } catch {
    /* ignore */
  }
}

export function toggleResumeAiRailVisible() {
  resumeAiRailVisibleRef.value = !resumeAiRailVisibleRef.value;
  persist(resumeAiRailVisibleRef.value);
}

export function setResumeAiRailVisible(visible) {
  resumeAiRailVisibleRef.value = !!visible;
  persist(resumeAiRailVisibleRef.value);
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key === RESUME_AI_RAIL_LS_KEY && e.newValue != null) {
      resumeAiRailVisibleRef.value = e.newValue !== "0";
    }
  });
}
