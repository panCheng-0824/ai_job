/**
 * 面试中心 — 记录分组、状态文案与统计。
 */

const UPCOMING_STATUSES = new Set(["planning", "ready", "in_progress", "booked"]);
const HISTORY_STATUSES = new Set(["completed", "abandoned"]);

/** 设计稿用日期：2026.05.20 14:00 */
export function formatRecordSchedule(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${y}.${m}.${day} ${h}:${min}`;
}

export function recordDisplayTitle(item) {
  return item?.plan_title || item?.target_role || "模拟面试";
}

export function recordCompanyLabel(item) {
  if (item?.is_job_booking) {
    const company = String(item?.industry_label || item?.company_name || "").trim();
    return company || "岗位预约";
  }
  const industry = String(item?.industry_label || "").trim();
  if (!industry) return "模拟面试";
  const parts = industry.split(/\s*\/\s*/).filter(Boolean);
  return parts[parts.length - 1] || industry;
}

export function isJobBookingCard(item) {
  return Boolean(item?.is_job_booking);
}

/** 岗位预约 → 面试中心待面试卡片 */
export function bookingToPendingCard(booking) {
  const bookingId = booking?.booking_id ?? booking?.id;
  if (!bookingId) return null;
  const jobTitle =
    booking?.job_title || booking?.job?.job_title || booking?.job?.job_name || booking?.job_id || "岗位面试";
  const company =
    booking?.company_name ||
    booking?.job?.company_name ||
    booking?.job?.company_relation?.company_name ||
    "";
  return {
    record_id: `job-booking-${bookingId}`,
    booking_id: bookingId,
    job_id: booking.job_id,
    plan_title: jobTitle,
    target_role: jobTitle,
    industry_label: company,
    company_name: company,
    session_status: "booked",
    created_at: booking.booked_at,
    is_job_booking: true
  };
}

export function isUpcomingRecord(item) {
  if (item?.is_job_booking) return true;
  return UPCOMING_STATUSES.has(String(item?.session_status || "").trim());
}

export function isHistoryRecord(item) {
  return HISTORY_STATUSES.has(String(item?.session_status || "").trim());
}

/** 待面试区卡片状态徽标 */
export function upcomingStatusMeta(status) {
  const s = String(status || "").trim();
  if (s === "in_progress") {
    return { label: "面试中", tone: "live" };
  }
  if (s === "booked") {
    return { label: "待面试", tone: "pending" };
  }
  if (s === "ready" || s === "planning") {
    return { label: "待开始", tone: "pending" };
  }
  return { label: "待开始", tone: "pending" };
}

/** 历史记录区状态徽标 */
export function historyStatusMeta(status) {
  const s = String(status || "").trim();
  if (s === "abandoned") {
    return { label: "已放弃", tone: "muted" };
  }
  return { label: "已结束", tone: "ended" };
}

export function buildContinueChatQuery(item) {
  const q = {};
  if (item?.interview_session_id) {
    q.interview_session = item.interview_session_id;
  }
  if (item?.chat_session_id) {
    q.session_id = item.chat_session_id;
  }
  return q;
}

/** 已完成记录中得分 ≥ threshold 视为通过 */
export function computePassRate(items, passThreshold = 60) {
  const finished = (items || []).filter((r) => r.session_status === "completed");
  if (!finished.length) return null;
  const passed = finished.filter((r) => {
    const score = Number(r.total_score);
    return !Number.isNaN(score) && score >= passThreshold;
  });
  return Math.round((passed.length / finished.length) * 100);
}

export function partitionInterviewRecords(items) {
  const upcoming = [];
  const history = [];
  for (const item of items || []) {
    if (isUpcomingRecord(item)) upcoming.push(item);
    else if (isHistoryRecord(item)) history.push(item);
    else history.push(item);
  }
  return { upcoming, history };
}
