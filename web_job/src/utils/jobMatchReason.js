/** 岗位推荐理由分段（与 ai_job reason_format.py 标题约定一致） */
export const JOB_MATCH_REASON_SECTIONS = [
  { key: "conclusion", title: "匹配结论", prefixes: ["【匹配结论】", "①匹配结论：", "①匹配结论:"] },
  { key: "score_basis", title: "评分依据", prefixes: ["【评分依据】", "②评分依据：", "②评分依据:"] },
  { key: "evidence", title: "素材依据", prefixes: ["【素材依据】", "③素材依据：", "③素材依据:"] },
  { key: "gap", title: "差异提示", prefixes: ["【差异提示】", "④差异提示：", "④差异提示:"] }
];

/**
 * @param {string} text
 * @returns {{ key: string, title: string, body: string }[]}
 */
export function parseJobMatchReason(text) {
  const raw = String(text || "").trim();
  if (!raw) return [];

  const markers = [];
  for (const spec of JOB_MATCH_REASON_SECTIONS) {
    for (const prefix of spec.prefixes) {
      const idx = raw.indexOf(prefix);
      if (idx >= 0) {
        markers.push({ idx, key: spec.key, title: spec.title, prefix });
        break;
      }
    }
  }

  if (!markers.length) {
    return [{ key: "full", title: "推荐理由", body: raw }];
  }

  markers.sort((a, b) => a.idx - b.idx);
  const out = [];
  for (let i = 0; i < markers.length; i += 1) {
    const { key, title, prefix } = markers[i];
    const start = raw.indexOf(prefix) + prefix.length;
    const end = i + 1 < markers.length ? markers[i + 1].idx : raw.length;
    const body = raw.slice(start, end).trim().replace(/^[；;]+|[；;]+$/g, "");
    if (body) out.push({ key, title, body });
  }
  return out;
}

/** @param {string} text */
export function jobMatchReasonCharCount(text) {
  return String(text || "").replace(/\s+/g, "").length;
}

/**
 * @param {{ match_reason?: string, match_reason_sections?: object[], match_reasons?: string[], score?: number, job_id?: string|number }} hit
 * @param {{ match_reasons?: string[], match_reason_sections?: object[], score?: number, job_id?: string|number }} [job]
 */
export function resolveJobMatchReasonDisplay(hit, job) {
  const reason =
    String(hit?.match_reason || "").trim() ||
    (Array.isArray(hit?.match_reasons) && hit.match_reasons.length ? hit.match_reasons.join("；") : "") ||
    (Array.isArray(job?.match_reasons) && job.match_reasons.length ? job.match_reasons.join("；") : "");

  let sections = Array.isArray(hit?.match_reason_sections) ? hit.match_reason_sections : null;
  if (!sections?.length && Array.isArray(job?.match_reason_sections) && job.match_reason_sections.length) {
    sections = job.match_reason_sections;
  }
  if (!sections?.length) {
    sections = parseJobMatchReason(reason);
  }

  return {
    reason,
    sections,
    charCount: jobMatchReasonCharCount(reason),
    score: hit?.score ?? job?.score ?? null
  };
}
