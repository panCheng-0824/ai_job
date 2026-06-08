import { apiGet } from "../api/client";

/** bm+dm → 中文名 的简单内存缓存 */
const cache = new Map();

/**
 * 将字典编码转为中文；已是文本则原样返回。
 * @param {string} bm sys_code.BM，如 job_dwxz
 * @param {unknown} raw API 字段值
 */
export async function resolveDictLabel(bm, raw) {
  const s = raw == null ? "" : String(raw).trim();
  if (!s) return "-";
  if (!/^\d+$/.test(s)) return s;

  const key = `${bm}:${s}`;
  if (cache.has(key)) return cache.get(key);

  try {
    const q = new URLSearchParams({ bm, dm: s });
    const resp = await apiGet(`/api/biz/sys-code/lookup?${q}`);
    const name = resp?.found && resp?.name ? String(resp.name).trim() : s;
    cache.set(key, name || s);
    return name || s;
  } catch {
    return s;
  }
}
