import { apiGet, apiPost } from "../../api/client";

/**
 * 我的面试预约列表。
 * @param {string} studentId
 */
export async function fetchMyInterviewBookings(studentId) {
  const sid = encodeURIComponent(String(studentId).trim());
  return apiGet(`/api/me/interview-bookings?student_id=${sid}`);
}

/**
 * 预约岗位面试。
 * @param {{ student_id: string, job_id: string, source?: string }} payload
 */
export async function submitJobInterviewBooking(payload) {
  return apiPost("/api/me/interview-bookings", {
    source: "job_card",
    ...payload
  });
}
