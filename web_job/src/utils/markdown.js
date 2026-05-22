/**
 * 对话气泡 Markdown → 安全 HTML（供 ChatView 助手消息渲染）。
 */
import DOMPurify from "dompurify";
import { marked } from "marked";

marked.setOptions({
  gfm: true,
  breaks: true,
});

DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A") {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  }
});

const PLACEHOLDER_RE = /^「语音播报」|^深度思考中|^（已中止）|^（查询为空）/;

const PURIFY_OPTS = {
  USE_PROFILES: { html: true },
  ADD_ATTR: ["target", "rel"],
};

/** 流式阶段占位、极短提示：不做 MD 解析，避免闪烁 */
function isPlainPlaceholder(text) {
  const t = String(text || "").trim();
  if (!t) return true;
  if (PLACEHOLDER_RE.test(t)) return true;
  if (t.length < 8 && !/[#*_`\[]/.test(t)) return true;
  return false;
}

/**
 * 将助手回复 Markdown 转为可 v-html 的安全 HTML。
 * @param {string} source
 * @returns {string}
 */
export function renderChatMarkdown(source) {
  const raw = String(source ?? "");
  if (!raw.trim()) return "";

  if (isPlainPlaceholder(raw)) {
    return escapeHtml(raw).replace(/\n/g, "<br>");
  }

  const html = marked.parse(raw);
  return DOMPurify.sanitize(html, PURIFY_OPTS);
}

/** 是否为岗位推荐类 Markdown（用于附加卡片样式） */
export function isJobRecommendMarkdown(source) {
  return /岗位推荐结果/.test(String(source || ""));
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
