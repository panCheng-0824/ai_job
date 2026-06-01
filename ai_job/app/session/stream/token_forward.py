"""
角色 Token 流 → SSE 事件转发（结构化事件与 delta/thinking 分离）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List, Optional, Tuple

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.stream.sse_format import sse_chunk, thinking_delta_from_piece

_STRUCTURED_SSE_TYPES = frozenset({
    "job_recommend",
    "resume_render",
    "interview_plan_preview",
    "interview_progress",
    "interview_turn",
})


def collect_forward_tokens(
    ctx: ChatStreamRunContext,
    token_iter: Iterator[Dict[str, str]],
) -> Tuple[Iterator[str], Dict[str, Any]]:
    """
    转发 token 并返回 ``(sse_iterator, aggregates)``。

    aggregates 含 answer_parts、thinking_text、job_recommend、resume_render。
    """
    answer_parts: List[str] = []
    thinking_text = ""
    job_recommend_payload: Optional[Dict[str, Any]] = None
    resume_render_payload: Optional[Dict[str, Any]] = None

    def gen() -> Iterator[str]:
        nonlocal thinking_text, job_recommend_payload, resume_render_payload
        for token in token_iter:
            piece = token.get("content", "")
            token_type = token.get("type", "")

            if token_type == "job_recommend":
                job_recommend_payload = _parse_json_payload(piece, job_recommend_payload)
                if job_recommend_payload:
                    yield sse_chunk(
                        "job_recommend",
                        json.dumps(job_recommend_payload, ensure_ascii=False),
                    )
                continue

            if token_type == "resume_render":
                resume_render_payload = _parse_json_payload(piece, resume_render_payload)
                if resume_render_payload:
                    yield sse_chunk(
                        "resume_render",
                        json.dumps(resume_render_payload, ensure_ascii=False),
                    )
                continue

            if token_type in _STRUCTURED_SSE_TYPES:
                if piece:
                    data = piece if piece.startswith("{") else json.dumps(
                        {"raw": piece}, ensure_ascii=False
                    )
                    yield sse_chunk(token_type, data)
                continue

            if not piece:
                continue

            if token_type == "thinking":
                delta_piece = thinking_delta_from_piece(thinking_text, piece)
                if delta_piece:
                    thinking_text += delta_piece
                    yield sse_chunk(
                        "thinking",
                        json.dumps({"content": delta_piece}, ensure_ascii=False),
                    )
            else:
                answer_parts.append(piece)
                yield sse_chunk("delta", json.dumps({"content": piece}, ensure_ascii=False))

    aggregates = {
        "answer_parts": answer_parts,
        "thinking_text": thinking_text,
        "job_recommend": job_recommend_payload,
        "resume_render": resume_render_payload,
    }
    return gen(), aggregates


def _parse_json_payload(
    piece: str,
    current: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(piece or "{}")
        return data if isinstance(data, dict) else current
    except json.JSONDecodeError:
        return current
