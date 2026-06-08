/**
 * 岗位描述（zwms）、单位简介（dwjj）等富文本 HTML 的安全渲染与纯文本抽取。
 */
import DOMPurify from "dompurify";

const RICH_TEXT_PURIFY_OPTS = {
  USE_PROFILES: { html: true },
  ADD_ATTR: ["target", "rel", "style", "class", "align", "colspan", "rowspan"],
  ADD_TAGS: ["font", "span"],
};

let linkHookInstalled = false;

function ensureLinkHook() {
  if (linkHookInstalled) return;
  DOMPurify.addHook("afterSanitizeAttributes", (node) => {
    if (node.tagName === "A") {
      node.setAttribute("target", "_blank");
      node.setAttribute("rel", "noopener noreferrer");
    }
  });
  linkHookInstalled = true;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** 是否像 HTML 富文本（含标签） */
export function looksLikeHtml(source) {
  return /<[a-z][\s\S]*>/i.test(String(source || "").trim());
}

/**
 * 富文本 → 可 v-html 的安全 HTML。
 * @param {string} source
 * @returns {string}
 */
export function sanitizeRichHtml(source) {
  const raw = String(source ?? "").trim();
  if (!raw) return "";
  if (!looksLikeHtml(raw)) {
    return escapeHtml(raw).replace(/\n/g, "<br>");
  }
  ensureLinkHook();
  return DOMPurify.sanitize(raw, RICH_TEXT_PURIFY_OPTS);
}

/**
 * 富文本 → 纯文本（送入聊天隐藏上下文等）。
 * @param {string} source
 * @returns {string}
 */
export function richTextToPlain(source) {
  const raw = String(source ?? "").trim();
  if (!raw) return "";
  if (!looksLikeHtml(raw)) return raw;
  if (typeof document !== "undefined") {
    const div = document.createElement("div");
    div.innerHTML = DOMPurify.sanitize(raw, RICH_TEXT_PURIFY_OPTS);
    return (div.textContent || div.innerText || "")
      .replace(/\u00a0/g, " ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }
  return raw
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
