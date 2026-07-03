import { buildJobContextItem } from "../modules/resume/aiContext";
import { dispatchResumeAiContext } from "./useResumeAiContextBridge";
import { setResumeAiRailVisible } from "./useResumeAiRailVisible";
import { setResumeStudioRailVisible } from "./useResumeStudioRailVisible";

/**
 * 从岗位卡片「生成简历」：跳转我的简历，并将岗位放入 AI 优化素材篮。
 * @param {Record<string, unknown> | null | undefined} job
 * @param {import('vue-router').Router} router
 */
export function openResumeWithJobContext(job, router) {
  const item = buildJobContextItem(job);
  if (item) {
    dispatchResumeAiContext(item);
    setResumeStudioRailVisible(false);
    setResumeAiRailVisible(true);
  }
  const path = "/resume/create";
  if (router.currentRoute.value.path === path) return;
  router.push({
    path,
    state: item ? { resumeAiContext: item } : {}
  });
}
