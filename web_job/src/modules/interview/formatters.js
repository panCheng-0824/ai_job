/**
 * 面试模块展示格式化（时间、分数、进度）。
 */

/** 将 ISO / 后端时间格式化为本地简短日期时间 */
export function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

/** 答题进度文案 */
export function formatProgress(answered, total) {
  const a = Number(answered) || 0;
  const t = Number(total) || 0;
  if (t <= 0) return "—";
  return `${a} / ${t} 题`;
}

/** 分数展示，无分数时返回占位 */
export function formatScore(score) {
  if (score == null || score === "") return "—";
  const n = Number(score);
  if (Number.isNaN(n)) return String(score);
  return n.toFixed(1);
}

/** 答题进度百分比（0～100），无题目时返回 0 */
export function formatProgressPercent(answered, total) {
  const a = Number(answered) || 0;
  const t = Number(total) || 0;
  if (t <= 0) return 0;
  return Math.min(100, Math.round((a / t) * 100));
}
