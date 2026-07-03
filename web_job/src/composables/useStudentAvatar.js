import { computed, ref } from "vue";
import { getStudentId } from "../api/client";
import { openAvatarCrop } from "./useAvatarCrop";
import { readImageAsDataUrl, readImageFileAsDataUrl } from "../utils/avatarImage";

const STORAGE_PREFIX = "student_avatar_";
const EVENT_NAME = "student-avatar-changed";

/** 全站共享头像 URL（按学号 localStorage 持久化） */
export const studentAvatarUrlRef = ref("");
export const studentAvatarLoadedForRef = ref("");
/** 服务端头像 URL（与学生画像「头像」字段一致，优先于 localStorage） */
export const studentServerAvatarUrlRef = ref("");
export const studentServerAvatarForRef = ref("");

function storageKey(studentId) {
  return `${STORAGE_PREFIX}${String(studentId || "").trim()}`;
}

/** 头像占位文字：优先姓名首字，否则学号末两位 */
export function avatarFallbackText(name, studentId) {
  const n = String(name || "").trim();
  if (n) return n.slice(0, 1);
  const sid = String(studentId || getStudentId() || "").trim();
  return sid.slice(-2) || "学";
}

function readFromStorage(studentId) {
  const sid = String(studentId || "").trim();
  if (!sid) return "";
  try {
    return localStorage.getItem(storageKey(sid)) || "";
  } catch {
    return "";
  }
}

function writeToStorage(studentId, dataUrl) {
  const sid = String(studentId || "").trim();
  if (!sid) return;
  try {
    if (dataUrl) localStorage.setItem(storageKey(sid), dataUrl);
    else localStorage.removeItem(storageKey(sid));
  } catch {
    /* ignore quota */
  }
}

function notifyChanged(studentId) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(EVENT_NAME, { detail: { studentId: String(studentId || "").trim() } })
  );
}

export function setStudentServerAvatar(url, studentId) {
  const sid = String(studentId || getStudentId() || "").trim();
  if (!sid) return;
  const next = String(url || "").trim();
  // 学籍接口不含头像时勿用空值覆盖 HomeLayout / 画像已同步的服务端 URL
  if (!next && studentServerAvatarForRef.value === sid && studentServerAvatarUrlRef.value) {
    return;
  }
  studentServerAvatarUrlRef.value = next;
  studentServerAvatarForRef.value = sid;
  notifyChanged(sid);
}

export function syncStudentAvatar(studentId) {
  const sid = String(studentId || getStudentId() || "").trim();
  if (!sid) {
    studentAvatarUrlRef.value = "";
    studentAvatarLoadedForRef.value = "";
    studentServerAvatarUrlRef.value = "";
    studentServerAvatarForRef.value = "";
    return "";
  }
  const url = readFromStorage(sid);
  studentAvatarUrlRef.value = url;
  studentAvatarLoadedForRef.value = sid;
  return url;
}

/** 解析当前应展示的头像：服务端 URL 优先，其次 localStorage */
export function resolveStudentAvatarUrl(studentId) {
  const sid = String(studentId || getStudentId() || "").trim();
  if (!sid) return "";
  if (studentServerAvatarForRef.value === sid && studentServerAvatarUrlRef.value) {
    return studentServerAvatarUrlRef.value;
  }
  if (studentAvatarLoadedForRef.value !== sid) {
    syncStudentAvatar(sid);
  }
  return studentAvatarUrlRef.value;
}

export function setStudentAvatarFromDataUrl(dataUrl, studentId) {
  const sid = String(studentId || getStudentId() || "").trim();
  if (!sid) throw new Error("请先登录");
  const url = String(dataUrl || "").trim();
  if (!url) throw new Error("无效头像");
  writeToStorage(sid, url);
  studentAvatarUrlRef.value = url;
  studentAvatarLoadedForRef.value = sid;
  notifyChanged(sid);
  return url;
}

/** 选图 → 圆形裁切 → 保存 */
export async function setStudentAvatarFromFile(file, studentId) {
  const sid = String(studentId || getStudentId() || "").trim();
  if (!sid) throw new Error("请先登录");
  const raw = await readImageFileAsDataUrl(file);
  let cropped;
  try {
    cropped = await openAvatarCrop(raw);
  } catch (e) {
    if (String(e?.message || "").includes("取消")) return "";
    throw e;
  }
  return setStudentAvatarFromDataUrl(cropped, sid);
}

export function clearStudentAvatar(studentId) {
  const sid = String(studentId || getStudentId() || "").trim();
  if (!sid) return;
  writeToStorage(sid, "");
  if (studentAvatarLoadedForRef.value === sid) {
    studentAvatarUrlRef.value = "";
  }
  notifyChanged(sid);
}

export function useStudentAvatar() {
  const studentId = computed(() => getStudentId());

  const avatarUrl = computed(() => resolveStudentAvatarUrl(studentId.value));

  return {
    studentId,
    avatarUrl,
    syncFromStorage: syncStudentAvatar,
    setServerAvatar: setStudentServerAvatar,
    resolveAvatarUrl: resolveStudentAvatarUrl,
    setAvatarFromFile: setStudentAvatarFromFile,
    setAvatarFromDataUrl: setStudentAvatarFromDataUrl,
    clearAvatar: clearStudentAvatar,
    avatarFallbackText
  };
}

if (typeof window !== "undefined") {
  window.addEventListener(EVENT_NAME, (ev) => {
    const sid = getStudentId();
    if (sid && ev.detail?.studentId === sid) {
      syncStudentAvatar(sid);
    }
  });
  window.addEventListener("storage", (ev) => {
    if (!ev.key?.startsWith(STORAGE_PREFIX)) return;
    const sid = getStudentId();
    if (sid && ev.key === storageKey(sid)) {
      syncStudentAvatar(sid);
    }
  });
}
