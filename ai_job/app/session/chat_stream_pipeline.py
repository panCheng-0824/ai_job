"""
会话 SSE 流：按 **每条 user_model（通常以 usercode 标识）** 解析「这条角色要怎么处理流式对话」，
再映射到具体的 **handler**（实现分支），便于扩展。

- **业务语义**：一个场景 = 一个 user_model 条目需要的处理策略（参数 + 可选实现类型），
  写在 ``usermodel.json`` 该条的 ``stream_handler`` / ``stream_options``。
- **页面优先**：是否开启对抗（深度思考）仅由请求的 ``use_adversarial_harness`` 决定；
  ``use_role_pipeline``（纯净思考）亦以页面为准。
- **对抗轮次**：``adversarial_max_rounds`` / ``adversarial_max_rounds_cap`` 仅从本条 ``stream_options``
  读取（不经前端传参）；先取目标轮次再与 cap 取较小值，并最终限制在 1～10（与 harness 一致）。
- **实现语义**：``stream_handler`` 当前仅有常规 ``openai_direct``。``stream_options`` 还可配置 ``temperature``（缺省 0.0）。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from app.session.chat_service import stream_chat_service_tokens
from app.session.chat_stream_context import ChatStreamRunContext
from app.session.user_turn_context import append_user_turn_to_history

from app.session.role.role_001 import stream_chat_service_tokens as chat001
from app.session.role.role_002 import  stream_chat_service_tokens as chat002
from app.session.role.role_003 import  stream_chat_service_tokens as chat003
from app.session.role.role_004 import  stream_chat_service_tokens as chat004
from app.session.role.role_005 import  stream_chat_service_tokens as chat005
from app.session.role.role_006 import  stream_chat_service_tokens as chat006
from app.session.role.role_007 import  stream_chat_service_tokens as chat007
from app.skills.adversarial_harness import run_adversarial_harness

logger = logging.getLogger(__name__)

HANDLER_OPENAI_DIRECT = "openai_direct"
HANDLER_ADVERSARIAL_HARNESS = "adversarial_harness"

KNOWN_HANDLERS = frozenset({HANDLER_OPENAI_DIRECT, HANDLER_ADVERSARIAL_HARNESS})


def _stream_options_from_user_model(user_model: Dict[str, Any]) -> Dict[str, Any]:
    """仅来自 ``usermodel.json`` 当前条的 ``stream_options``。"""
    raw = user_model.get("stream_options") or {}
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def _coerce_adversarial_rounds_from_merged(merged: Dict[str, Any]) -> int:
    """``stream_options`` 中的对抗轮次：缺省 3，与 cap 取 min，再约束 1～10。"""
    raw = merged.get("adversarial_max_rounds")
    try:
        base = int(raw) if raw is not None else 3
    except (TypeError, ValueError):
        base = 3
    base = max(1, min(base, 10))
    cap = merged.get("adversarial_max_rounds_cap")
    if cap is not None:
        try:
            c = max(1, min(int(cap), 10))
            base = min(base, c)
        except (TypeError, ValueError):
            pass
    return base


def resolve_adversarial_max_rounds_from_user_model(user_model: Dict[str, Any]) -> int:
    """供非流式 harness 与管线共用：对抗最大轮次仅以 ``usermodel`` 的 ``stream_options`` 为准。"""
    return _coerce_adversarial_rounds_from_merged(_stream_options_from_user_model(user_model))


def resolve_stream_handler_and_options(
    user_model: Dict[str, Any],
    *,
    use_adversarial_harness: bool,
    use_role_pipeline: bool,
) -> Tuple[str, Dict[str, Any]]:
    """
    返回 (handler_id, runtime_fields)。

    是否对抗由 ``use_adversarial_harness``（页面）决定；``use_role_pipeline`` 来自页面。
    对抗轮次、温度来自 ``stream_options``。
    """
    if use_adversarial_harness:
        handler_id = HANDLER_ADVERSARIAL_HARNESS
        merged = _stream_options_from_user_model(user_model)
        return handler_id, _finalize_runtime_fields(
            merged,
            use_role_pipeline=use_role_pipeline,
        )

    usercode = str(user_model.get("usercode", "")).strip()
    explicit = str(user_model.get("stream_handler") or "").strip()

    if explicit == HANDLER_ADVERSARIAL_HARNESS:
        # 对抗实现只允许由请求开关触发，配置里误写则忽略。
        explicit = ""

    handler_id = explicit or HANDLER_OPENAI_DIRECT
    if handler_id not in KNOWN_HANDLERS:
        logger.warning(
            "usercode=%s 配置的 stream_handler=%s 未实现，回退到 %s",
            usercode,
            handler_id,
            HANDLER_OPENAI_DIRECT,
        )
        handler_id = HANDLER_OPENAI_DIRECT

    merged = _stream_options_from_user_model(user_model)
    return handler_id, _finalize_runtime_fields(
        merged,
        use_role_pipeline=use_role_pipeline,
    )


def _finalize_runtime_fields(
    merged: Dict[str, Any],
    *,
    use_role_pipeline: bool,
) -> Dict[str, Any]:
    try:
        temperature = float(merged.get("temperature", 0.0))
    except (TypeError, ValueError):
        temperature = 0.0

    return {
        "temperature": temperature,
        "adversarial_max_rounds": _coerce_adversarial_rounds_from_merged(merged),
        "use_role_pipeline": use_role_pipeline,
    }


def sse_chunk(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


def thinking_delta_from_piece(current: str, piece: str) -> str:
    """将可能为累计文本的 thinking 片段转为增量，减轻前端重复滚动。"""
    if not piece:
        return ""
    if not current:
        return piece
    if piece == current:
        return ""
    if piece.startswith(current):
        return piece[len(current) :]
    if current.startswith(piece):
        return ""

    max_overlap = min(len(current), len(piece))
    for overlap in range(max_overlap, 0, -1):
        if current.endswith(piece[:overlap]):
            return piece[overlap:]
    return piece


def _persist_user_turn(ctx: ChatStreamRunContext, now: str) -> None:
    display = (ctx.user_display_content or "").strip()
    if not display and not ctx.user_context_cards and not ctx.user_message_context:
        display = (ctx.text or "").strip()
    append_user_turn_to_history(
        ctx.history_turns,
        ts=now,
        display_content=display,
        message_context=ctx.user_message_context,
        context_cards=ctx.user_context_cards,
    )


def build_chat_stream_run_context(
    *,
    session_id: str,
    usercode: str,
    text: str,
    history_turns: List[Dict[str, Any]],
    user_model: Dict[str, Any],
    use_role_pipeline: bool,
    use_adversarial_harness: bool,
    adversarial_desc: str,
    model_level_fallback: str,
    system_prompt_extra: str,
    after_history_mutated: Optional[Callable[[], None]],
    register_stream_canceller: Callable[[str, Any], None],
    clear_stream_canceller_if_same: Callable[[str, Any], None],
    safe_cancel: Callable[[Any], None],
    user_display_content: str = "",
    user_message_context: str = "",
    user_context_cards: Optional[List[Dict[str, Any]]] = None,
) -> ChatStreamRunContext:
    handler_id, opts = resolve_stream_handler_and_options(
        user_model,
        use_adversarial_harness=use_adversarial_harness,
        use_role_pipeline=use_role_pipeline,
    )
    return ChatStreamRunContext(
        session_id=session_id,
        usercode=usercode,
        user_model=user_model,
        text=text,
        history_turns=history_turns,
        handler_id=handler_id,
        use_role_pipeline=bool(opts["use_role_pipeline"]),
        use_adversarial_harness=use_adversarial_harness,
        adversarial_max_rounds=int(opts["adversarial_max_rounds"]),
        adversarial_desc=adversarial_desc,
        model_level_fallback=model_level_fallback,
        system_prompt_extra=system_prompt_extra,
        temperature=float(opts["temperature"]),
        after_history_mutated=after_history_mutated,
        register_stream_canceller=register_stream_canceller,
        clear_stream_canceller_if_same=clear_stream_canceller_if_same,
        safe_cancel=safe_cancel,
        user_display_content=user_display_content,
        user_message_context=user_message_context,
        user_context_cards=list(user_context_cards or []),
    )


def _done_meta(ctx: ChatStreamRunContext) -> Dict[str, Any]:
    """done 事件里补充实现 handler、配置的对抗上限轮次，便于排查。"""
    return {
        "stream_handler": ctx.handler_id,
        "adversarial_max_rounds": ctx.adversarial_max_rounds,
    }

def iter_chat_stream_sse_by_model(ctx: ChatStreamRunContext) -> Iterator[str]:
    cancel_fn: Any = None
    yield sse_chunk("start", json.dumps({"session_id": ctx.session_id}, ensure_ascii=False))
    try:
        usercode = str(ctx.user_model.get("usercode", "")).strip()

        if usercode == "ROLE001":  # 岗位规划师（job_planner）
            stream_ctx = chat001(ctx )
        elif usercode == "ROLE002":#心理咨询师
            stream_ctx = chat002(ctx )
        elif usercode == "ROLE003":#贴心辅导员
            stream_ctx = chat003(ctx)
        elif usercode == "ROLE004":#简历优化师
            stream_ctx = chat004(ctx)
        elif usercode == "ROLE005":#日常助手
            stream_ctx = chat005(ctx)
        elif usercode == "ROLE006":#制度咨询师
            stream_ctx = chat006(ctx)
        else:#测试聊天机器人
            stream_ctx = chat007(ctx )
        # 3b 登记 cancel，便于客户端中止时打断上游请求。
        cancel_fn = stream_ctx.get("cancel")
        ctx.register_stream_canceller(ctx.session_id, cancel_fn)

        answer_parts: List[str] = []
        thinking_text = ""
        job_recommend_payload: Dict[str, Any] | None = None
        resume_render_payload: Dict[str, Any] | None = None
        # 3c 逐块转发：thinking → event thinking；正文 → event delta。
        for token in stream_ctx["token_iter"]:
            piece = token.get("content", "")
            if token.get("type") == "job_recommend":
                try:
                    job_recommend_payload = json.loads(piece or "{}")
                except json.JSONDecodeError:
                    job_recommend_payload = None
                if job_recommend_payload:
                    yield sse_chunk(
                        "job_recommend",
                        json.dumps(job_recommend_payload, ensure_ascii=False),
                    )
                continue
            if token.get("type") == "resume_render":
                try:
                    resume_render_payload = json.loads(piece or "{}")
                except json.JSONDecodeError:
                    resume_render_payload = None
                if resume_render_payload:
                    yield sse_chunk(
                        "resume_render",
                        json.dumps(resume_render_payload, ensure_ascii=False),
                    )
                continue
            if not piece:
                continue
            if token.get("type") == "thinking":
                delta_piece = thinking_delta_from_piece(thinking_text, piece)
                if not delta_piece:
                    continue
                thinking_text += delta_piece
                yield sse_chunk("thinking", json.dumps({"content": delta_piece}, ensure_ascii=False))
            else:
                answer_parts.append(piece)
                yield sse_chunk("delta", json.dumps({"content": piece}, ensure_ascii=False))

        answer = "".join(answer_parts).strip()
        thinking_text = thinking_text.strip()

        # 3d 将本轮问答写入内存中的 history，并可选持久化（如 chat_sessions）。
        now = datetime.utcnow().isoformat() + "Z"
        _persist_user_turn(ctx, now)
        assistant_turn: Dict[str, Any] = {"role": "assistant", "content": answer, "ts": now}
        if job_recommend_payload:
            assistant_turn["job_recommend"] = job_recommend_payload
        if resume_render_payload:
            assistant_turn["resume_render"] = resume_render_payload
        ctx.history_turns.append(assistant_turn)
        # 兜底：确保持久化前最后一轮助手带上结构化块（避免仅 SSE 有、history 缺字段）
        if ctx.history_turns:
            last = ctx.history_turns[-1]
            if last.get("role") == "assistant":
                if resume_render_payload and not last.get("resume_render"):
                    last["resume_render"] = resume_render_payload
                if job_recommend_payload and not last.get("job_recommend"):
                    last["job_recommend"] = job_recommend_payload
        if ctx.after_history_mutated:
            ctx.after_history_mutated()

        # 3e 收尾：done 中带完整 answer / thinking / history 及 handler 元数据。
        final_payload = {
            "session_id": ctx.session_id,
            "usercode": ctx.usercode,
            "model_level": stream_ctx.get("model_level", ctx.model_level_fallback),
            "use_role_pipeline": ctx.use_role_pipeline,
            "use_adversarial_harness": False,
            "thinking": thinking_text,
            "answer": answer,
            "history": ctx.history_turns,
            **_done_meta(ctx),
        }
        if job_recommend_payload:
            final_payload["job_recommend"] = job_recommend_payload
        if resume_render_payload:
            final_payload["resume_render"] = resume_render_payload
        yield sse_chunk("done", json.dumps(final_payload, ensure_ascii=False))
        return


    except GeneratorExit:
        ctx.safe_cancel(cancel_fn)
        raise
    except Exception as exc:
        yield sse_chunk("error", json.dumps({"detail": str(exc)}, ensure_ascii=False))
    finally:
        ctx.safe_cancel(cancel_fn)
        ctx.clear_stream_canceller_if_same(ctx.session_id, cancel_fn)
    return None




def iter_chat_stream_sse(ctx: ChatStreamRunContext) -> Iterator[str]:
    """按 ``ctx.handler_id`` 派发；SSE 事件格式与历史实现一致。"""
    # 步骤 0：底层流式请求的 cancel，供 stop 接口与清理使用。
    cancel_fn: Any = None

    # 步骤 1：通知客户端流已建立，便于绑定 session 与加载态。
    yield sse_chunk("start", json.dumps({"session_id": ctx.session_id}, ensure_ascii=False))

    try:
        # 步骤 2：对抗 harness（非 token 流）——一次算完后伪流式下发，详见 _sse_adversarial_harness。
        if ctx.handler_id == HANDLER_ADVERSARIAL_HARNESS:
            yield from _sse_adversarial_harness(ctx)
            return

        # 步骤 3：直连 OpenAI 兼容流式（真实增量 token）。
        if ctx.handler_id == HANDLER_OPENAI_DIRECT:
            # 3a 开启上游流式调用（内部可按 use_role_pipeline 做去噪/压缩等）。
            stream_ctx = stream_chat_service_tokens(
                usercode=ctx.usercode,
                message=ctx.text,
                history=ctx.history_turns,
                temperature=ctx.temperature,
                use_role_pipeline=ctx.use_role_pipeline,
                system_prompt_extra=ctx.system_prompt_extra or None,
            )
            # 3b 登记 cancel，便于客户端中止时打断上游请求。
            cancel_fn = stream_ctx.get("cancel")
            ctx.register_stream_canceller(ctx.session_id, cancel_fn)

            answer_parts: List[str] = []
            thinking_text = ""
            # 3c 逐块转发：thinking → event thinking；正文 → event delta。
            for token in stream_ctx["token_iter"]:
                piece = token.get("content", "")
                if not piece:
                    continue
                if token.get("type") == "thinking":
                    delta_piece = thinking_delta_from_piece(thinking_text, piece)
                    if not delta_piece:
                        continue
                    thinking_text += delta_piece
                    yield sse_chunk("thinking", json.dumps({"content": delta_piece}, ensure_ascii=False))
                else:
                    answer_parts.append(piece)
                    yield sse_chunk("delta", json.dumps({"content": piece}, ensure_ascii=False))

            answer = "".join(answer_parts).strip()
            thinking_text = thinking_text.strip()

            # 3d 将本轮问答写入内存中的 history，并可选持久化（如 chat_sessions）。
            now = datetime.utcnow().isoformat() + "Z"
            _persist_user_turn(ctx, now)
            ctx.history_turns.append({"role": "assistant", "content": answer, "ts": now})
            if ctx.after_history_mutated:
                ctx.after_history_mutated()

            # 3e 收尾：done 中带完整 answer / thinking / history 及 handler 元数据。
            final_payload = {
                "session_id": ctx.session_id,
                "usercode": ctx.usercode,
                "model_level": stream_ctx.get("model_level", ctx.model_level_fallback),
                "use_role_pipeline": ctx.use_role_pipeline,
                "use_adversarial_harness": False,
                "thinking": thinking_text,
                "answer": answer,
                "history": ctx.history_turns,
                **_done_meta(ctx),
            }
            yield sse_chunk("done", json.dumps(final_payload, ensure_ascii=False))
            return

        # 步骤 4：未注册的 handler，明确 error 事件。
        yield sse_chunk(
            "error",
            json.dumps({"detail": f"未实现的 stream_handler: {ctx.handler_id}"}, ensure_ascii=False),
        )
    except GeneratorExit:
        # 步骤 5a：消费端关闭生成器时取消上游。
        ctx.safe_cancel(cancel_fn)
        raise
    except Exception as exc:
        # 步骤 5b：异常转为 SSE error，避免裸异常打断传输。
        yield sse_chunk("error", json.dumps({"detail": str(exc)}, ensure_ascii=False))
    finally:
        # 步骤 6：无论成功失败，取消残留请求并清空 cancel 登记。
        ctx.safe_cancel(cancel_fn)
        ctx.clear_stream_canceller_if_same(ctx.session_id, cancel_fn)


def _sse_adversarial_harness(ctx: ChatStreamRunContext) -> Iterator[str]:
    """对抗分支：无 token 流，整体步骤在下方编号。"""
    # A1 跑完整 harness（多轮生产者/审查，上限见 ctx.adversarial_max_rounds）。
    harness_result = run_adversarial_harness(
        role_ref=ctx.usercode,
        adversary_desc=ctx.adversarial_desc,
        question=ctx.text,
        max_rounds=ctx.adversarial_max_rounds,
    )
    answer = str(harness_result.get("final_answer", "")).strip()
    # A2 用单次 delta 下发最终正文，前端可与直连流一样拼接展示。
    if answer:
        yield sse_chunk("delta", json.dumps({"content": answer}, ensure_ascii=False))

    # A3 写入 history 并可选持久化。
    now = datetime.utcnow().isoformat() + "Z"
    _persist_user_turn(ctx, now)
    ctx.history_turns.append({"role": "assistant", "content": answer, "ts": now})
    if ctx.after_history_mutated:
        ctx.after_history_mutated()

    # A4 done：附带对抗审查、轮次等元数据。
    final_payload = {
        "session_id": ctx.session_id,
        "usercode": ctx.usercode,
        "model_level": ctx.model_level_fallback,
        "use_role_pipeline": ctx.use_role_pipeline,
        "use_adversarial_harness": True,
        "thinking": "",
        "adversarial_review": str(harness_result.get("final_review", "")),
        "adversarial_rounds_used": int(harness_result.get("rounds_used", 0)),
        "adversarial_history": harness_result.get("history", []),
        "answer": answer,
        "history": ctx.history_turns,
        **_done_meta(ctx),
    }
    yield sse_chunk("done", json.dumps(final_payload, ensure_ascii=False))
