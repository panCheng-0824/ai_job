/**
 * 加载会话 history 后，按 plan_id + chat_session_id 批量恢复「进入」状态。
 */
import { lookupInterviewRecordByPlanAndChat } from "./api";
import {
  hasInterviewPlanStarted,
  resolvePlanIdFromMessage,
  shouldShowInterviewPlanActionBar
} from "./planStart";

function applyStartToTurn(turn, lookupResp) {
  if (!lookupResp?.exists || !lookupResp.record_id) return turn;
  return {
    ...turn,
    interview_session_started: true,
    interview_start_result: {
      record_id: lookupResp.record_id,
      interview_session_id: lookupResp.interview_session_id,
      plan_id: lookupResp.plan_id,
      plan_version: lookupResp.plan_version,
      status: lookupResp.session_status || "ready"
    }
  };
}

/**
 * 加载会话 history 后，对每条规划预览气泡按 plan_id + chat_session_id 查库。
 */
export async function hydrateInterviewPlanStartHistory(chatSessionId, studentId, history) {
  if (!Array.isArray(history)) return [];
  const cs = String(chatSessionId || "").trim();
  const sid = String(studentId || "").trim();
  if (!cs || !sid) return history;

  const out = history.map((t) => ({ ...t }));
  const pending = [];
  for (let i = 0; i < out.length; i++) {
    const turn = out[i];
    if (turn?.role !== "assistant" || !shouldShowInterviewPlanActionBar(turn)) continue;
    const planId = resolvePlanIdFromMessage(turn);
    if (!planId) continue;
    if (hasInterviewPlanStarted(turn)) continue;
    pending.push({ index: i, planId });
  }
  if (!pending.length) return out;

  const lookups = await Promise.all(
    pending.map((p) => lookupInterviewRecordByPlanAndChat(sid, p.planId, cs))
  );
  for (let j = 0; j < pending.length; j++) {
    out[pending[j].index] = applyStartToTurn(out[pending[j].index], lookups[j]);
  }
  return out;
}
