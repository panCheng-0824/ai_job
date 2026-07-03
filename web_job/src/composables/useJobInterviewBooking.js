/**
 * 岗位面试预约：预约面试、已预约态。
 */
import { ref } from "vue";
import { getStudentId } from "../api/client";
import * as bookingApi from "../modules/interview/bookingApi";

const bookedJobIds = ref(new Set());

export function useJobInterviewBooking() {
  function markBooked(jobId) {
    const id = String(jobId || "").trim();
    if (!id) return;
    const next = new Set(bookedJobIds.value);
    next.add(id);
    bookedJobIds.value = next;
  }

  function isJobBooked(jobId) {
    const id = String(jobId || "").trim();
    return id ? bookedJobIds.value.has(id) : false;
  }

  async function loadBookedJobIds(studentId) {
    const sid = String(studentId || getStudentId() || "").trim();
    if (!sid) {
      bookedJobIds.value = new Set();
      return [];
    }
    try {
      const data = await bookingApi.fetchMyInterviewBookings(sid);
      const ids = (data?.job_ids || []).map((x) => String(x));
      bookedJobIds.value = new Set(ids);
      return ids;
    } catch {
      bookedJobIds.value = new Set();
      return [];
    }
  }

  /**
   * 提交预约；返回 { ok, message, alreadyBooked }。
   */
  async function bookInterview(job, { studentId, source = "job_card" } = {}) {
    const sid = String(studentId || getStudentId() || "").trim();
    const jobId = String(job?.job_id || job?.id || "").trim();
    if (!sid) {
      return { ok: false, message: "请先登录后再预约", needLogin: true };
    }
    if (!jobId) {
      return { ok: false, message: "岗位信息无效" };
    }
    if (isJobBooked(jobId)) {
      return { ok: true, message: "该岗位已预约面试", alreadyBooked: true };
    }
    try {
      const data = await bookingApi.submitJobInterviewBooking({
        student_id: sid,
        job_id: jobId,
        source
      });
      markBooked(jobId);
      if (data?.already_booked) {
        return { ok: true, message: "该岗位已预约面试", alreadyBooked: true, data };
      }
      return { ok: true, message: "预约成功", alreadyBooked: false, data };
    } catch (e) {
      return { ok: false, message: e?.message || "预约失败" };
    }
  }

  return {
    bookedJobIds,
    isJobBooked,
    loadBookedJobIds,
    markBooked,
    bookInterview
  };
}
