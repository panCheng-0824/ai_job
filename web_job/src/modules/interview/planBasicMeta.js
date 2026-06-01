/**
 * 大纲基础信息展示辅助 — 状态标签、模块标签解析。
 */
import { PLAN_STATUS } from "./constants";

/** @returns {{ label: string, tone: string }} */
export function planStatusMeta(status) {
  const toneMap = {
    draft: "draft",
    published: "published",
    archived: "archived"
  };
  const meta = PLAN_STATUS[status];
  return {
    label: meta?.label || status || "—",
    tone: toneMap[status] || "muted"
  };
}

/** 表单 module_tags 字符串或 API 数组 → 标签列表 */
export function parseModuleTags(raw) {
  if (Array.isArray(raw)) return raw.filter(Boolean);
  return String(raw || "")
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean);
}
