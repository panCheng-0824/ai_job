import { apiGet, apiPost } from "../../api/client";

/**
 * 我的投递列表（含岗位 enrich）。
 * @param {string} studentId
 */
export async function fetchMyApplications(studentId) {
  const sid = encodeURIComponent(String(studentId).trim());
  return apiGet(`/api/me/applications?student_id=${sid}`);
}

/**
 * 一键投递岗位。
 * @param {{ student_id: string, job_id: string, resume_id?: string, source?: string }} payload
 */
export async function submitJobApplication(payload) {
  return apiPost("/api/me/applications", {
    source: "one_click",
    ...payload
  });
}
