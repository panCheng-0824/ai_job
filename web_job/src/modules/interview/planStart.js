/**
 * 模拟面试官规划预览完成后，聊天气泡「开始 / 进入」操作条识别与 plan 解析。
 */

/** 与 ai_job plan_preview 摘要末尾文案一致，用于识别规划预览气泡 */
export const INTERVIEW_PLAN_START_MARKER = "确认后可创建正式面试会话";

/** 从 SSE 载荷或 Markdown 正文解析 plan_id */
export function resolvePlanIdFromMessage(item) {
  const plan = item?.interview_plan_preview?.plan;
  const pid = plan?.plan_id ?? plan?.planId;
  if (pid) return String(pid).trim();

  const text = String(item?.content || "");
  if (!text.trim()) return "";

  // - **题目编号**：`plan_xxx` 或 题目编号：`plan_xxx`
  let m = text.match(/题目编号[\s*]*[：:][^`\n]*`([^`]+)`/);
  if (m) return m[1].trim();

  // 兜底：正文中的 `plan_` 前缀编号
  m = text.match(/`(plan_[a-zA-Z0-9_]+)`/);
  if (m) return m[1].trim();

  return "";
}

/** 是否可展示操作条（有确认文案或能解析出 plan_id 即可） */
export function shouldShowInterviewPlanActionBar(item) {
  if (!item || item.role !== "assistant") return false;
  const text = String(item.content || "");
  if (text.includes(INTERVIEW_PLAN_START_MARKER)) return true;
  if (resolvePlanIdFromMessage(item)) return true;
  // 大纲预览标题结构
  if (/面试大纲已就绪/.test(text) && /题目编号/.test(text)) return true;
  return false;
}

/** @deprecated 使用 {@link shouldShowInterviewPlanActionBar} */
export function shouldShowInterviewPlanStart(item) {
  return shouldShowInterviewPlanActionBar(item);
}

/** 是否已成功创建面试记录（本地 history 标记） */
export function hasInterviewPlanStarted(item) {
  if (!item || item.role !== "assistant") return false;
  if (item.interview_session_started) return true;
  const r = item.interview_start_result;
  return Boolean(r && (r.record_id || r.interview_session_id));
}

/** 从 history 条目取创建接口返回的结果 */
export function resolveInterviewStartResult(item) {
  const r = item?.interview_start_result;
  if (!r || typeof r !== "object") return null;
  return r;
}

export function resolvePlanVersionFromMessage(item) {
  const plan = item?.interview_plan_preview?.plan;
  const v = plan?.version ?? plan?.plan_version;
  return v != null && v !== "" ? Number(v) : null;
}
