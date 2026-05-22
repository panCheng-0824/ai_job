"""岗位推荐：在 GrepRAG / LightRAG 检索前，用大模型改写查询。

以用户「查询问题」为主线做意图拆分与浓缩；「学生画像」仅作参考，不与用户明确表述冲突。
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import List, Tuple

from model_cfg import ModelEntry, load_model_list
from openai import OpenAI

log = logging.getLogger(__name__)


def _select_chat_by_level(entries: List[ModelEntry], level: str) -> ModelEntry:
    """与 lc_agent.selection.select_model_by_type_and_level(chat, level) 同逻辑，避免导入 lc_agent 包触发 LangChain。"""
    if not entries:
        raise ValueError("entries must not be empty")
    normalized_type = "chat"
    normalized_level = (level or "").strip()
    for entry in entries:
        if str(entry.get("model_type", "chat")).strip().lower() == normalized_type and entry.get("model_level") == normalized_level:
            return entry
    for entry in entries:
        if str(entry.get("model_type", "chat")).strip().lower() == normalized_type:
            return entry
    for entry in entries:
        if entry.get("model_level") == normalized_level:
            return entry
    return entries[0]

_REWRITE_SYSTEM = (
    "你是高校就业「岗位文档检索」专用的查询改写模型。\n\n"
    "## 输入分工（必须遵守）\n"
    "1) **用户查询问题**：这是**唯一的主线**。你要**逐句读懂、拆分隐含条件**（例如：岗位类型/职级、城市或地域、"
    "行业或业务方向、必备技能与工具、实习/校招/社招、薪资或工作强度偏好、公司规模等），再浓缩成**适合关键词与向量混合检索**的短文本。\n"
    "2) **学生画像参考**：仅作**背景参考**。可用于补全用户**未明说但与画像一致**的信息（如专业对口技能、常见意向城市），"
    "但**不得替代、弱化或违背**用户在查询问题里已经写清楚的要求；画像与查询冲突时，**一律以查询问题为准**。\n\n"
    "## 输出要求\n"
    "- 只输出**一段**连续中文（建议 80～220 字，硬上限约 300 字），用于后续 RAG/检索；**不要**标题、编号、Markdown、引号包裹或任何解释性前后缀。\n"
    "- 优先保留**可检索实体**：标准技术名词、岗位名称、城市名、行业名、学历/届别等；口语可换成检索更稳的书面同义表达。\n"
    "- 若用户问题含多个子诉求，用顿号或短分句串联，**不要**展开成问答或列举「我将如何帮你」。"
)


def rewrite_job_query_sync(user_query: str, student_context: str = "") -> str:
    raw = (user_query or "").strip()
    if not raw:
        return ""
    if os.getenv("JOB_RAG_QUERY_REWRITE_DISABLED", "").strip().lower() in ("1", "true", "yes", "on"):
        return raw
    level = (os.getenv("JOB_RAG_QUERY_REWRITE_MODEL_LEVEL", "mid") or "mid").strip()
    try:
        entries = load_model_list()
        entry: ModelEntry = _select_chat_by_level(entries, level)
    except Exception as e:
        log.warning("岗位查询改写跳过（模型列表不可用）: %s", e)
        return raw

    parts = [
        "【用户查询问题】（请重点拆解、紧扣下列表述；冲突时以本节为准）\n" + raw,
    ]
    ctx = (student_context or "").strip()
    if ctx:
        parts.append("【学生画像参考】（仅作补充，不得覆盖上文明确条件）\n" + ctx)
    user_content = "\n\n".join(parts)

    try:
        client = OpenAI(api_key=entry["model_key"], base_url=entry["model_api"])
        resp = client.chat.completions.create(
            model=entry["model_name"],
            messages=[
                {"role": "system", "content": _REWRITE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=420,
        )
        out = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        log.warning("岗位查询改写调用失败，使用原文: %s", e)
        return raw

    if not out:
        return raw
    out = out.splitlines()[0].strip()
    out = out.strip(' "\'「」')
    if len(out) > 600:
        out = out[:600]
    return out or raw


async def rewrite_job_query_for_rag(user_query: str, student_context: str = "") -> Tuple[str, str]:
    """
    在线程池中执行同步 OpenAI 调用，避免阻塞事件循环。
    返回 (用于 RAG/搜索 的改写句, 用户原始 query)。
    """
    raw = (user_query or "").strip()
    if not raw:
        return "", ""
    try:
        rewritten = await asyncio.to_thread(rewrite_job_query_sync, raw, student_context)
        text = (rewritten or raw).strip()
        return (text or raw), raw
    except Exception as e:
        log.warning("岗位查询改写异步失败，使用原文: %s", e)
        return raw, raw
