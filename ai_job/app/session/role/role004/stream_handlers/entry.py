"""
ROLE004 — SSE 流式入口（意图分类 → LangGraph → 分片输出）。
"""

from __future__ import annotations

from threading import Event
from typing import Dict, Iterator

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role004.bindings_factory import build_graph_bindings
from app.session.role.role004.config import resolve_role004_llm_timeout_seconds
from app.session.role.role004.graph import run_resume_optimize_sync
from app.session.role.role004.intent import classify_role004_intent, resolve_resume_intent_mode
from app.session.role.role004.materials import build_materials_block
from app.session.role.role004.resume_templates import get_template, resolve_template_id
from app.session.role.role004.stream_handlers.emit import iter_post_graph_tokens
from app.session.role.role_util.stream_common import (
    ChatTokenStreamContext,
    build_full_question,
    merge_stream_user,
    prepare_question_and_history,
    role_display_name,
)
from lc_agent import chat_model_from_entry
from lc_agent.selection import select_model_by_level
from model_cfg import load_model_list
from pipeline_llm import _max_retries
from user_model import build_system_prompt_from_user


def stream_chat_service_tokens(ctx: ChatStreamRunContext) -> ChatTokenStreamContext:
    """
    ROLE004（简历优化师）专用流式入口。

    双通道：``resume_advise`` 段落建议；``resume_generate`` 整份简历 + ``resume_render`` 事件。
    """
    merged_user = merge_stream_user(ctx)
    model_level = str(merged_user.get("model_level", "mid"))
    entry = select_model_by_level(load_model_list(), model_level)

    question, history_block = prepare_question_and_history(ctx, merged_user=merged_user)
    materials_block = build_materials_block(
        message_context=ctx.user_message_context,
        context_cards=ctx.user_context_cards,
    )
    template_id = resolve_template_id(context_cards=ctx.user_context_cards)
    tpl = get_template(template_id)

    role_sys = build_system_prompt_from_user(merged_user)
    if not ctx.use_role_pipeline:
        history_block = ""
        profile_extra = ""
    else:
        profile_extra = (ctx.system_prompt_extra or "").strip()
        if profile_extra:
            role_sys = f"{role_sys}\n\n{profile_extra}"

    full_question = build_full_question(
        role_sys=role_sys,
        history_block=history_block,
        question=question,
        materials_block=materials_block,
    )

    llm = chat_model_from_entry(
        entry,
        temperature=max(0.0, min(float(ctx.temperature), 1.0)),
        timeout=resolve_role004_llm_timeout_seconds(merged_user),
        max_retries=_max_retries(),
    )

    cancel_event = Event()
    bindings = build_graph_bindings(
        merged_user, llm, cancel_event, history_block=history_block
    )
    role_label = role_display_name(merged_user, fallback="简历优化师")
    intent_mode = resolve_resume_intent_mode(merged_user)
    query_for_intent = (question or ctx.user_display_content).strip()
    intent = classify_role004_intent(
        query_for_intent,
        history_block=history_block,
        materials_block=materials_block,
        intent_mode=intent_mode,
        llm=llm,
    )

    def cancel() -> None:
        cancel_event.set()

    def iter_tokens() -> Iterator[Dict[str, str]]:
        if intent == "resume_generate":
            yield {
                "type": "thinking",
                "content": (
                    f"【{role_label}·简历生成】正在按模版「{tpl.name}」综合素材生成结构化简历…\n"
                ),
            }
        else:
            yield {
                "type": "thinking",
                "content": f"【{role_label}·优化建议】正在分析简历表述并生成可替换的修改方案…\n",
            }

        try:
            final = run_resume_optimize_sync(
                full_question,
                bindings=bindings,
                user_query=question,
                student_context=profile_extra,
                materials_block=materials_block,
                template_id=template_id,
                intent=intent,
            )
        except Exception as exc:
            yield {"type": "answer", "content": f"简历优化对话流水线异常：{exc}"}
            return

        yield from iter_post_graph_tokens(
            final=final,
            cancel_event=cancel_event,
            role_label=role_label,
            intent=intent,
        )

    return {
        "usercode": ctx.usercode,
        "model_level": model_level,
        "token_iter": iter_tokens(),
        "cancel": cancel,
    }
