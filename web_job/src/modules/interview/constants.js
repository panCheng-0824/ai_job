/**
 * 面试模块状态与展示文案常量。
 */

/** 面试总结状态 */
export const SUMMARY_STATUS = {
  pending: { label: "未总结", tone: "warn" },
  summarized: { label: "已总结", tone: "ok" }
};

/** 单题答题状态 */
export const ANSWER_STATUS = {
  pending: { label: "未答题", tone: "muted" },
  answered: { label: "已答题", tone: "info" },
  summarized: { label: "已总结", tone: "ok" }
};

/** 大纲发布状态 */
export const PLAN_STATUS = {
  draft: { label: "草稿" },
  published: { label: "已发布" },
  archived: { label: "已归档" }
};

/** 会话状态 */
export const SESSION_STATUS = {
  planning: { label: "规划中", tone: "muted" },
  ready: { label: "待开始", tone: "info" },
  in_progress: { label: "进行中", tone: "info" },
  completed: { label: "已完成", tone: "ok" },
  abandoned: { label: "已放弃", tone: "muted" }
};
