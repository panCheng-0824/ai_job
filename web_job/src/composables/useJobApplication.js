/**
 * 岗位投递：一键投递、已投递态、默认简历解析。
 */
import { ref } from "vue";
import { getStudentId } from "../api/client";
import * as applicationApi from "../modules/applications/api";
import * as resumeApi from "../modules/resume/api";

const appliedJobIds = ref(new Set());

export function useJobApplication() {
  function markApplied(jobId) {
    const id = String(jobId || "").trim();
    if (!id) return;
    const next = new Set(appliedJobIds.value);
    next.add(id);
    appliedJobIds.value = next;
  }

  function isJobApplied(jobId) {
    const id = String(jobId || "").trim();
    return id ? appliedJobIds.value.has(id) : false;
  }

  async function loadAppliedJobIds(studentId) {
    const sid = String(studentId || getStudentId() || "").trim();
    if (!sid) {
      appliedJobIds.value = new Set();
      return [];
    }
    try {
      const data = await applicationApi.fetchMyApplications(sid);
      const ids = (data?.job_ids || []).map((x) => String(x));
      appliedJobIds.value = new Set(ids);
      return ids;
    } catch {
      appliedJobIds.value = new Set();
      return [];
    }
  }

  async function resolveDefaultResumeId(studentId) {
    const sid = String(studentId || getStudentId() || "").trim();
    if (!sid) return null;
    try {
      const store = await resumeApi.fetchResumeStore(sid);
      if (store?.defaultResumeId) return store.defaultResumeId;
      const list = store?.resumes || [];
      const seriesDefault = list.find((r) => r.isSeriesDefault);
      if (seriesDefault?.id) return seriesDefault.id;
      return list[0]?.id || null;
    } catch {
      return null;
    }
  }

  /**
   * 提交投递；返回 { ok, message, alreadyApplied }。
   */
  async function applyToJob(job, { studentId, source = "one_click" } = {}) {
    const sid = String(studentId || getStudentId() || "").trim();
    const jobId = String(job?.job_id || job?.id || "").trim();
    if (!sid) {
      return { ok: false, message: "请先登录后再投递", needLogin: true };
    }
    if (!jobId) {
      return { ok: false, message: "岗位信息无效" };
    }
    if (isJobApplied(jobId)) {
      return { ok: true, message: "该岗位已投递", alreadyApplied: true };
    }
    const resumeId = await resolveDefaultResumeId(sid);
    try {
      const data = await applicationApi.submitJobApplication({
        student_id: sid,
        job_id: jobId,
        resume_id: resumeId || undefined,
        source
      });
      markApplied(jobId);
      if (data?.already_applied) {
        return { ok: true, message: "该岗位已投递", alreadyApplied: true, data };
      }
      return { ok: true, message: "投递成功", alreadyApplied: false, data };
    } catch (e) {
      return { ok: false, message: e?.message || "投递失败" };
    }
  }

  return {
    appliedJobIds,
    isJobApplied,
    loadAppliedJobIds,
    markApplied,
    applyToJob,
    resolveDefaultResumeId
  };
}
