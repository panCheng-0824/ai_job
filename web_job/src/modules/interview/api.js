/**
 * 面试模块 API — 与 server_job /api/interview 及 /api/me/interview-records 对齐。
 */
import {
  apiDelete,
  apiGet,
  apiGetFresh,
  apiPost,
  apiPut,
  getStudentId,
  invalidateCache
} from "../../api/client";

const INTERVIEW_RECORDS_PREFIX = "/api/me/interview-records";

function bumpInterviewRecordsCache() {
  invalidateCache(INTERVIEW_RECORDS_PREFIX);
}

function sidQuery(studentId) {
  const sid = encodeURIComponent(String(studentId || getStudentId() || "").trim());
  return `student_id=${sid}`;
}

/** 行业分类树/平铺；维护页 includeAll=true */
export async function fetchIndustryCategories({ forPurpose = "", tree = true, includeAll = false } = {}) {
  const q = new URLSearchParams();
  if (forPurpose) q.set("for", forPurpose);
  q.set("tree", tree ? "true" : "false");
  if (includeAll) q.set("include_all", "true");
  return apiGet(`/api/interview/industry/categories?${q}`);
}

/** 行业分类详情 */
export async function fetchIndustryCategoryDetail(categoryId) {
  return apiGet(`/api/interview/industry/categories/${encodeURIComponent(categoryId)}`);
}

/** 新增行业分类 */
export async function createIndustryCategory(payload) {
  return apiPost("/api/interview/industry/categories", payload);
}

/** 修改行业分类 */
export async function updateIndustryCategory(categoryId, payload) {
  return apiPut(`/api/interview/industry/categories/${encodeURIComponent(categoryId)}`, payload);
}

/** 删除行业分类 */
export async function deleteIndustryCategory(categoryId) {
  return apiDelete(`/api/interview/industry/categories/${encodeURIComponent(categoryId)}`);
}

/** 我的题目大纲列表 */
export async function fetchInterviewPlans(studentId, { status = "", industryCategoryId = "" } = {}) {
  const q = new URLSearchParams(sidQuery(studentId));
  if (status) q.set("status", status);
  if (industryCategoryId) q.set("industry_category_id", industryCategoryId);
  return apiGet(`/api/interview/plans?${q}`);
}

/** 大纲详情 */
export async function fetchInterviewPlanDetail(studentId, planId, version) {
  const q = new URLSearchParams(sidQuery(studentId));
  if (version != null) q.set("version", String(version));
  return apiGet(`/api/interview/plans/${encodeURIComponent(planId)}?${q}`);
}

/** 在二级行业下新建大纲 */
export async function createInterviewPlan(payload) {
  const q = sidQuery(payload?.student_id || getStudentId());
  return apiPost(`/api/interview/plans?${q}`, payload);
}

/** 编辑升版（version + 1） */
export async function reviseInterviewPlan(planId, payload) {
  const q = sidQuery(payload?.student_id || getStudentId());
  return apiPut(`/api/interview/plans/${encodeURIComponent(planId)}?${q}`, payload);
}

/** 删除大纲（全部版本） */
export async function deleteInterviewPlan(studentId, planId) {
  const q = sidQuery(studentId);
  return apiDelete(`/api/interview/plans/${encodeURIComponent(planId)}?${q}`);
}

/** 我的面试记录列表；fresh=true 时强制请求最新数据 */
export async function fetchInterviewRecords(studentId, { summaryStatus = "", fresh = false } = {}) {
  const q = new URLSearchParams(sidQuery(studentId));
  if (summaryStatus) q.set("summary_status", summaryStatus);
  const path = `/api/me/interview-records?${q}`;
  return fresh ? apiGetFresh(path) : apiGet(path);
}

/** 单条面试记录详情 */
export async function fetchInterviewRecordDetail(studentId, recordId) {
  const q = sidQuery(studentId);
  return apiGet(`/api/me/interview-records/${encodeURIComponent(recordId)}?${q}`);
}

/** 逐题答题列表 */
export async function fetchInterviewRecordAnswers(studentId, recordId) {
  const q = sidQuery(studentId);
  return apiGet(`/api/me/interview-records/${encodeURIComponent(recordId)}/answers?${q}`);
}

/** 删除单条面试记录（含关联会话与答题，不删大纲题库） */
export async function deleteInterviewRecord(studentId, recordId) {
  const q = sidQuery(studentId);
  const result = await apiDelete(`/api/me/interview-records/${encodeURIComponent(recordId)}?${q}`);
  bumpInterviewRecordsCache();
  return result;
}

/**
 * 聊天气泡：按 plan_id + chat_session_id 判断是否已有面试记录。
 */
export async function lookupInterviewRecordByPlanAndChat(studentId, planId, chatSessionId) {
  const sid = String(studentId || getStudentId() || "").trim();
  const pid = String(planId || "").trim();
  const cs = String(chatSessionId || "").trim();
  if (!sid || !pid || !cs) {
    return { exists: false, plan_id: pid, chat_session_id: cs };
  }
  const q = new URLSearchParams({
    student_id: sid,
    plan_id: pid,
    chat_session_id: cs
  });
  return apiGet(`/api/me/interview-records/lookup?${q}`);
}

/**
 * 学生确认大纲：按 plan_id 创建 interview_session 与 student_interview_records（大纲须已入库）。
 */
export async function startInterviewFromPlan({
  student_id,
  plan_id,
  plan_version,
  chat_session_id
} = {}) {
  const result = await apiPost("/api/interview/plan/start", {
    studentId: student_id || getStudentId(),
    planId: plan_id,
    planVersion: plan_version ?? null,
    chatSessionId: chat_session_id || ""
  });
  bumpInterviewRecordsCache();
  return result;
}
