"""
ROLE001 流式对话入口（SSE Token 流）。
"""

from __future__ import annotations

import json
from threading import Event
from typing import Any, Callable, Dict, Iterator

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role001.bindings import GraphBindings
from app.session.role.role001.config import (
    build_plan_execute_role_block,
    resolve_use_structured_return,
    tools_from_user_model,
)
from app.session.role.role001.graph import run_job_plan_execute_sync
from app.session.role.role001.intent import classify_role001_intent, resolve_intent_mode
from app.session.role.role_util.stream_common import (
    ChatTokenStreamContext,
    build_full_question,
    chunk_text,
    merge_stream_user,
    prepare_question_and_history,
    role_display_name,
)
from lc_agent import chat_model_from_entry
from lc_agent.selection import select_model_by_level
from model_cfg import load_model_list
from pipeline_llm import _max_retries, _request_timeout_seconds
from user_model import build_system_prompt_from_user


def build_graph_bindings(
    merged_user: Dict[str, Any],
    llm: Any,
    cancel_event: Event,
    *,
    history_block: str = "",
) -> GraphBindings:
    """根据合并后的用户模型构造图运行时绑定（含意图路由所需上下文）。"""
    role_block = build_plan_execute_role_block(merged_user)
    identity = {
        "username": merged_user.get("username", ""),
        "usercode": merged_user.get("usercode", ""),
        "output_format": merged_user.get("output_format", ""),
    }
    tools, tool_map = tools_from_user_model(merged_user)
    use_structured = resolve_use_structured_return(merged_user)
    return GraphBindings(
        llm=llm,
        cancel_event=cancel_event,
        role_block=role_block,
        identity=identity,
        tools=tools,
        tool_map=tool_map,
        use_structured_return=use_structured,
        history_block=history_block,
        intent_mode=resolve_intent_mode(merged_user),
    )


def stream_chat_service_tokens(ctx: ChatStreamRunContext) -> ChatTokenStreamContext:
    """
    ROLE001（岗位规划师）专用流式入口。

    入口先 ``classify_role001_intent``，再 invoke 含 ``intent_router`` 的图。
    """
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

        if cancel_event.is_set():
            yield {"type": "answer", "content": "（已中止）"}
            return

        resolved_intent = (final.intent or intent or "career_consult").strip()

        if resolved_intent == "job_recommend":
            yield {
                "type": "thinking",
                "content": f"【{role_label}·岗位推荐】检索与分析已完成，正在输出推荐列表…\n",
            }
        else:
            tail_phase = (
                f"【{role_label}·结构化小结】子步骤与观测已就绪，按 output_format 生成 JSON…\n"
                if bindings.use_structured_return
                else f"【{role_label}·对话小结】子步骤与观测已就绪，生成 Markdown 答复…\n"
            )
            yield {"type": "thinking", "content": tail_phase}
            for i, step in enumerate(final.plan, start=1):
                obs = final.observations[i - 1] if i - 1 < len(final.observations) else ""
                tail = (obs[:240] + "…") if len(obs) > 240 else obs
                yield {
                    "type": "thinking",
                    "content": f"  · 子步骤{i}: {step}\n    观测摘要: {tail}\n",
                }

        job_rec = final.job_recommend if isinstance(final.job_recommend, dict) else {}
        if job_rec.get("jobs") or job_rec.get("recommendation"):
            yield {
                "type": "job_recommend",
                "content": json.dumps(job_rec, ensure_ascii=False),
            }

        answer = (final.final_answer or "").strip() or json.dumps(
            {"error": "empty_pipeline_output"},
            ensure_ascii=False,
        )
        for piece in chunk_text(answer):
            if cancel_event.is_set():
                break
            yield {"type": "answer", "content": piece}

    return {
        "usercode": ctx.usercode,
        "model_level": model_level,
        "token_iter": iter_tokens(),
        "cancel": cancel,
    }
