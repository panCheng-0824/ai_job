/** 统一 job_id 比较（避免 number / string 不一致） */
export function normalizeJobId(id) {
  if (id == null) return "";
  return String(id).trim();
}

export function sameJobId(a, b) {
  const left = normalizeJobId(a);
  const right = normalizeJobId(b);
  return Boolean(left && right && left === right);
}
