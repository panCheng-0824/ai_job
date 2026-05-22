"""
管道角色执行层：基于 ``role_profiles.json`` 的四类 LLM 步骤（去噪、压缩、对抗、画像补充）。

分层说明：
- ``pipeline_llm``：单次 Chat + 可选 JSON Schema（与具体「去噪/压缩」文案无关）；
- **本模块**：把业务文本拼成 payload、调用 ``run_pipeline_llm``、失败回退策略（如空摘要则退回原始 memory）；
- ``user_session``：决定何时调用本模块各函数及如何将结果写入 ``invoke`` 参数。

管线顺序（由 ``user_session.run_user_query`` 固定）：去噪 → 压缩历史 → 主 Agent → 对抗 → 画像建议。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from pipeline_llm import format_structured_to_string, run_pipeline_llm as _run_pipeline_llm
from app.pipeline.payloads import (
    build_adversarial_payload,
    build_profile_enrichment_payload,
    memory_turns_to_plain,
)
from user_model import MemoryTurn, PipelineRoleProfile, UserModel

# ---------------------------------------------------------------------------
# 兼容说明：``demo.py`` 使用 ``patch("role_pipeline._run_pipeline_llm", ...)``
# 必须在模块命名空间保留 ``_run_pipeline_llm`` 这个名字。
# ---------------------------------------------------------------------------


def denoise_question(raw_question: str, profile: PipelineRoleProfile) -> str:
    """剔除口语噪声，保留核心语义；失败或空输出时退回原文。"""
    raw = (raw_question or "").strip()
    if not raw:
        return raw

    raw_out = _run_pipeline_llm(profile, raw, temperature=0.0)
    cleaned = format_structured_to_string(profile, raw_out)
    return cleaned if cleaned else raw


def compress_context_to_messages(
    memory: List[MemoryTurn],
    profile: PipelineRoleProfile,
) -> Tuple[List[BaseMessage], Optional[str]]:
    """
    将多轮上下文压缩为少量 LangChain 消息（默认一条 HumanMessage 承载摘要）。

    返回值：
    - ``messages``：传给 Agent 模板里 ``chat_history`` 占位符；
    - ``summary_text``：摘要正文，供画像补充等下游拼接；若压缩失败或未产出则可能为 None，
      此时若 ``memory`` 非空会退回「逐轮还原」消息列表且不附带摘要字符串。
    """
    if not memory:
        return [], None

    plain = memory_turns_to_plain(memory)
    raw_out = _run_pipeline_llm(profile, plain, temperature=0.0)
    summary_text = format_structured_to_string(profile, raw_out)

    if not summary_text:
        out: List[BaseMessage] = []
        for turn in memory:
            if turn["role"] == "user":
                out.append(HumanMessage(content=turn["content"]))
            else:
                out.append(AIMessage(content=turn["content"]))
        return out, None

    wrapped = (
        "【以下为经管道角色压缩的历史上下文摘要，已尝试去除闲聊与噪点】\n"
        f"{summary_text}"
    )
    return [HumanMessage(content=wrapped)], summary_text


def adversarial_review(
    agent_answer: str,
    denoised_question: str,
    profile: PipelineRoleProfile,
) -> str:
    """对已生成答案做对抗式审查（红队）；无答案时仍发起审查但内容中标注空答。"""
    payload = build_adversarial_payload(denoised_question, agent_answer)
    raw_out = _run_pipeline_llm(profile, payload, temperature=0.3)
    review = format_structured_to_string(profile, raw_out)
    return review if review else "（对抗审查未产生输出）"


def suggest_profile_enrichment(
    user: UserModel,
    *,
    denoised_question: str,
    agent_answer: str,
    context_summary: Optional[str],
    profile: PipelineRoleProfile,
    adversarial_review_text: Optional[str] = None,
) -> str:
    """
    根据本轮问答与历史摘要对用户画像给出补充建议（字符串；若启用 Schema 则为格式化 JSON 文本）。

    注意：**不**写回 ``usermodel.json``，仅返回建议文本供产品层决策是否落库。
    """
    payload = build_profile_enrichment_payload(
        user,
        denoised_question=denoised_question,
        agent_answer=agent_answer,
        context_summary=context_summary,
        adversarial_review_text=adversarial_review_text,
    )
    raw_out = _run_pipeline_llm(profile, payload, temperature=0.25)
    suggestion = format_structured_to_string(profile, raw_out)
    return suggestion if suggestion else "（画像补充角色未产生输出）"


def _invoke_role_text(profile: PipelineRoleProfile, user_payload: str, *, temperature: float = 0.0) -> str:
    """
    向后兼容：历史上部分测试曾 patch ``_invoke_role_text``；现统一走 ``_run_pipeline_llm`` 并格式化为字符串。

    新代码请直接调用 ``pipeline_llm.run_pipeline_llm`` + ``format_structured_to_string``。
    """
    raw = _run_pipeline_llm(profile, user_payload, temperature=temperature)
    return format_structured_to_string(profile, raw)
