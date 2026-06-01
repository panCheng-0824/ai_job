/**
 * 服务端 history 与本地/缓存合并：补回 GET 或持久化丢失的附加上下文。
 */

const RESUME_RENDER_CACHE_LS = "chat_session_resume_render_by_ts";

function readResumeRenderCacheAll() {
  try {
    const raw = localStorage.getItem(RESUME_RENDER_CACHE_LS);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeResumeRenderCacheAll(all) {
  try {
    localStorage.setItem(RESUME_RENDER_CACHE_LS, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

/** 判断助手轮次是否带有可展示的 resume_render */
export function hasResumeRenderPayload(rr) {
  if (!rr || typeof rr !== "object") return false;
  const sections = rr.sections;
  if (sections && typeof sections === "object") {
    const hasContent = Object.values(sections).some(
      (arr) =>
        Array.isArray(arr) &&
        arr.some((i) => i && (String(i.title || "").trim() || String(i.body || "").trim()))
    );
    if (hasContent) return true;
  }
  return !!(String(rr.templateId || rr.template_id || "").trim());
}

function findLocalAssistant(local, serverHistory, index) {
  if (local[index]?.role === "assistant") return local[index];
  const serverTurn = serverHistory[index];
  const ts = serverTurn?.ts;
  if (ts) {
    const hit = local.find((l) => l?.role === "assistant" && l.ts === ts);
    if (hit) return hit;
  }
  const localAssistants = local.filter((l) => l?.role === "assistant");
  let ord = 0;
  for (let j = 0; j <= index; j++) {
    if (serverHistory[j]?.role === "assistant") ord++;
  }
  return ord > 0 ? localAssistants[ord - 1] || null : null;
}

function mergeAssistantExtras(turn, localHit, doneExtras) {
  let merged = { ...turn };
  const fromLocal = localHit || {};
  if (!merged.resume_render && fromLocal.resume_render) {
    merged = { ...merged, resume_render: fromLocal.resume_render };
  }
  if (!merged.job_recommend && fromLocal.job_recommend) {
    merged = { ...merged, job_recommend: fromLocal.job_recommend };
  }
  if (!merged.interview_plan_preview && fromLocal.interview_plan_preview) {
    merged = { ...merged, interview_plan_preview: fromLocal.interview_plan_preview };
  }
  if (fromLocal.interview_session_started) {
    merged = { ...merged, interview_session_started: fromLocal.interview_session_started };
  }
  if (!merged.interview_start_result && fromLocal.interview_start_result) {
    merged = { ...merged, interview_start_result: fromLocal.interview_start_result };
  }
  if (doneExtras?.resume_render && !merged.resume_render) {
    merged = { ...merged, resume_render: doneExtras.resume_render };
  }
  if (doneExtras?.job_recommend && !merged.job_recommend) {
    merged = { ...merged, job_recommend: doneExtras.job_recommend };
  }
  if (doneExtras?.interview_plan_preview && !merged.interview_plan_preview) {
    merged = { ...merged, interview_plan_preview: doneExtras.interview_plan_preview };
  }
  return merged;
}

/**
 * 合并用户 context_cards + 助手 resume_render / job_recommend。
 *
 * @param {unknown[]} serverHistory
 * @param {unknown[]} localHistory 流式结束前的本地 history（含 SSE 挂上的字段）
 * @param {{ resume_render?: object, job_recommend?: object }} [doneExtras] done 事件顶层字段，补最后一轮助手
 */
export function mergePersistedHistory(serverHistory, localHistory, doneExtras) {
  if (!Array.isArray(serverHistory)) return [];
  const local = Array.isArray(localHistory) ? localHistory : [];
  const lastAssistantIdx = serverHistory.reduce(
    (acc, t, i) => (t?.role === "assistant" ? i : acc),
    -1
  );

  return serverHistory.map((turn, i) => {
    if (turn?.role === "user") {
      if (turn.context_cards && turn.context_cards.length) return { ...turn };
      let hit = local[i];
      if (hit?.role === "user" && hit.context_cards?.length) {
        return { ...turn, context_cards: hit.context_cards };
      }
      if (turn.ts) {
        hit = local.find(
          (l) => l?.role === "user" && l.ts === turn.ts && l.context_cards?.length
        );
        if (hit) return { ...turn, context_cards: hit.context_cards };
      }
      hit = local.find(
        (l) =>
          l?.role === "user" &&
          l.content === turn.content &&
          l.context_cards?.length
      );
      if (hit) return { ...turn, context_cards: hit.context_cards };
      return { ...turn };
    }

    if (turn?.role === "assistant") {
      const localHit = findLocalAssistant(local, serverHistory, i);
      const extras =
        i === lastAssistantIdx
          ? {
              resume_render: doneExtras?.resume_render,
              job_recommend: doneExtras?.job_recommend
            }
          : undefined;
      return mergeAssistantExtras(turn, localHit, extras);
    }

    return { ...turn };
  });
}

/** @deprecated 使用 mergePersistedHistory */
export function mergeHistoryContextCards(serverHistory, localHistory) {
  return mergePersistedHistory(serverHistory, localHistory);
}

/** 将当前会话中带 resume_render 的助手轮次写入 localStorage（按 ts 索引） */
export function saveSessionResumeRenderCache(sessionId, history) {
  const sid = (sessionId || "").trim();
  if (!sid || !Array.isArray(history)) return;
  const all = readResumeRenderCacheAll();
  const map = { ...(all[sid] || {}) };
  for (const t of history) {
    if (t?.role === "assistant" && t.ts && t.resume_render && hasResumeRenderPayload(t.resume_render)) {
      map[t.ts] = t.resume_render;
    }
  }
  all[sid] = map;
  writeResumeRenderCacheAll(all);
}

/** 刷新后从 localStorage 补回服务端 history 中缺失的 resume_render */
export function hydrateSessionResumeRenderCache(sessionId, history) {
  const sid = (sessionId || "").trim();
  if (!sid || !Array.isArray(history)) return history;
  const map = readResumeRenderCacheAll()[sid];
  if (!map || typeof map !== "object") return history;
  return history.map((turn) => {
    if (turn?.role !== "assistant" || turn.resume_render) return { ...turn };
    const ts = turn.ts;
    const rr = ts ? map[ts] : null;
    if (rr && hasResumeRenderPayload(rr)) {
      return { ...turn, resume_render: rr };
    }
    return { ...turn };
  });
}
