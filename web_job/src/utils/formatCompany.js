/** 注册资金展示：库内 {@code zczj} 数值单位为万元 */
export function fmtRegisteredCapital(raw) {
  if (raw === null || raw === undefined) return "-";
  const s = String(raw).trim();
  if (!s) return "-";
  if (/万元/.test(s)) return s;
  return `${s} 万元`;
}
