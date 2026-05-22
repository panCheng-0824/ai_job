import { ref } from "vue";

export const CHAT_SIDEBAR_LS_KEY = "chat_sidebar_visible";

/** 对话页左侧栏是否展开（全站共享，与 localStorage 同步） */
export const chatSidebarVisibleRef = ref(
  typeof localStorage !== "undefined" ? localStorage.getItem(CHAT_SIDEBAR_LS_KEY) !== "0" : true
);

function persist(v) {
  try {
    localStorage.setItem(CHAT_SIDEBAR_LS_KEY, v ? "1" : "0");
  } catch (_) {
    /* ignore */
  }
}

export function toggleChatSidebarVisible() {
  chatSidebarVisibleRef.value = !chatSidebarVisibleRef.value;
  persist(chatSidebarVisibleRef.value);
}

export function setChatSidebarVisible(visible) {
  chatSidebarVisibleRef.value = !!visible;
  persist(chatSidebarVisibleRef.value);
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key === CHAT_SIDEBAR_LS_KEY && e.newValue != null) {
      chatSidebarVisibleRef.value = e.newValue !== "0";
    }
  });
}
