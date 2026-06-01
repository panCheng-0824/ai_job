/**
 * 规划预览 SSE 载荷 localStorage 缓存（服务端 history 不持久化 interview_plan_preview）。
 */
const LS_KEY = "chat_session_interview_plan_preview_v1";

function readAll() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeAll(all) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

/** 将带 interview_plan_preview 的助手轮次写入缓存（按 ts / plan_id 双索引） */
export function saveSessionInterviewPlanPreviewCache(sessionId, history) {
  const sid = String(sessionId || "").trim();
  if (!sid || !Array.isArray(history)) return;
  const all = readAll();
  const bucket = { byTs: { ...(all[sid]?.byTs || {}) }, byPlan: { ...(all[sid]?.byPlan || {}) } };
  for (const t of history) {
    if (t?.role !== "assistant") continue;
    const preview = t.interview_plan_preview;
    const planId = preview?.plan?.plan_id || preview?.plan?.planId;
    if (!preview || !planId) continue;
    if (t.ts) bucket.byTs[t.ts] = preview;
    bucket.byPlan[String(planId).trim()] = preview;
  }
  all[sid] = bucket;
  writeAll(all);
}

/** 刷新后补回 interview_plan_preview，供 resolvePlanIdFromMessage 使用 */
export function hydrateSessionInterviewPlanPreviewCache(sessionId, history) {
  const sid = String(sessionId || "").trim();
  if (!sid || !Array.isArray(history)) return history;
  const bucket = readAll()[sid];
  if (!bucket) return history;
  return history.map((turn) => {
    if (turn?.role !== "assistant" || turn.interview_plan_preview) return { ...turn };
    let preview = turn.ts ? bucket.byTs?.[turn.ts] : null;
    if (!preview) {
      const text = String(turn.content || "");
      const m = text.match(/题目编号[\s\S]*?`([^`]+)`/);
      const pid = m ? m[1].trim() : "";
      if (pid) preview = bucket.byPlan?.[pid];
    }
    if (preview) return { ...turn, interview_plan_preview: preview };
    return { ...turn };
  });
}

/** 删除记录后清除该 plan 的预览缓存（可选，便于同会话重新「开始」） */
export function clearInterviewPlanPreviewCache(sessionId, planId) {
  const sid = String(sessionId || "").trim();
  const pid = String(planId || "").trim();
  if (!sid || !pid) return;
  const all = readAll();
  const bucket = all[sid];
  if (!bucket) return;
  const next = {
    byTs: { ...(bucket.byTs || {}) },
    byPlan: { ...(bucket.byPlan || {}) }
  };
  delete next.byPlan[pid];
  for (const [ts, val] of Object.entries(next.byTs)) {
    if (val?.plan?.plan_id === pid) delete next.byTs[ts];
  }
  all[sid] = next;
  writeAll(all);
}
