import { formatSectionItemsText, normalizeSectionItems } from "./sectionsModel";

/**
 * 与 ResumeCreateView「实时预览」一致的纯文本（供 AI 优化基准）。
 *
 * @param {object} opts
 * @param {import('./templates').ResumeTemplate} opts.template
 * @param {Record<string, string>} opts.basic
 * @param {{ targetJobs: string, targetCompanies: string }} opts.intent
 * @param {Record<string, unknown>} opts.sections
 * @param {string} [opts.extraNotes]
 */
export function formatResumePreviewText({ template, basic, intent, sections, extraNotes = "" }) {
  const t = template;
  if (!t) return "";

  const lines = [];
  lines.push(`【${t.name}】 ${t.badge ? `· ${t.badge}` : ""}`.trim());
  if (t.description) lines.push(t.description);
  lines.push("");
  lines.push("—— 基本信息 ——");
  Object.entries(basic || {}).forEach(([k, v]) => {
    if (String(v ?? "").trim()) lines.push(`${k}：${v}`);
  });

  const targetJobs = String(intent?.targetJobs ?? "").trim();
  const targetCompanies = String(intent?.targetCompanies ?? "").trim();
  const hasIntent = targetJobs || targetCompanies;
  if (t.intentMode === "full" && hasIntent) {
    lines.push("");
    lines.push("—— 求职意向 ——");
    if (targetJobs) lines.push(`意向岗位：${targetJobs}`);
    if (targetCompanies) lines.push(`意向企业：${targetCompanies}`);
  }

  lines.push("");
  for (const key of t.sectionKeys || []) {
    const text = formatSectionItemsText(normalizeSectionItems(sections?.[key]));
    if (!text) continue;
    lines.push(`—— ${key} ——`);
    lines.push(text);
    lines.push("");
  }

  const notes = String(extraNotes ?? "").trim();
  if (notes) {
    lines.push("—— 补充说明 ——");
    lines.push(notes);
  }
  return lines.join("\n").trim();
}

/**
 * 预览是否有实质内容（用于启用「带入左侧表单」）。
 */
export function resumePreviewHasContent(previewText) {
  const t = String(previewText || "").trim();
  if (!t) return false;
  const bodyLines = t.split("\n").filter((line) => {
    const s = line.trim();
    if (!s) return false;
    if (s.startsWith("【") && s.endsWith("】")) return false;
    if (s.startsWith("——") && s.endsWith("——")) return false;
    return true;
  });
  return bodyLines.length > 0;
}
