"""
ROLE001 — 图执行完成后的 thinking / job_recommend / answer 分片输出。
"""

from __future__ import annotations

import json
from threading import Event
from typing import Any, Dict, Iterator

from app.session.role.role001.state import JobPlanExecuteState
from app.session.role.role_util.bindings import GraphBindings
from app.session.role.role_util.stream_common import chunk_text


def iter_post_graph_tokens(
    *,
    final: JobPlanExecuteState,
    bindings: GraphBindings,
    cancel_event: Event,
    role_label: str,
    intent: str,
) -> Iterator[Dict[str, str]]:
    """图 invoke 结束后，按意图输出 thinking、结构化推荐与正文分片。"""
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
