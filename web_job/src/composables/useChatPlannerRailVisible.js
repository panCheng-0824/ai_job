import { ref } from "vue";

/** 各角色会话右侧「我的资料」栏 localStorage 键（与 usercode 对齐） */
export const CHAT_PLANNER_RAIL_LS_KEY = "chat_planner_rail_visible";
export const CHAT_RESUME_OPTIMIZER_RAIL_LS_KEY = "chat_resume_optimizer_rail_visible";

const RAIL_LS_BY_USERCODE = {
  ROLE001: CHAT_PLANNER_RAIL_LS_KEY,
  ROLE004: CHAT_RESUME_OPTIMIZER_RAIL_LS_KEY
};

function readLs(key) {
  if (typeof localStorage === "undefined") return true;
  return localStorage.getItem(key) !== "0";
}

function persistKey(key, visible) {
  try {
    localStorage.setItem(key, visible ? "1" : "0");
  } catch (_) {
    /* ignore */
  }
}

function railRefForUsercode(usercode) {
  const code = (usercode || "").trim();
  const lsKey = RAIL_LS_BY_USERCODE[code] || CHAT_PLANNER_RAIL_LS_KEY;
  if (!railRefForUsercode._cache[lsKey]) {
    railRefForUsercode._cache[lsKey] = ref(readLs(lsKey));
  }
  return railRefForUsercode._cache[lsKey];
}
railRefForUsercode._cache = {};

/** 岗位规划师（ROLE001）— 兼容旧引用 */
export const chatPlannerRailVisibleRef = railRefForUsercode("ROLE001");

/** 简历优化师（ROLE004） */
export const chatResumeOptimizerRailVisibleRef = railRefForUsercode("ROLE004");

/** 当前角色是否支持「我的资料」侧栏 */
export function supportsContextRail(usercode) {
  const code = (usercode || "").trim();
  return code === "ROLE001" || code === "ROLE004";
}

export function contextRailVisibleRef(usercode) {
  return railRefForUsercode(usercode);
}

export function toggleContextRailVisible(usercode) {
  const r = railRefForUsercode(usercode);
  r.value = !r.value;
  const code = (usercode || "").trim();
  const lsKey = RAIL_LS_BY_USERCODE[code] || CHAT_PLANNER_RAIL_LS_KEY;
  persistKey(lsKey, r.value);
}

export function setContextRailVisible(usercode, visible) {
  const r = railRefForUsercode(usercode);
  r.value = !!visible;
  const code = (usercode || "").trim();
  const lsKey = RAIL_LS_BY_USERCODE[code] || CHAT_PLANNER_RAIL_LS_KEY;
  persistKey(lsKey, r.value);
}

/** @deprecated 使用 toggleContextRailVisible('ROLE001') */
export function toggleChatPlannerRailVisible() {
  toggleContextRailVisible("ROLE001");
}

/** @deprecated 使用 setContextRailVisible('ROLE001', visible) */
export function setChatPlannerRailVisible(visible) {
  setContextRailVisible("ROLE001", visible);
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (!e.key || e.newValue == null) return;
    for (const lsKey of Object.values(RAIL_LS_BY_USERCODE)) {
      if (e.key === lsKey) {
        const r = railRefForUsercode._cache[lsKey];
        if (r) r.value = e.newValue !== "0";
      }
    }
  });
}
