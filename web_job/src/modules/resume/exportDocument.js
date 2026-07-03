import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import {
  AlignmentType,
  Document,
  HeadingLevel,
  Packer,
  Paragraph,
  TextRun
} from "docx";
import { parseResumeContent } from "./content";
import { formatSectionItemsText, normalizeSectionItems } from "./sectionsModel";
import { getTemplateById } from "./templates";

/** @typedef {'json' | 'pdf' | 'docx'} ResumeExportFormat */

export const RESUME_EXPORT_FORMAT_LABELS = {
  pdf: "PDF",
  docx: "Word",
  json: "JSON"
};

/**
 * 文件名安全化。
 * @param {string} name
 */
export function safeResumeFileName(name) {
  return (String(name || "简历").replace(/[/\\?%*:|"<>]/g, "-").trim() || "简历");
}

/**
 * @param {Blob} blob
 * @param {string} filename
 */
export function downloadBlob(blob, filename) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/**
 * @param {Record<string, string>} basic
 */
export function buildHeroFromBasic(basic) {
  const b = basic || {};
  return {
    name: String(b.姓名 || "").trim() || "同学",
    subtitle: [b.学校, b.院系, b.专业, b.学历, b.毕业时间]
      .map((v) => String(v ?? "").trim())
      .filter(Boolean)
      .join(" | "),
    phone: String(b.手机 ?? "").trim(),
    email: String(b.邮箱 ?? "").trim()
  };
}

/**
 * 从简历记录或编辑器状态构建导出模型。
 * @param {object} opts
 * @param {import('./templates').ResumeTemplate} opts.template
 * @param {Record<string, string>} opts.basic
 * @param {{ targetJobs: string, targetCompanies: string }} opts.intent
 * @param {Record<string, unknown>} opts.sections
 * @param {string} [opts.extraNotes]
 * @param {string} [opts.displayName]
 */
export function buildResumeDocumentModel({
  template,
  basic,
  intent,
  sections,
  extraNotes = "",
  displayName = ""
}) {
  const tpl = template || getTemplateById("standard_cn");
  const hero = buildHeroFromBasic(basic);
  const sectionBlocks = [];

  for (const key of tpl.sectionKeys || []) {
    const text = formatSectionItemsText(normalizeSectionItems(sections?.[key]));
    if (!text) continue;
    sectionBlocks.push({ key, text, items: normalizeSectionItems(sections?.[key]) });
  }

  const targetJobs = String(intent?.targetJobs ?? "").trim();
  const targetCompanies = String(intent?.targetCompanies ?? "").trim();
  const showIntent = tpl.intentMode === "full" && (targetJobs || targetCompanies);

  return {
    displayName: String(displayName || hero.name || "简历").trim() || "简历",
    template: tpl,
    basic: basic || {},
    hero,
    intent: { targetJobs, targetCompanies },
    showIntent,
    sectionBlocks,
    extraNotes: String(extraNotes ?? "").trim()
  };
}

/**
 * @param {object} rec 简历版本记录
 * @param {import('./templates').ResumeTemplate} [fallbackTemplate]
 */
export function buildResumeDocumentModelFromRecord(rec, fallbackTemplate) {
  const content = parseResumeContent(rec?.content);
  const template = getTemplateById(rec?.templateId || content.templateId) || fallbackTemplate;
  return buildResumeDocumentModel({
    template,
    basic: content.basic,
    intent: content.intent,
    sections: content.sections,
    extraNotes: content.extraNotes,
    displayName: rec?.displayName || ""
  });
}

/**
 * @param {ReturnType<typeof buildResumeDocumentModel>} model
 */
function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * @param {string} text
 */
function textToHtmlBlocks(text) {
  const lines = String(text || "").split("\n");
  const parts = [];
  let listOpen = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (listOpen) {
        parts.push("</ul>");
        listOpen = false;
      }
      continue;
    }
    if (trimmed.startsWith("- ")) {
      if (!listOpen) {
        parts.push('<ul style="margin:4px 0 8px;padding-left:20px;">');
        listOpen = true;
      }
      parts.push(`<li style="margin:2px 0;">${escapeHtml(trimmed.slice(2))}</li>`);
    } else {
      if (listOpen) {
        parts.push("</ul>");
        listOpen = false;
      }
      parts.push(`<p style="margin:4px 0 8px;line-height:1.55;">${escapeHtml(trimmed)}</p>`);
    }
  }
  if (listOpen) parts.push("</ul>");
  return parts.join("");
}

/**
 * @param {ReturnType<typeof buildResumeDocumentModel>} model
 */
export function buildResumeExportHtml(model) {
  const accent = model.template?.accent || "#4f46e5";
  const { hero, showIntent, intent, sectionBlocks, extraNotes } = model;
  const contact = [hero.phone, hero.email].filter(Boolean).map(escapeHtml).join(" · ");

  const sectionsHtml = sectionBlocks
    .map(({ key, text }) => {
      return `
        <section style="margin-top:18px;">
          <h2 style="margin:0 0 8px;font-size:15px;font-weight:700;color:${accent};border-left:3px solid ${accent};padding-left:8px;">${escapeHtml(key)}</h2>
          <div style="font-size:13px;line-height:1.55;color:#334155;">${textToHtmlBlocks(text)}</div>
        </section>`;
    })
    .join("");

  const intentHtml = showIntent
    ? `
        <section style="margin-top:16px;">
          <h2 style="margin:0 0 8px;font-size:15px;font-weight:700;color:${accent};border-left:3px solid ${accent};padding-left:8px;">求职意向</h2>
          <div style="font-size:13px;line-height:1.55;color:#334155;">
            ${intent.targetJobs ? `<p style="margin:4px 0;">意向岗位：${escapeHtml(intent.targetJobs)}</p>` : ""}
            ${intent.targetCompanies ? `<p style="margin:4px 0;">意向企业：${escapeHtml(intent.targetCompanies)}</p>` : ""}
          </div>
        </section>`
    : "";

  const notesHtml = extraNotes
    ? `
        <section style="margin-top:18px;">
          <h2 style="margin:0 0 8px;font-size:15px;font-weight:700;color:${accent};border-left:3px solid ${accent};padding-left:8px;">补充说明</h2>
          <div style="font-size:13px;line-height:1.55;color:#334155;">${textToHtmlBlocks(extraNotes)}</div>
        </section>`
    : "";

  return `
    <div style="width:794px;padding:48px 44px;box-sizing:border-box;font-family:'PingFang SC','Microsoft YaHei','Noto Sans SC',sans-serif;color:#0f172a;background:#fff;">
      <header style="padding-bottom:14px;border-bottom:2px solid ${accent};">
        <h1 style="margin:0;font-size:28px;font-weight:800;line-height:1.25;">${escapeHtml(hero.name)}</h1>
        ${hero.subtitle ? `<p style="margin:8px 0 0;font-size:14px;color:#64748b;">${escapeHtml(hero.subtitle)}</p>` : ""}
        ${contact ? `<p style="margin:10px 0 0;font-size:13px;color:#475569;">${contact}</p>` : ""}
      </header>
      ${intentHtml}
      ${sectionsHtml}
      ${notesHtml}
    </div>`;
}

/**
 * @param {HTMLElement} element
 * @param {string} filename
 */
export async function exportElementToPdf(element, filename) {
  const canvas = await html2canvas(element, {
    scale: 2,
    useCORS: true,
    backgroundColor: "#ffffff",
    logging: false
  });
  const imgData = canvas.toDataURL("image/png");
  const pdf = new jsPDF({ orientation: "p", unit: "mm", format: "a4" });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const imgWidth = pageWidth;
  const imgHeight = (canvas.height * imgWidth) / canvas.width;

  let heightLeft = imgHeight;
  let position = 0;

  pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
  heightLeft -= pageHeight;

  while (heightLeft > 0) {
    position = heightLeft - imgHeight;
    pdf.addPage();
    pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;
  }

  pdf.save(filename);
}

/**
 * @param {ReturnType<typeof buildResumeDocumentModel>} model
 */
export async function exportResumeToPdf(model) {
  const host = document.createElement("div");
  host.style.position = "fixed";
  host.style.left = "-12000px";
  host.style.top = "0";
  host.style.zIndex = "-1";
  host.innerHTML = buildResumeExportHtml(model);
  document.body.appendChild(host);
  const page = host.firstElementChild;
  try {
    const base = safeResumeFileName(model.displayName);
    await exportElementToPdf(page, `${base}.pdf`);
  } finally {
    document.body.removeChild(host);
  }
}

/**
 * @param {string} text
 */
function bodyToDocxParagraphs(text) {
  const lines = String(text || "").split("\n");
  /** @type {Paragraph[]} */
  const paragraphs = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith("- ")) {
      paragraphs.push(
        new Paragraph({
          text: trimmed.slice(2),
          bullet: { level: 0 },
          spacing: { after: 80 }
        })
      );
    } else {
      paragraphs.push(
        new Paragraph({
          children: [new TextRun(trimmed)],
          spacing: { after: 100 }
        })
      );
    }
  }
  return paragraphs;
}

/**
 * @param {import('./sectionsModel').SectionItem[]} items
 */
function sectionItemsToDocxParagraphs(items) {
  const list = (items || []).filter((i) => i.body.trim() || i.title.trim());
  /** @type {Paragraph[]} */
  const paragraphs = [];
  for (const item of list) {
    if (item.title) {
      paragraphs.push(
        new Paragraph({
          children: [new TextRun({ text: item.title, bold: true })],
          spacing: { before: 120, after: 60 }
        })
      );
    }
    paragraphs.push(...bodyToDocxParagraphs(item.body));
  }
  return paragraphs;
}

/**
 * @param {ReturnType<typeof buildResumeDocumentModel>} model
 */
export async function exportResumeToDocx(model) {
  const { hero, showIntent, intent, sectionBlocks, extraNotes } = model;
  /** @type {Paragraph[]} */
  const children = [
    new Paragraph({
      children: [new TextRun({ text: hero.name, bold: true, size: 36 })],
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.LEFT,
      spacing: { after: 120 }
    })
  ];

  if (hero.subtitle) {
    children.push(
      new Paragraph({
        children: [new TextRun({ text: hero.subtitle, color: "64748B", size: 22 })],
        spacing: { after: 80 }
      })
    );
  }

  const contact = [hero.phone, hero.email].filter(Boolean).join("  ·  ");
  if (contact) {
    children.push(
      new Paragraph({
        children: [new TextRun({ text: contact, size: 20 })],
        spacing: { after: 200 }
      })
    );
  }

  if (showIntent) {
    children.push(
      new Paragraph({
        text: "求职意向",
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 160, after: 100 }
      })
    );
    if (intent.targetJobs) {
      children.push(new Paragraph({ text: `意向岗位：${intent.targetJobs}`, spacing: { after: 80 } }));
    }
    if (intent.targetCompanies) {
      children.push(new Paragraph({ text: `意向企业：${intent.targetCompanies}`, spacing: { after: 120 } }));
    }
  }

  for (const block of sectionBlocks) {
    children.push(
      new Paragraph({
        text: block.key,
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      })
    );
    children.push(...sectionItemsToDocxParagraphs(block.items));
  }

  if (extraNotes) {
    children.push(
      new Paragraph({
        text: "补充说明",
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      })
    );
    children.push(...bodyToDocxParagraphs(extraNotes));
  }

  const doc = new Document({
    sections: [{ properties: {}, children }]
  });
  const blob = await Packer.toBlob(doc);
  const base = safeResumeFileName(model.displayName);
  downloadBlob(blob, `${base}.docx`);
}

/**
 * @param {object} payload JSON 导出载荷（与历史 exportJson 一致）
 */
export function exportResumeToJson(payload) {
  const name = safeResumeFileName(payload?.displayName || "简历");
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8"
  });
  downloadBlob(blob, `${name}.json`);
}

/**
 * @param {ResumeExportFormat} format
 * @param {ReturnType<typeof buildResumeDocumentModel>} model
 * @param {object} [jsonPayload]
 */
export async function exportResumeByFormat(format, model, jsonPayload) {
  if (format === "json") {
    exportResumeToJson(jsonPayload);
    return;
  }
  if (format === "pdf") {
    await exportResumeToPdf(model);
    return;
  }
  if (format === "docx") {
    await exportResumeToDocx(model);
    return;
  }
  throw new Error(`不支持的导出格式：${format}`);
}
