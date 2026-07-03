import { invalidateCache } from "../api/client";
import { useJobInterviewBooking } from "./useJobInterviewBooking";

const INTERVIEW_BOOKINGS_PREFIX = "/api/me/interview-bookings";
const { bookInterview } = useJobInterviewBooking();

/**
 * 从岗位卡片「预约面试」：写入预约并跳转面试中心。
 * @param {Record<string, unknown> | null | undefined} job
 * @param {import('vue-router').Router} router
 * @param {{ studentId?: string }} [options]
 */
export async function openInterviewCenterWithJob(job, router, options = {}) {
  const result = await bookInterview(job, options);
  invalidateCache(INTERVIEW_BOOKINGS_PREFIX);
  const path = "/interview/center";
  if (router.currentRoute.value.path === path) {
    return result;
  }
  router.push({
    path,
    state: result.ok ? { interviewBookingJobId: String(job?.job_id || job?.id || "") } : {}
  });
  return result;
}
