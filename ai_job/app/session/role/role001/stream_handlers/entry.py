"""
ROLE001 — SSE 流式入口（意图分类 → LangGraph → 分片输出）。
"""

from __future__ import annotations

from threading import Event
from typing import Any, Dict, Iterator

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role001.bindings_factory import build_graph_bindings
from app.session.role.role001.graph import run_job_plan_execute_sync
from app.session.role.role001.intent import classify_role001_intent, resolve_intent_mode
from app.session.role.role001.stream_handlers.emit import iter_post_graph_tokens
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
from pipeline_llm import _max_retries, _request_timeout_seconds
from user_model import build_system_prompt_from_user


def stream_chat_service_tokens(ctx: ChatStreamRunContext) -> ChatTokenStreamContext:
    """ROLE001（岗位规划师）专用流式入口。"""
    merged_user = merge_stream_user(ctx)
    model_level = str(merged_user.get("model_level", "mid"))
    entry = select_model_by_level(load_model_list(), model_level)

    question, history_block = prepare_question_and_history(ctx, merged_user=merged_user)
    role_sys = build_system_prompt_from_user(merged_user)
    profile_extra = (ctx.system_prompt_extra or "").strip()
    if profile_extra:
        role_sys = f"{role_sys}\n\n{profile_extra}"

    full_question = build_full_question(
        role_sys=role_sys,
        history_block=history_block,
        question=question,
    )

    llm = chat_model_from_entry(
        entry,
        temperature=max(0.0, min(float(ctx.temperature), 1.0)),
        timeout=_request_timeout_seconds(),
        max_retries=_max_retries(),
    )

    cancel_event = Event()
    bindings = build_graph_bindings(
        merged_user, llm, cancel_event, history_block=history_block
    )
    role_label = role_display_name(merged_user, fallback="岗位规划师")
    intent_mode = resolve_intent_mode(merged_user)
    query_for_intent = (question or ctx.user_display_content).strip()
    intent = classify_role001_intent(
        query_for_intent,
        history_block=history_block,
        intent_mode=intent_mode,
        llm=llm,
    )

    def cancel() -> None:
        cancel_event.set()

    def iter_tokens() -> Iterator[Dict[str, str]]:
        if intent == "job_recommend":
            yield {
                "type": "thinking",
                "content": f"【{role_label}·岗位推荐】正在根据你的诉求与档案检索并生成推荐岗位…\n",
            }
        else:
            yield {
                "type": "thinking",
                "content": f"【{role_label}·职业咨询】正在规划本轮子步骤（对话式规划）…\n",
            }

        try:
            final = run_job_plan_execute_sync(
                full_question,
                bindings=bindings,
                user_query=question,
                student_context=profile_extra,
                intent=intent,
            )
        except Exception as exc:
            yield {"type": "answer", "content": f"岗位规划对话流水线异常：{exc}"}
            return

        yield from iter_post_graph_tokens(
            final=final,
            bindings=bindings,
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
