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
