import { SECTION_ALIAS_GROUPS } from "./templates";
import { newResumeId } from "./storage";

/**
 * @typedef {{ id: string, title: string, body: string }} SectionItem
 */

/** @returns {SectionItem} */
export function newSectionItem(title = "", body = "") {
  return {
    id: newResumeId(),
    title: String(title || "").trim(),
    body: String(body || "").trim()
  };
}

/**
 * 兼容旧版 string 与新版 SectionItem[]。
 * @param {unknown} raw
 * @returns {SectionItem[]}
 */
export function normalizeSectionItems(raw) {
  if (Array.isArray(raw)) {
    const items = raw.map((item) => {
      if (item && typeof item === "object") {
        return newSectionItem(item.title, item.body ?? item.content ?? "");
      }
      return newSectionItem("", String(item ?? ""));
    });
    return items.length ? items : [newSectionItem()];
  }
  const text = String(raw ?? "").trim();
  if (!text) return [newSectionItem()];
  return [newSectionItem("", text)];
}

/**
 * @param {import('./templates').ResumeTemplate} template
 * @param {string} sectionKey
 */
export function sectionAllowsMultiple(template, sectionKey) {
  const cfg = template?.sections?.[sectionKey];
  if (cfg && typeof cfg.multi === "boolean") return cfg.multi;
  const singleOnly = [
    "教育背景",
    "自我评价",
    "个人风格",
    "求职意向说明",
    "技术栈",
    "技能与证书",
    "技能与荣誉",
    "学术技能",
    "研究兴趣",
    "业绩亮点"
  ];
  if (singleOnly.includes(sectionKey)) return false;
  const multiHint = ["经历", "项目", "作品", "科研", "论文", "专利", "竞赛", "开源", "获奖"];
  return multiHint.some((h) => sectionKey.includes(h));
}

/** @param {import('./templates').ResumeTemplate} template */
export function emptySectionsForTemplate(template) {
  const keys = template?.sectionKeys || [];
  return Object.fromEntries(keys.map((k) => [k, [newSectionItem()]]));
}

/**
 * @param {Record<string, unknown>} prevSections
 * @param {import('./templates').ResumeTemplate} fromTemplate
 * @param {import('./templates').ResumeTemplate} toTemplate
 * @returns {Record<string, SectionItem[]>}
 */
export function mapSectionsOnTemplateChange(prevSections, fromTemplate, toTemplate) {
  const fromKeys = new Set(fromTemplate.sectionKeys);
  const result = {};
  for (const key of toTemplate.sectionKeys) {
    if (fromTemplate.sectionKeys.includes(key)) {
      const items = normalizeSectionItems(prevSections[key]);
      if (items.some((i) => i.body || i.title)) {
        result[key] = items.map((i) => ({ ...i, id: newResumeId() }));
        continue;
      }
    }
    const group = SECTION_ALIAS_GROUPS.find((g) => g.includes(key));
    if (group) {
      const donorKey = group.find((k) => {
        if (!fromKeys.has(k)) return false;
        return normalizeSectionItems(prevSections[k]).some((i) => i.body || i.title);
      });
      if (donorKey) {
        result[key] = normalizeSectionItems(prevSections[donorKey]).map((i) => ({
          ...i,
          id: newResumeId()
        }));
        continue;
      }
    }
    result[key] = [newSectionItem()];
  }
  return result;
}

/**
 * @param {SectionItem[]} items
 * @param {{ numbered?: boolean }} [opts]
 */
export function formatSectionItemsText(items, opts = {}) {
  const list = (items || []).filter((i) => i.body.trim() || i.title.trim());
  if (!list.length) return "";
  const numbered = opts.numbered !== false && list.length > 1;
  return list
    .map((item, idx) => {
      const prefix = numbered ? `${idx + 1}. ` : "";
      const head = item.title ? `${prefix}${item.title}` : numbered ? `${idx + 1}.` : "";
      if (head && item.body) return `${head}\n${item.body}`;
      return head || item.body;
    })
    .join("\n\n");
}

/**
 * 持久化：统一为数组格式写入 JSON。
 * @param {Record<string, SectionItem[] | unknown>} sections
 */
export function serializeSections(sections) {
  const out = {};
  for (const [key, raw] of Object.entries(sections || {})) {
    out[key] = normalizeSectionItems(raw).map(({ id, title, body }) => ({ id, title, body }));
  }
  return out;
}
