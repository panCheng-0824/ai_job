import { prefillBasicFromPortrait } from "./prefill";

/**
 * 统一解析接口/本地存储中的 content（兼容 JSON 字符串、空值）。
 * @param {unknown} raw
 * @returns {{ templateId: string, basic: Record<string, string>, intent: Record<string, string>, sections: Record<string, unknown>, extraNotes: string }}
 */
export function parseResumeContent(raw) {
  let c = raw;
  if (typeof c === "string") {
    try {
      c = JSON.parse(c);
    } catch {
      c = {};
    }
  }
  if (!c || typeof c !== "object" || Array.isArray(c)) {
    c = {};
  }
  const basicRaw = c.basic;
  let basic = {};
  if (basicRaw && typeof basicRaw === "object" && !Array.isArray(basicRaw)) {
    basic = Object.fromEntries(
      Object.entries(basicRaw).map(([k, v]) => [k, String(v ?? "").trim()])
    );
  }
  const intentRaw = c.intent;
  const intent =
    intentRaw && typeof intentRaw === "object" && !Array.isArray(intentRaw)
      ? {
          targetJobs: String(intentRaw.targetJobs ?? "").trim(),
          targetCompanies: String(intentRaw.targetCompanies ?? "").trim()
        }
      : { targetJobs: "", targetCompanies: "" };
  const sections =
    c.sections && typeof c.sections === "object" && !Array.isArray(c.sections) ? c.sections : {};
  return {
    templateId: String(c.templateId ?? c.template_id ?? "").trim(),
    basic,
    intent,
    sections,
    extraNotes: String(c.extraNotes ?? "").trim()
  };
}

/**
 * 保存用：合并默认字段，确保 basic 键完整且为字符串。
 * @param {Record<string, string>} basicValues
 */
export function buildBasicForSave(basicValues) {
  const base = prefillBasicFromPortrait(null);
  const merged = { ...base, ...(basicValues || {}) };
  return Object.fromEntries(
    Object.keys(base).map((k) => [k, String(merged[k] ?? "").trim()])
  );
}
