"""
ROLE004 对话意图：简历优化建议 vs 综合素材生成简历。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage

from app.session.role.role004.materials import materials_substantial
from app.session.role.role_util.intent_mode import resolve_stream_option_mode
from app.session.role.role_util.parsing import strip_markdown_json_fence

log = logging.getLogger(__name__)

Role004Intent = Literal["resume_advise", "resume_generate"]

_GENERATE_HINTS = (
    "生成简历",
    "生成一份",
    "帮我写简历",
    "写一份简历",
    "产出简历",
    "渲染简历",
    "根据素材",
    "根据以上素材",
    "综合素材",
    "填入简历",
    "更新简历页",
    "整份简历",
    "完整简历",
)

_ADVISE_HINTS = (
    "优化",
    "改一下",
    "怎么写",
    "润色",
    "修改建议",
    "原文",
    "改后",
    "这一段",
    "这段经历",
    "量化",
    "表达",
)

_INTENT_PROMPT = """你是简历优化师的「对话意图路由器」，只判断本轮更适合哪条处理通道。

【通道说明】
1. resume_advise（优化建议）
   - 用户提供了简历段落或经历描述，希望得到优化意见、原文 vs 改后对照、问题点与修改理由；
   - 典型：帮我优化这段项目经历、这段怎么写更好、请指出问题并给改后版本。

2. resume_generate（生成结构化简历）
   - 用户希望根据素材篮（OCR 简历、岗位、企业、补充说明等）生成或更新一整份可填入简历页的格式化内容；
   - 典型：根据以上素材生成简历、帮我写一份完整简历、把素材渲染到简历里。

【判别原则】
- 以用户当前轮原句为主；历史与素材摘录用于承接指代。
- 素材较丰富且用户明确要「生成/写一份/渲染」整份简历 → resume_generate。
- 仅优化局部、点评、对照改写 → resume_advise。
- 无法判断时 → resume_advise。

【输出格式】
只输出一个 JSON 对象：
{{"intent":"resume_advise或resume_generate","reason":"一句话理由"}}

【用户当前轮】
{user_query}

【近期对话摘录（可能为空）】
{history_block}

【简历素材摘录（可能为空）】
{materials_block}
"""


def resolve_resume_intent_mode(merged_user: dict) -> str:
    """
    ``stream_options.resume_intent_mode`` / ``resume_intent_mode``：
    ``advise`` | ``generate`` | ``auto``。
    """
    return resolve_stream_option_mode(
        merged_user,
        option_key="resume_intent_mode",
        allowed=("auto", "advise", "generate"),
        default="auto",
    )


def _normalize_text(*parts: str) -> str:
    return " ".join((p or "").strip() for p in parts if (p or "").strip()).lower()


def _count_hints(text: str, hints: tuple[str, ...]) -> int:
    return sum(1 for h in hints if h in text)


def _parse_intent_json(text: str) -> Role004Intent | None:
    raw = strip_markdown_json_fence(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    intent = str(data.get("intent") or "").strip().lower()
    if intent == "resume_generate":
        return "resume_generate"
    if intent == "resume_advise":
        return "resume_advise"
    return None


def _classify_by_rules(text: str, *, has_materials: bool) -> Role004Intent:
    if not text:
        return "resume_generate" if has_materials else "resume_advise"

    gen = _count_hints(text, _GENERATE_HINTS)
    adv = _count_hints(text, _ADVISE_HINTS)

    if gen > 0 and gen >= adv:
        return "resume_generate"
    if adv > 0 and adv > gen:
        return "resume_advise"

    if has_materials and re.search(r"(生成|写一|渲染|填入|完整)", text):
        return "resume_generate"

    return "resume_advise"


def _classify_by_llm(
    llm: Any,
    user_query: str,
    *,
    history_block: str = "",
    materials_block: str = "",
) -> Role004Intent | None:
    if llm is None:
        return None
    query = (user_query or "").strip()
    if not query and not (materials_block or "").strip():
        return "resume_advise"

    prompt = _INTENT_PROMPT.format(
        user_query=query or "（用户未输入可见文案，请结合素材判断）",
        history_block=(history_block or "").strip() or "（无）",
        materials_block=(materials_block or "").strip() or "（无）",
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = str(getattr(response, "content", "") or "")
        parsed = _parse_intent_json(content)
        if parsed is not None:
            log.info("ROLE004 意图 LLM 分类: intent=%s", parsed)
            return parsed
        log.warning("ROLE004 意图 LLM 输出无法解析: %s", content[:200])
    except Exception as exc:
        log.warning("ROLE004 意图 LLM 调用失败: %s", exc, exc_info=True)
    return None


def classify_role004_intent(
    user_query: str,
    *,
    history_block: str = "",
    materials_block: str = "",
    intent_mode: str = "auto",
    llm: Any = None,
) -> Role004Intent:
    """判断本轮走优化建议还是生成结构化简历。"""
    mode = (intent_mode or "auto").strip().lower()
    if mode == "generate":
        return "resume_generate"
    if mode == "advise":
        return "resume_advise"

    has_materials = materials_substantial(materials_block)
    text = _normalize_text(user_query, history_block, materials_block)

    if llm is not None:
        llm_result = _classify_by_llm(
            llm,
            user_query,
            history_block=history_block,
            materials_block=materials_block,
        )
        if llm_result is not None:
            return llm_result

    rules_result = _classify_by_rules(text, has_materials=has_materials)
    log.info("ROLE004 意图规则回退: intent=%s", rules_result)
    return rules_result
