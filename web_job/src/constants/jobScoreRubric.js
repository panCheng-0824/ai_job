/** 岗位推荐五维评分（与 ai_job score_rubric 一致） */
export const DEFAULT_SCORE_DIMENSIONS = Object.freeze({
  major: 25,
  skill: 25,
  threshold: 20,
  intent: 15,
  quality: 15
});

export const SCORE_DIMENSION_DEFS = Object.freeze([
  {
    key: "major",
    label: "专业/方向对口",
    desc: "岗位类别、职责与专业/检索诉求是否一致"
  },
  {
    key: "skill",
    label: "技能与职责匹配",
    desc: "技能、软件、项目要求与能力画像吻合度"
  },
  {
    key: "threshold",
    label: "门槛匹配",
    desc: "学历、届别、经验、证书等硬性条件"
  },
  {
    key: "intent",
    label: "诉求匹配",
    desc: "城市、薪资、行业、校招/社招等检索意图"
  },
  {
    key: "quality",
    label: "岗位质量",
    desc: "企业规模、行业前景、岗位发展（仅基于素材）"
  }
]);

export function cloneDefaultScoreDimensions() {
  return { ...DEFAULT_SCORE_DIMENSIONS };
}

export function clampDimensionScore(value, fallback) {
  const n = Number.parseInt(String(value), 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.min(100, n));
}

export function sumScoreDimensions(dims) {
  return SCORE_DIMENSION_DEFS.reduce((acc, d) => acc + (Number(dims?.[d.key]) || 0), 0);
}
