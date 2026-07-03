/** Live2D 动作组中文名 */
export const MOTION_GROUP_LABELS = {
  Idle: "待机",
  TapBody: "身体互动",
  TapHead: "头部互动",
  mtn: "动作",
  special: "特殊"
};

/** 常见表情中文说明 */
export const EXPRESSION_LABELS = {
  F01: "默认",
  F02: "聆听",
  F03: "思考",
  F04: "表情 4",
  F05: "表情 5",
  F06: "表情 6",
  F07: "表情 7",
  F08: "表情 8",
  Normal: "普通",
  Smile: "微笑",
  Surprised: "惊讶",
  Sad: "难过",
  Angry: "生气",
  Blushing: "害羞",
  exp_01: "表情 1",
  exp_02: "表情 2",
  exp_03: "表情 3",
  exp_04: "表情 4",
  exp_05: "表情 5",
  exp_06: "表情 6",
  exp_07: "表情 7",
  exp_08: "表情 8"
};

/** 区域交互说明 */
export const HIT_AREA_HINTS = {
  Head: "随机切换表情",
  Body: "随机播放身体动作（含模型内置语音）"
};

function motionFileLabel(file, index) {
  const base = String(file || "")
    .split("/")
    .pop()
    ?.replace(/\.motion3\.json$/i, "");
  return base || `动作 ${index + 1}`;
}

function soundFileLabel(sound) {
  if (!sound) return "";
  return String(sound).split("/").pop() || sound;
}

/**
 * 从 model3.json 解析当前角色的表情 / 动作 / 交互区
 * @param {string} modelName
 */
export async function fetchLive2dModelCatalog(modelName) {
  const url = `/cubism/Resources/${encodeURIComponent(modelName)}/${encodeURIComponent(modelName)}.model3.json`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`无法加载 ${modelName} 模型配置`);
  const data = await res.json();
  const refs = data?.FileReferences || {};

  const expressions = (refs.Expressions || []).map((item) => ({
    id: item.Name,
    file: item.File,
    label: EXPRESSION_LABELS[item.Name] || item.Name
  }));

  const motions = [];
  const motionGroups = refs.Motions || {};
  for (const [group, items] of Object.entries(motionGroups)) {
    (items || []).forEach((item, index) => {
      motions.push({
        group,
        index,
        file: item.File,
        sound: item.Sound || "",
        soundLabel: soundFileLabel(item.Sound),
        groupLabel: MOTION_GROUP_LABELS[group] || group,
        label: motionFileLabel(item.File, index)
      });
    });
  }

  const hitAreas = (data.HitAreas || []).map((item) => ({
    name: item.Name,
    label: item.Name === "Head" ? "点击头部" : item.Name === "Body" ? "点击身体" : item.Name,
    hint: HIT_AREA_HINTS[item.Name] || "触发模型互动"
  }));

  return {
    modelName,
    expressions,
    motions,
    hitAreas,
    hasExpressions: expressions.length > 0,
    hasMotions: motions.length > 0,
    hasHitAreas: hitAreas.length > 0
  };
}
