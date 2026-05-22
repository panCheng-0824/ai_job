import { ref } from "vue";

export const RESUME_STUDIO_RAIL_LS_KEY = "resume_studio_rail_visible";

/** 创建简历页右侧工具栏（版本/保存/预览）是否展开；默认关闭，仅记住用户主动打开 */
export const resumeStudioRailVisibleRef = ref(
  typeof localStorage !== "undefined" ? localStorage.getItem(RESUME_STUDIO_RAIL_LS_KEY) === "1" : false
);

function persist(v) {
  try {
    localStorage.setItem(RESUME_STUDIO_RAIL_LS_KEY, v ? "1" : "0");
  } catch {
    /* ignore */
  }
}

export function toggleResumeStudioRailVisible() {
  resumeStudioRailVisibleRef.value = !resumeStudioRailVisibleRef.value;
  persist(resumeStudioRailVisibleRef.value);
}

export function setResumeStudioRailVisible(visible) {
  resumeStudioRailVisibleRef.value = !!visible;
  persist(resumeStudioRailVisibleRef.value);
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key === RESUME_STUDIO_RAIL_LS_KEY && e.newValue != null) {
      resumeStudioRailVisibleRef.value = e.newValue === "1";
    }
  });
}
