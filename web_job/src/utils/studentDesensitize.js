/**
 * 学生敏感信息展示脱敏（仅用于 UI 只读展示，编辑/保存仍用原始值）。
 */

/** 需在展示层脱敏的字段标签 */
export const DESENSITIZE_FIELD_LABELS = new Set([
  "姓名",
  "学号",
  "手机",
  "邮箱",
  "证件号",
  "出生日期",
  "通信地址",
  "籍贯",
  "学校",
  "学校名称",
  "专业",
  "专业名称",
  "院系",
  "院系名称",
  "班级",
  "班级名称",
  "学历"
]);

function maskMiddle(str, keepStart, keepEnd, maskChar = "*") {
  const s = String(str ?? "").trim();
  if (!s) return s;
  const len = s.length;
  if (len <= keepStart + keepEnd) {
    if (len <= 1) return maskChar;
    if (len === 2) return s[0] + maskChar;
    return s[0] + maskChar.repeat(len - 2) + s[len - 1];
  }
  return s.slice(0, keepStart) + maskChar.repeat(len - keepStart - keepEnd) + s.slice(-keepEnd);
}

/** 姓名：保留首尾，中间 * */
export function maskName(name) {
  const s = String(name ?? "").trim();
  if (!s) return s;
  if (s.length === 1) return "*";
  if (s.length === 2) return `${s[0]}*`;
  return `${s[0]}${"*".repeat(Math.min(s.length - 2, 2))}${s.slice(-1)}`;
}

/** 手机：138****5678 */
export function maskPhone(phone) {
  const s = String(phone ?? "").trim();
  if (!s) return s;
  const digits = s.replace(/\D/g, "");
  if (digits.length >= 7) {
    return maskMiddle(digits, 3, 4);
  }
  return maskMiddle(s, 2, 1);
}

/** 邮箱：z***@example.com */
export function maskEmail(email) {
  const s = String(email ?? "").trim();
  if (!s) return s;
  const at = s.indexOf("@");
  if (at <= 0) return maskMiddle(s, 1, 0);
  const local = s.slice(0, at);
  const domain = s.slice(at);
  const maskedLocal = local.length <= 1 ? "*" : `${local[0]}${"*".repeat(Math.min(local.length - 1, 3))}`;
  return maskedLocal + domain;
}

/** 学号：前 4 + **** + 后 2 */
export function maskStudentId(id) {
  const s = String(id ?? "").trim();
  if (!s) return s;
  if (s.length <= 6) return maskMiddle(s, 2, 1);
  return maskMiddle(s, 4, 2);
}

/** 证件号：前 3 + **** + 后 4 */
export function maskIdCard(id) {
  const s = String(id ?? "").trim();
  if (!s) return s;
  if (s.length <= 7) return maskMiddle(s, 2, 2);
  return maskMiddle(s, 3, 4);
}

/** 出生日期：1990-**-** */
export function maskBirthDate(date) {
  const s = String(date ?? "").trim();
  if (!s) return s;
  const m = s.match(/^(\d{4})[-/.年]?(\d{1,2})[-/.月]?(\d{1,2})/);
  if (m) return `${m[1]}-**-**`;
  if (/^\d{4}/.test(s)) return `${s.slice(0, 4)}-**-**`;
  return maskMiddle(s, 2, 0);
}

/** 地址/籍贯：保留前段，其余 * */
export function maskAddress(addr) {
  const s = String(addr ?? "").trim();
  if (!s) return s;
  if (s.length <= 4) return maskMiddle(s, 1, 0);
  return `${s.slice(0, Math.min(6, s.length))}${"*".repeat(Math.min(4, Math.max(0, s.length - 6)))}`;
}

/** 学校/专业/院系等：保留前 2 字，其余 * */
export function maskOrgText(text, keepStart = 2) {
  const s = String(text ?? "").trim();
  if (!s) return s;
  if (s.length <= keepStart) return maskMiddle(s, 1, 0);
  return s.slice(0, keepStart) + "*".repeat(Math.min(s.length - keepStart, 4));
}

/** 班级：前 2 + * + 末 1 */
export function maskClassName(name) {
  const s = String(name ?? "").trim();
  if (!s) return s;
  if (s.length <= 3) return maskMiddle(s, 1, 0);
  return maskMiddle(s, 2, 1);
}

/** 学历：本* / 硕士** */
export function maskEducation(edu) {
  const s = String(edu ?? "").trim();
  if (!s) return s;
  if (s.length <= 2) return `${s[0]}*`;
  return maskOrgText(s, 2);
}

/** 按字段标签脱敏单个值 */
export function maskStudentField(label, value) {
  if (value == null || value === "" || value === "-") return value;
  switch (label) {
    case "姓名":
      return maskName(value);
    case "学号":
      return maskStudentId(value);
    case "手机":
      return maskPhone(value);
    case "邮箱":
      return maskEmail(value);
    case "证件号":
      return maskIdCard(value);
    case "出生日期":
      return maskBirthDate(value);
    case "通信地址":
    case "籍贯":
      return maskAddress(value);
    case "学校":
    case "学校名称":
      return maskOrgText(value, 2);
    case "专业":
    case "专业名称":
      return maskOrgText(value, 2);
    case "院系":
    case "院系名称":
      return maskOrgText(value, 2);
    case "班级":
    case "班级名称":
      return maskClassName(value);
    case "学历":
      return maskEducation(value);
    default:
      return value;
  }
}

/** 脱敏 { label, value }[] 供档案网格展示 */
export function maskFieldRows(rows) {
  return (rows || []).map((item) => ({
    ...item,
    value: maskStudentField(item.label, item.value)
  }));
}

/** 脱敏学生基本信息对象（浅拷贝） */
export function maskStudentInfoForDisplay(info) {
  if (!info || typeof info !== "object") return info || {};
  const out = { ...info };
  for (const key of Object.keys(out)) {
    if (DESENSITIZE_FIELD_LABELS.has(key)) {
      out[key] = maskStudentField(key, out[key]);
    }
  }
  return out;
}
