"""
ROLE004 — 图执行完成后的 thinking / resume_render / answer 分片输出。
"""

from __future__ import annotations

import json
from threading import Event
from typing import Iterator

from app.session.role.role004.state import ResumeOptimizeState
from app.session.role.role_util.stream_common import chunk_text


def iter_post_graph_tokens(
    *,
    final: ResumeOptimizeState,
    cancel_event: Event,
    role_label: str,
    intent: str,
) -> Iterator[dict[str, str]]:
    if cancel_event.is_set():
        yield {"type": "answer", "content": "（已中止）"}
        return

    resolved = (final.intent or intent or "resume_advise").strip()
    if resolved == "resume_generate":
        yield {
            "type": "thinking",
            "content": f"【{role_label}·简历生成】结构化简历已就绪，正在同步至简历页…\n",
        }
    else:
        yield {
            "type": "thinking",
            "content": f"【{role_label}·优化建议】建议文稿已生成，正在输出…\n",
        }

    resume_payload = final.resume_content if isinstance(final.resume_content, dict) else {}
    if resolved == "resume_generate" and resume_payload.get("sections"):
        yield {
            "type": "resume_render",
            "content": json.dumps(resume_payload, ensure_ascii=False),
        }

    answer = (final.final_answer or "").strip() or json.dumps(
        {"error": "empty_pipeline_output"},
        ensure_ascii=False,
    )
    for piece in chunk_text(answer):
        if cancel_event.is_set():
            break
        yield {"type": "answer", "content": piece}
