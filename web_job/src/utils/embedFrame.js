/** 与 PortalNavWheel / JobRecommendPanel 一致的嵌入页 URL */
export function embedUrl(path, extraQuery = {}) {
  const u = new URL(path, window.location.origin);
  u.searchParams.set("_embed", "1");
  for (const [k, v] of Object.entries(extraQuery || {})) {
    if (v != null && String(v).trim() !== "") u.searchParams.set(k, String(v).trim());
  }
  return u.pathname + u.search + u.hash;
}

export function fullPageUrl(embedPath) {
  const u = new URL(embedPath, window.location.origin);
  u.searchParams.delete("_embed");
  return u.pathname + u.search + u.hash;
}

/** 嵌入/浮层场景：在新标签页打开详情（保持 _embed 简洁布局） */
export function openDetailInNewWindow(path, extraQuery = {}) {
  if (typeof window === "undefined") return null;
  const url = embedUrl(path, extraQuery);
  return window.open(url, "_blank", "noopener,noreferrer");
}
