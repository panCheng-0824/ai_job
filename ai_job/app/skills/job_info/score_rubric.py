"""岗位推荐评分维度：默认值、归一化与提示词格式化。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

DEFAULT_SCORE_DIMENSIONS: Dict[str, int] = {
    "major": 25,
    "skill": 25,
    "threshold": 20,
    "intent": 15,
    "quality": 15,
}

DIMENSION_ORDER: List[str] = ["major", "skill", "threshold", "intent", "quality"]

DIMENSION_LABELS: Dict[str, str] = {
    "major": "专业/方向对口",
    "skill": "技能与职责匹配",
    "threshold": "门槛匹配",
    "intent": "诉求匹配",
    "quality": "岗位质量",
}

DIMENSION_DESCRIPTIONS: Dict[str, str] = {
    "major": "岗位类别、职责与学生专业/检索诉求是否一致",
    "skill": "素材中的技能、软件、项目/职责要求与学生能力画像的吻合度",
    "threshold": "学历、届别、经验、证书等硬性条件是否满足或可争取",
    "intent": "城市、薪资区间、行业、校招/社招等是否符合用户检索意图",
    "quality": "企业规模、行业前景、岗位发展等（仅基于素材，勿臆测）",
}


def normalize_score_dimensions(raw: Any) -> Dict[str, int]:
    """解析请求体中的维度权重，缺省回退到 DEFAULT_SCORE_DIMENSIONS。"""
    defaults = dict(DEFAULT_SCORE_DIMENSIONS)
    src = raw if isinstance(raw, dict) else {}
    out: Dict[str, int] = {}
    for key in DIMENSION_ORDER:
        try:
            v = int(src.get(key, defaults[key]))
        except (TypeError, ValueError):
            v = defaults[key]
        out[key] = max(0, min(100, v))
    return out


def dimensions_total(dims: Mapping[str, int]) -> int:
    return sum(int(dims.get(k, 0)) for k in DIMENSION_ORDER)


def dimensions_scope_token(dims: Mapping[str, int]) -> str:
    return ",".join(f"{k}={int(dims.get(k, 0))}" for k in DIMENSION_ORDER)


def format_dimensions_for_prompt(dims: Mapping[str, int]) -> str:
    """生成 LLM 提示词中的【评分维度】段落。"""
    lines: List[str] = []
    for i, key in enumerate(DIMENSION_ORDER, 1):
        mx = int(dims.get(key, 0))
        label = DIMENSION_LABELS[key]
        desc = DIMENSION_DESCRIPTIONS[key]
        lines.append(f"{i}) {label}（0–{mx} 分）：{desc}；")
    total = dimensions_total(dims)
    lines.append(
        f"各维度得分之和应等于 score（满分 {total}）；"
        "须在【评分依据】中逐维写出「维度名 + 得分/满分 + 依据」。"
    )
    return "\n".join(lines)
