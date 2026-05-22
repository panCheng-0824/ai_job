import { parseResumeContent } from "./content";
import { emptySectionsForTemplate, normalizeSectionItems } from "./sectionsModel";
import { newResumeId } from "./storage";

/**
 * 将后端 resume_render（或 parseResumeContent 同构对象）合并进编辑器状态。
 *
 * @param {object} opts
 * @param {unknown} opts.payload SSE / done 中的 resume_render 块
 * @param {import('./templates').ResumeTemplate} opts.template 当前模版
 * @param {Record<string, string>} opts.basic
 * @param {{ targetJobs: string, targetCompanies: string }} opts.intent
 * @param {Record<string, import('./sectionsModel').SectionItem[]>} opts.sections
 * @param {string} opts.extraNotes
 * @param {{ mergeBasic?: boolean }} [opts.options]
 */
export function mergeResumeRenderIntoEditor({
  payload,
  template,
  basic,
  intent,
  sections,
  extraNotes,
  options = {}
}) {
  const { mergeBasic = true } = options;
  const content = parseResumeContent(payload);
  const tpl = template;
  const sectionKeys = tpl?.sectionKeys || [];

  const nextBasic = { ...basic };
  if (mergeBasic) {
    for (const [k, v] of Object.entries(content.basic || {})) {
      const val = String(v ?? "").trim();
      if (val) nextBasic[k] = val;
    }
  }

  const nextIntent = {
    targetJobs: String(content.intent?.targetJobs ?? intent?.targetJobs ?? "").trim(),
    targetCompanies: String(content.intent?.targetCompanies ?? intent?.targetCompanies ?? "").trim()
  };

  const baseSections =
    sections && Object.keys(sections).length
      ? { ...sections }
      : emptySectionsForTemplate(tpl);

  const nextSections = { ...baseSections };
  const incomingSections = content.sections || {};

  for (const key of sectionKeys) {
    const items = normalizeSectionItems(incomingSections[key]);
    const hasContent = items.some((i) => i.title || i.body);
    if (hasContent) {
      nextSections[key] = items.map((i) => ({ ...i, id: newResumeId() }));
    } else if (!nextSections[key]?.length) {
      nextSections[key] = normalizeSectionItems(nextSections[key]);
    }
  }

  for (const [key, raw] of Object.entries(incomingSections)) {
    if (sectionKeys.includes(key)) continue;
    const items = normalizeSectionItems(raw);
    if (items.some((i) => i.title || i.body)) {
      nextSections[key] = items.map((i) => ({ ...i, id: newResumeId() }));
    }
  }

  const nextExtra =
    String(content.extraNotes ?? "").trim() || String(extraNotes ?? "").trim();

  return {
    basic: nextBasic,
    intent: nextIntent,
    sections: nextSections,
    extraNotes: nextExtra
  };
}
