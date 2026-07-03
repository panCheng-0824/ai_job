export const MATCH_PRESETS = Object.freeze([
  {
    key: "balanced",
    label: "智能均衡",
    desc: "综合考量专业、技能、门槛、诉求与发展",
    icon: "⚖️",
    weights: { major: 20, skill: 20, threshold: 20, intent: 20, quality: 20 }
  },
  {
    key: "skill_first",
    label: "偏重技能",
    desc: "优先匹配专业能力与技术要求",
    icon: "🛠️",
    weights: { major: 25, skill: 35, threshold: 15, intent: 10, quality: 15 }
  },
  {
    key: "salary_first",
    label: "偏重薪资",
    desc: "优先匹配薪资待遇与城市诉求",
    icon: "💰",
    weights: { major: 15, skill: 15, threshold: 15, intent: 30, quality: 25 }
  },
  {
    key: "growth_first",
    label: "偏重发展",
    desc: "优先匹配企业前景与岗位成长空间",
    icon: "🚀",
    weights: { major: 15, skill: 15, threshold: 10, intent: 20, quality: 40 }
  }
]);