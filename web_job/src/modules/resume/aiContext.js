/**
 * 简历 AI 优化素材篮：岗位/企业条目结构（拖入、点击添加、跨页带入共用）
 */

/**
 * @param {Record<string, unknown> | null | undefined} job
 */
export function buildJobContextItem(job) {
  if (!job || typeof job !== "object") return null;
  const refId = job.job_id || job.id;
  if (!refId) return null;
  const normalized = { ...job, job_id: refId };
  return {
    kind: "job",
    refId: String(refId),
    title: job.job_title || job.job_name || String(refId),
    subtitle: `${job.city || ""} ${job.company_relation?.company_name || job.company_name || ""}`.trim(),
    payload: normalized
  };
}

/**
 * @param {Record<string, unknown> | null | undefined} company
 */
export function buildCompanyContextItem(company) {
  if (!company || typeof company !== "object") return null;
  const refId = company.credit_code;
  if (!refId) return null;
  return {
    kind: "company",
    refId: String(refId),
    title: company.company_name || String(refId),
    subtitle: company.industry || "",
    payload: company
  };
}
