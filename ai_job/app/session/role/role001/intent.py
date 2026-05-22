"""
ROLE001 对话意图分类：岗位推荐快车道 vs 职业咨询慢车道。

分类结果写入图状态 ``intent``，由 ``compile_plan_execute_graph`` 入口条件边路由。

``intent_mode=auto`` 时优先使用 LLM 判别；失败时回退到关键词规则，再默认职业咨询。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage

from app.session.role.role_util.intent_mode import resolve_stream_option_mode
from app.session.role.role_util.parsing import strip_markdown_json_fence

log = logging.getLogger(__name__)

Role001Intent = Literal["job_recommend", "career_consult"]

# 规则回退：明确「要岗位列表 / 匹配」
_RECOMMEND_HINTS = (
    "推荐岗位",
    "推荐几个",
    "帮我推荐",
    "给我推荐",
    "岗位推荐",
    "推荐一下",
    "有什么岗位",
    "哪些岗位",
    "什么岗位适合",
    "适合我的岗位",
    "适合我",
    "帮我匹配",
    "岗位匹配",
    "找工作",
    "找实习",
    "实习岗位",
    "校招岗位",
    "投递岗位",
    "招人",
    "招聘信息",
)

# 规则回退：明确「先聊规划 / 分析」
_CONSULT_HINTS = (
    "职业规划",
    "生涯规划",
    "转行",
    "要不要转",
    "该不该",
    "纠结",
    "怎么选",
    "如何选择",
    "职业路径",
    "发展路径",
    "聊规划",
    "分析一下",
    "适不适合",
    "有没有前途",
    "前景如何",
    "能力差距",
    "心态",
)

_INTENT_PROMPT = """你是岗位规划师的「对话意图路由器」，只判断本轮用户更适合哪条处理通道。

【通道说明】
1. job_recommend（岗位推荐快车道）
   - 用户希望尽快得到可投递/可参考的岗位列表、匹配结果或具体招聘推荐；
   - 典型：推荐岗位、有什么适合我的、帮我匹配实习、北京 Java 岗位有哪些。

2. career_consult（职业咨询慢车道）
   - 用户主要在谈职业规划、路径选择、转行纠结、能力差距、岗位分析、日常聊天、心态与策略等暂不需要立刻出岗位列表；
   - 典型：该不该考研、转行好不好、如何做生涯规划、行业前景分析、帮我分析一下。

【判别原则】
- 以「用户当前轮原句」为主；历史摘录仅用于承接指代（如「那再推荐几个北京的」）。
- 若同时含推荐与分析，但用户明显要岗位列表 → job_recommend。
- 仅寒暄、空泛问候、无法判断时 → career_consult。
- 无明确要求需要岗位推荐的统一任务是career_consult

【输出格式】
只输出一个 JSON 对象，不要 Markdown 围栏外的文字：
{{"intent":"job_recommend或career_consult","reason":"一句话理由"}}

【用户当前轮】
{user_query}

【近期对话摘录（可能为空）】
{history_block}
"""


def resolve_intent_mode(merged_user: dict) -> str:
    """
    从用户模型读取意图模式覆盖。

    ``stream_options.intent_mode`` 或顶层 ``intent_mode``：
    - ``recommend`` / ``consult`` / ``auto``（默认）。
    """
    return resolve_stream_option_mode(
        merged_user,
        option_key="intent_mode",
        allowed=("auto", "recommend", "consult"),
        default="auto",
    )


def _normalize_text(*parts: str) -> str:
    return " ".join((p or "").strip() for p in parts if (p or "").strip()).lower()


def _count_hints(text: str, hints: tuple[str, ...]) -> int:
    return sum(1 for h in hints if h in text)


def _parse_intent_json(text: str) -> Role001Intent | None:
    raw = strip_markdown_json_fence(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    intent = str(data.get("intent") or "").strip().lower()
    if intent == "job_recommend":
        return "job_recommend"
    if intent == "career_consult":
        return "career_consult"
    return None


def _classify_by_rules(text: str) -> Role001Intent:
    """关键词规则回退（LLM 不可用或解析失败时使用）。"""
    if not text:
        return "career_consult"

    rec = _count_hints(text, _RECOMMEND_HINTS)
    con = _count_hints(text, _CONSULT_HINTS)

    if rec > 0 and rec >= con:
        return "job_recommend"
    if con > 0 and con > rec:
        return "career_consult"

    if re.search(r"(推荐|匹配|招人)", text) and re.search(r"岗位|工作|实习|职位", text):
        return "job_recommend"

    return "career_consult"


def _classify_by_llm(
    llm: Any,
    user_query: str,
    *,
    history_block: str = "",
) -> Role001Intent | None:
    """调用 LLM 判别意图；失败返回 None。"""
    if llm is None:
        return None
    query = (user_query or "").strip()
    if not query:
        return "career_consult"

    prompt = _INTENT_PROMPT.format(
        user_query=query,
        history_block=(history_block or "").strip() or "（无）",
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = str(getattr(response, "content", "") or "")
        parsed = _parse_intent_json(content)
        if parsed is not None:
            log.info(
                "ROLE001 意图 LLM 分类: intent=%s, query_preview=%s",
                parsed,
                query[:80],
            )
            return parsed
        log.warning("ROLE001 意图 LLM 输出无法解析: %s", content[:200])
    except Exception as exc:
        log.warning("ROLE001 意图 LLM 调用失败: %s", exc, exc_info=True)
    return None


def classify_role001_intent(
    user_query: str,
    *,
    history_block: str = "",
    intent_mode: str = "auto",
    llm: Any = None,
) -> Role001Intent:
    """
    判断本轮应走「岗位推荐快车道」还是「职业咨询慢车道」。

    参数
    ----
    user_query:
        用户当前轮原句（推荐检索 query 同源）。
    history_block:
        近期对话摘录；用于承接续问。
    intent_mode:
        ``auto`` / ``recommend`` / ``consult``，见 ``resolve_intent_mode``。
    llm:
        LangChain Chat 模型；``auto`` 模式下用于意图判别。未提供时 ``auto`` 仅走规则回退。
    """
    mode = (intent_mode or "auto").strip().lower()
    if mode == "recommend":
        return "job_recommend"
    if mode == "consult":
        return "career_consult"

    text = _normalize_text(user_query, history_block)

    if llm is not None:
        llm_result = _classify_by_llm(llm, user_query, history_block=history_block)
        if llm_result is not None:
            return llm_result

    rules_result = _classify_by_rules(text)
    log.info(
        "ROLE001 意图规则回退: intent=%s, query_preview=%s",
        rules_result,
        (user_query or "")[:80],
    )
    return rules_result
