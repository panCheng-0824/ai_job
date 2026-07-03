const STORAGE_KEY = "web_job_resume_store_v1";

function safeParse(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * @returns {{ resumes: Array<import('./types').ResumeRecord>, defaultResumeId: string | null }}
 */
export function loadStore() {
  const raw = localStorage.getItem(STORAGE_KEY);
  const data = raw ? safeParse(raw) : null;
  if (!data || !Array.isArray(data.resumes)) {
    return { resumes: [], defaultResumeId: null };
  }
  return {
    resumes: data.resumes,
    defaultResumeId: data.defaultResumeId || null
  };
}

export function saveStore(store) {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      resumes: store.resumes,
      defaultResumeId: store.defaultResumeId
    })
  );
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

function timestampSuffix() {
  const d = new Date();
  return `${d.getFullYear()}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}${pad2(d.getHours())}${pad2(d.getMinutes())}${pad2(d.getSeconds())}`;
}

/** 与「保存为时间副本」服务端/本地共用的展示名后缀 */
export function appendTimeCopySuffix(displayName) {
  const base = (displayName || "").trim() || "简历";
  return `${base}_${timestampSuffix()}`;
}

/** 去掉展示名末尾 `_yyyyMMddHHmmss`，得到逻辑名称（编辑区用） */
export function stripTimeCopySuffix(name) {
  return String(name || "").replace(/_\d{14}$/, "").trim();
}

/**
 * 学号-姓名-序号；按「去时间戳后的名称」去重计数。
 * @param {{ studentNo: string, name: string, store: ReturnType<typeof loadStore> }} p
 */
export function nextDisplayName({ studentNo, name, store }) {
  const sid = (studentNo || "").trim() || "未知学号";
  const nm = (name || "").trim() || "未命名";
  const prefix = `${sid}-${nm}-`;
  const logicalNames = new Set(
    (store.resumes || []).map((r) => stripTimeCopySuffix(r.displayName || ""))
  );
  const same = [...logicalNames].filter((lb) => lb.startsWith(prefix));
  const seq = same.length + 1;
  return `${sid}-${nm}-${String(seq).padStart(2, "0")}`;
}

function clearSeriesDefaultInStore(store, seriesId, keepId) {
  store.resumes.forEach((r) => {
    const ser = r.seriesId || r.id;
    if (ser === seriesId) {
      r.isSeriesDefault = r.id === keepId;
    }
  });
}

function clearGlobalDefaultInStore(store, keepId) {
  store.defaultResumeId = keepId;
  store.resumes.forEach((r) => {
    r.isDefault = r.id === keepId;
  });
}

/**
 * 原地更新当前副本（不改 id、不追加时间戳）。
 * @param {import('./types').ResumeRecord} record
 * @param {{ setGlobalDefault?: boolean }} opts
 */
export function updateResumeInPlace(record, opts = {}) {
  const store = loadStore();
  const idx = store.resumes.findIndex((r) => r.id === record.id);
  if (idx < 0) {
    throw new Error("副本不存在");
  }
  const ser = record.seriesId || store.resumes[idx].seriesId || record.id;
  const now = Date.now();
  const next = {
    ...store.resumes[idx],
    ...record,
    seriesId: ser,
    isSeriesDefault: true,
    updatedAt: now
  };
  store.resumes[idx] = next;
  clearSeriesDefaultInStore(store, ser, record.id);
  if (opts.setGlobalDefault) {
    clearGlobalDefaultInStore(store, record.id);
  } else if (!store.defaultResumeId) {
    clearGlobalDefaultInStore(store, record.id);
  }
  saveStore(store);
  return loadStore();
}

/**
 * 保存前将当前副本内容固化为同简历线下的历史快照（带时间戳展示名）。
 * @param {import('./types').ResumeRecord} existing
 */
export function appendVersionSnapshot(existing) {
  const store = loadStore();
  const ser = existing.seriesId || existing.id;
  const now = Date.now();
  const base = stripTimeCopySuffix(existing.displayName || "") || "简历";
  const snapshot = {
    ...existing,
    id: newResumeId(),
    seriesId: ser,
    displayName: appendTimeCopySuffix(base),
    isSeriesDefault: false,
    isDefault: false,
    createdAt: existing.updatedAt || existing.createdAt || now,
    updatedAt: existing.updatedAt || existing.createdAt || now
  };
  store.resumes.push(snapshot);
  saveStore(store);
  return snapshot;
}

/**
 * 新建一条简历线及首条记录（逻辑展示名，无时间戳后缀）。
 * @param {import('./types').ResumeRecord} record
 * @param {{ setGlobalDefault?: boolean }} opts
 */
export function insertNewResumeRecord(record, opts = {}) {
  const store = loadStore();
  const ser = record.seriesId || newResumeId();
  const now = Date.now();
  const rec = {
    ...record,
    seriesId: ser,
    displayName: stripTimeCopySuffix(record.displayName || "") || "简历",
    isSeriesDefault: true,
    isDefault: false,
    createdAt: record.createdAt ?? now,
    updatedAt: now
  };
  clearSeriesDefaultInStore(store, ser, rec.id);
  store.resumes.push(rec);
  if (opts.setGlobalDefault || !store.defaultResumeId) {
    clearGlobalDefaultInStore(store, rec.id);
  }
  saveStore(store);
  return { store: loadStore(), seriesId: ser };
}

/** @param {string} id @param {'series' | 'global'} scope */
export function setDefaultResume(id, scope = "series") {
  const store = loadStore();
  const rec = store.resumes.find((r) => r.id === id);
  if (!rec) return loadStore();
  const ser = rec.seriesId || rec.id;
  if (scope === "global") {
    clearGlobalDefaultInStore(store, id);
    clearSeriesDefaultInStore(store, ser, id);
  } else {
    clearSeriesDefaultInStore(store, ser, id);
  }
  saveStore(store);
  return loadStore();
}

export function deleteResume(id) {
  const store = loadStore();
  const removed = store.resumes.find((r) => r.id === id);
  const ser = removed?.seriesId || removed?.id;
  store.resumes = store.resumes.filter((r) => r.id !== id);
  if (store.defaultResumeId === id) {
    const sorted = [...store.resumes].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    store.defaultResumeId = sorted[0]?.id || null;
    store.resumes.forEach((r) => {
      r.isDefault = r.id === store.defaultResumeId;
    });
  }
  if (ser) {
    const left = store.resumes.filter((r) => (r.seriesId || r.id) === ser);
    if (left.length && !left.some((r) => r.isSeriesDefault)) {
      const pick = [...left].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))[0];
      clearSeriesDefaultInStore(store, ser, pick.id);
    }
  }
  saveStore(store);
  return loadStore();
}

export function newResumeId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `r_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

/** 取某简历线的默认副本（用于加载） */
export function pickSeriesDefaultVersion(versions, defaultResumeId) {
  const list = versions || [];
  if (!list.length) return null;
  return (
    list.find((r) => r.isSeriesDefault) ||
    list.find((r) => r.id === defaultResumeId) ||
    [...list].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))[0]
  );
}
