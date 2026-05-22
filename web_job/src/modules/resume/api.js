import { apiDelete, apiGet, apiPost, apiPut } from "../../api/client";

/**
 * 与 server_job StudentResumeController 对齐；返回体同 localStorage：{ defaultResumeId, resumes }。
 * @param {string} studentId
 */
export async function fetchResumeStore(studentId) {
  const sid = encodeURIComponent(String(studentId).trim());
  return apiGet(`/api/me/resumes?student_id=${sid}`);
}

/**
 * 按 id 拉取单条简历（含 content），用于编辑区回显。
 * @param {string} studentId
 * @param {string} resumeId
 */
export async function fetchResumeById(studentId, resumeId) {
  const sid = encodeURIComponent(String(studentId).trim());
  const rid = encodeURIComponent(resumeId);
  return apiGet(`/api/me/resumes/${rid}?student_id=${sid}`);
}

/**
 * @param {string} studentId
 * @param {string} resumeId
 * @param {{ templateId: string, displayName: string, content: object, seriesId?: string, createdAt?: number, updatedAt?: number, setSeriesDefault?: boolean, setGlobalDefault?: boolean }} payload
 */
export async function putResume(studentId, resumeId, payload) {
  const sid = encodeURIComponent(String(studentId).trim());
  const rid = encodeURIComponent(resumeId);
  return apiPut(`/api/me/resumes/${rid}?student_id=${sid}`, payload);
}

export async function deleteResumeOnServer(studentId, resumeId) {
  const sid = encodeURIComponent(String(studentId).trim());
  const rid = encodeURIComponent(resumeId);
  return apiDelete(`/api/me/resumes/${rid}?student_id=${sid}`);
}

/**
 * @param {string} studentId
 * @param {string} resumeId
 * @param {'series' | 'global'} [scope]
 */
export async function setDefaultResumeOnServer(studentId, resumeId, scope = "series") {
  const sid = encodeURIComponent(String(studentId).trim());
  const rid = encodeURIComponent(resumeId);
  const sc = encodeURIComponent(scope);
  return apiPost(`/api/me/resumes/${rid}/default?student_id=${sid}&scope=${sc}`, {});
}
