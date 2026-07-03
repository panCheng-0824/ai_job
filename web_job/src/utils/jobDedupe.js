import { normalizeJobId } from "./jobId";

function jobDedupeKey(job) {
  const id = normalizeJobId(job?.job_id || job?.id);
  if (id) return `id:${id.toLowerCase()}`;
  const title = String(job?.job_title || job?.job_name || "")
    .trim()
    .toLowerCase();
  const company = String(
    job?.company_name || job?.company_relation?.company_name || ""
  )
    .trim()
    .toLowerCase();
  if (title) return `title:${title}|${company}`;
  return "";
}

function jobRichness(job) {
  const score = Number(job?.score || 0);
  const reasons = job?.match_reasons;
  const reasonLen = Array.isArray(reasons) && reasons.length
    ? String(reasons[0] || "").length
    : String(job?.match_reason || "").length;
  const fieldCount = ["job_title", "job_name", "city", "salary_range_month", "company_name"].filter(
    (key) => String(job?.[key] || "").trim()
  ).length;
  return [score, reasonLen, fieldCount];
}

function isRicherJob(candidate, existing) {
  const left = jobRichness(candidate);
  const right = jobRichness(existing);
  for (let i = 0; i < left.length; i += 1) {
    if (left[i] !== right[i]) return left[i] > right[i];
  }
  return false;
}

/** 按 job_id（小写）去重；无 id 时按 title+company。保留分数更高、信息更全的一条。 */
export function dedupeJobs(jobs) {
  const list = Array.isArray(jobs) ? jobs : [];
  const byKey = new Map();
  const order = [];

  for (const job of list) {
    if (!job || typeof job !== "object") continue;
    const key = jobDedupeKey(job);
    if (!key) continue;
    const existing = byKey.get(key);
    if (!existing) {
      byKey.set(key, job);
      order.push(key);
      continue;
    }
    if (isRicherJob(job, existing)) {
      byKey.set(key, job);
    }
  }

  return order.map((key) => byKey.get(key)).filter(Boolean);
}

/** 智能匹配 API 响应：jobs 与 recommendation.recommended_jobs 同步去重。 */
export function normalizeMatchApiResponse(data) {
  if (!data || typeof data !== "object") return data;
  const jobs = dedupeJobs(data.jobs || []);
  const next = { ...data, jobs };

  const rec = data.recommendation;
  if (!rec || typeof rec !== "object") return next;

  const recommendation = { ...rec };
  if (recommendation.match_status === "matched" && jobs.length) {
    const rawRec = Array.isArray(recommendation.recommended_jobs)
      ? recommendation.recommended_jobs
      : [];
    const recById = new Map(
      dedupeJobs(rawRec).map((item) => [jobDedupeKey(item), item])
    );
    recommendation.recommended_jobs = jobs.map((job) => {
      const hit = recById.get(jobDedupeKey(job));
      if (hit) return hit;
      const reasons = (job.match_reasons || []).filter(Boolean);
      return {
        job_id: job.job_id,
        job_title: job.job_title,
        job_name: job.job_title,
        job_category: job.job_category,
        city: job.city,
        salary_range_month: job.salary_range_month,
        skills_required: job.skills_required || [],
        company_relation: job.company_relation || {},
        company_name: job.company_name,
        score: job.score,
        match_reason: reasons.join("；"),
        match_reasons: reasons,
        match_reason_sections: job.match_reason_sections || []
      };
    });
  } else if (Array.isArray(recommendation.recommended_jobs)) {
    recommendation.recommended_jobs = dedupeJobs(recommendation.recommended_jobs);
  }

  next.recommendation = recommendation;
  return next;
}
