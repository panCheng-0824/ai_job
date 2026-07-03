import { SCORE_DIMENSION_DEFS } from "../constants/jobScoreRubric";
import { parseJobMatchReason } from "./jobMatchReason";
import { normalizeJobId } from "./jobId";

/** @param {string} label */
function escapeRegExp(label) {
  return label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * 从【评分依据】段落解析五维得分（维度名 X/Y 分）。
 * @param {string} text
 * @returns {{ key: string, label: string, score: number|null, max: number|null }[]}
 */
export function parseDimensionScoresFromText(text) {
  const raw = String(text || "").trim();
  if (!raw) return [];

  return SCORE_DIMENSION_DEFS.map((def) => {
    const pattern = new RegExp(
      `${escapeRegExp(def.label)}[^\\d]{0,24}(\\d+)\\s*[/／]\\s*(\\d+)`,
      "i"
    );
    const m = raw.match(pattern);
    if (!m) {
      return { key: def.key, label: def.label, score: null, max: null };
    }
    return {
      key: def.key,
      label: def.label,
      score: Number(m[1]),
      max: Number(m[2])
    };
  });
}

/**
 * @param {{ key: string, title?: string, body?: string }[]} sections
 */
export function parseDimensionScoresFromSections(sections) {
  const basis = (sections || []).find((s) => s.key === "score_basis")?.body || "";
  if (basis) return parseDimensionScoresFromText(basis);
  return [];
}

/**
 * @param {object} job
 */
export function resolveJobDimensionScores(job) {
  const sections = Array.isArray(job?.match_reason_sections) ? job.match_reason_sections : null;
  if (sections?.length) {
    const parsed = parseDimensionScoresFromSections(sections);
    if (parsed.some((d) => d.score != null)) return parsed;
  }
  const reason =
    String(job?.match_reason || "").trim() ||
    (Array.isArray(job?.match_reasons) ? job.match_reasons.join("；") : "");
  if (reason) {
    const sectionsFromReason = parseJobMatchReason(reason);
    const parsed = parseDimensionScoresFromSections(sectionsFromReason);
    if (parsed.some((d) => d.score != null)) return parsed;
    return parseDimensionScoresFromText(reason);
  }
  return SCORE_DIMENSION_DEFS.map((def) => ({
    key: def.key,
    label: def.label,
    score: null,
    max: null
  }));
}

/** @param {object} job */
function formatSalary(job) {
  const range = String(job?.salary_range_month || job?.salary || "").trim();
  if (range) return range;

  const min = job?.salary_min;
  const max = job?.salary_max;
  const minK = min != null ? `${Number(min) / 1000}k` : "";
  const maxK = max != null ? `${Number(max) / 1000}k` : "";
  if (minK && maxK) return `${minK}-${maxK}`;
  if (minK) return `${minK}起`;
  if (maxK) return `最高${maxK}`;
  return "-";
}

/**
 * 统一智能匹配岗位与 server_job 岗位字段，供对比弹窗展示。
 * @param {object} job
 */
export function resolveJobCompareView(job) {
  const scoreRaw = job?.score ?? job?.match_score;
  const score =
    scoreRaw == null || scoreRaw === "" ? null : Math.round(Number(scoreRaw));

  return {
    jobId: job?.job_id || job?.id || "",
    title: job?.job_title || job?.job_name || "-",
    company: job?.company_name || job?.company_relation?.company_name || "-",
    city: job?.city || job?.job_city || "-",
    salary: formatSalary(job),
    edu: job?.edu_level || job?.job_edu || job?.education || "-",
    exp: job?.exp_req || job?.job_exp || job?.experience || "-",
    category: job?.job_category || "-",
    score,
    dimensions: resolveJobDimensionScores(job)
  };
}

/**
 * @param {ReturnType<typeof resolveJobCompareView>[]} jobs
 */
export function buildDimensionCompareRows(jobs) {
  return SCORE_DIMENSION_DEFS.map((def) => ({
    key: def.key,
    label: def.label,
    desc: def.desc,
    cells: (jobs || []).map((job) => {
      const hit = job.dimensions?.find((d) => d.key === def.key);
      if (hit?.score != null && hit?.max != null) {
        const ratio = hit.max > 0 ? hit.score / hit.max : 0;
        return {
          text: `${hit.score}/${hit.max}`,
          score: hit.score,
          max: hit.max,
          ratio,
          hasData: true
        };
      }
      return { text: "-", score: null, max: null, ratio: 0, hasData: false };
    })
  }));
}

/**
 * 找出某行最优列索引（得分最高；并列则全部高亮）。
 * @param {{ score: number|null, hasData?: boolean }[]} cells
 */
export function findBestCellIndices(cells) {
  const valid = (cells || [])
    .map((c, i) => ({ i, score: c.score, hasData: c.hasData }))
    .filter((x) => x.hasData && x.score != null);
  if (!valid.length) return new Set();
  const top = Math.max(...valid.map((x) => x.score));
  return new Set(valid.filter((x) => x.score === top).map((x) => x.i));
}

/** @param {number|null} score */
export function scoreTone(score) {
  if (score == null) return "muted";
  if (score >= 90) return "excellent";
  if (score >= 80) return "good";
  if (score >= 70) return "fair";
  return "low";
}

/**
 * 合并 recommendation 中的理由/得分，避免对比弹窗缺字段。
 * @param {object} job
 * @param {object|null|undefined} recHit
 */
export function mergeJobWithRecommendation(job, recHit) {
  if (!recHit) return job;
  return {
    ...job,
    score: recHit.score ?? job.score ?? job.match_score,
    match_score: recHit.score ?? job.match_score ?? job.score,
    match_reason: recHit.match_reason || job.match_reason,
    match_reasons: recHit.match_reasons?.length ? recHit.match_reasons : job.match_reasons,
    match_reason_sections: recHit.match_reason_sections?.length
      ? recHit.match_reason_sections
      : job.match_reason_sections,
    company_name: job.company_name || recHit.company_name,
    city: job.city || recHit.city,
    salary_range_month: job.salary_range_month || recHit.salary_range_month,
    job_category: job.job_category || recHit.job_category
  };
}

/**
 * 按已选 ID 收集岗位并合并 recommendation 字段。
 * @param {object[]} allJobs
 * @param {Array<string|number>} selectedIds
 * @param {object|null|undefined} recommendation
 */
export function pickJobsForCompare(allJobs, selectedIds, recommendation) {
  const idSet = new Set((selectedIds || []).map(normalizeJobId));
  const recMap = new Map(
    (recommendation?.recommended_jobs || []).map((r) => [normalizeJobId(r.job_id), r])
  );
  return (allJobs || [])
    .filter((j) => idSet.has(normalizeJobId(j.job_id || j.id)))
    .map((j) => mergeJobWithRecommendation(j, recMap.get(normalizeJobId(j.job_id || j.id))));
}
