"""
================================================================================
Day 9 —— 端到端 RAG：检索 → 组装上下文 → 生成答案（带引用）
================================================================================

写给 Java 转 Python 的同学：这一关你要学会什么？
--------------------------------------------
你在 Day6 已经完成了「多路检索（multi-query retrieval）」：
  - 用户问题 → LLM 拆子问题 → 多次向量检索 → 合并去重 → 得到命中 chunk 列表

Day9 的目标是补上真正的 “RAG = Retrieval-Augmented Generation” 的后半段：
  1) 把命中的 chunk 变成「可读上下文」（context）
  2) 再调用 LLM 生成最终答案
  3) 要求答案里带引用（让你知道答案依据来自哪些 chunk）

为什么要引用？
-------------
- 可解释：用户能看到信息来源
- 可回归：你改 prompt/检索后，引用命中变化可以衡量质量
- 可防幻觉：提示 LLM “只使用提供的上下文”，减少编造

运行方式
--------
在项目根目录执行：

    # 先确保你已经 ingest 过（Day6）
    python -m study01.day6 ingest --text "你的长文本" --reset

    # 再跑 Day9
    python -m study01.day9 "你的问题"

你也可以显式控制 top_k：
    python -m study01.day9 "你的问题" --top-k 6
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from study01.day6 import (
    CONTENT_FIELD,
    PK_FIELD,
    SOURCE_FIELD,
    Day6MilvusConfig,
    query_multi_subsearch,
)
from study01.llm import create_llm


@dataclass(frozen=True)
class RagAnswer:
    """
    Day9 的标准输出结构。

    为什么不用 dict？
    - dataclass 有字段提示，对新手更友好
    - 评测（Day8）时也更容易序列化/打印
    """

    question: str
    answer: str
    citations: List[Dict[str, Any]]
    sub_queries: List[str]


RAG_SYSTEM_PROMPT = """你是一个严谨的问答助手。你会得到：
1) 用户问题
2) 检索到的若干“上下文片段”（每段有 chunk_id 与 source）

规则（非常重要）：
- 只能使用上下文片段中提供的信息进行回答；如果上下文不足以回答，请明确说“资料不足”并指出缺少什么。
- 在回答中给出引用，引用格式必须严格为：[chunk_id]。
  例如：...因此结论是XXX。[a1b2c3]
- 若一句话综合了多个片段，请在句末写多个引用，如：[a1b2c3][d4e5f6]
- 不要编造不存在的 chunk_id。
"""


def _format_context(hits: List[Dict[str, Any]], *, max_chars_per_chunk: int = 900) -> str:
    """
    把 Day6 的命中列表格式化为 RAG 上下文。

    设计点（工程常识）：
    - LLM 上下文窗口有限，所以每个 chunk 做截断
    - 仍保留 chunk_id/source，便于引用与溯源
    """
    blocks: List[str] = []
    for h in hits:
        cid = str(h.get(PK_FIELD, "")).strip()
        src = str(h.get(SOURCE_FIELD, "")).strip()
        content = str(h.get(CONTENT_FIELD, "")).strip()
        if not cid or not content:
            continue
        if len(content) > max_chars_per_chunk:
            content = content[:max_chars_per_chunk] + "…"
        blocks.append(f"[{cid}] (source={src})\n{content}")
    return "\n\n".join(blocks)


def rag_answer(
    question: str,
    *,
    cfg: Optional[Day6MilvusConfig] = None,
    top_k_per_sub: int = 4,
    max_context_chunks: int = 8,
) -> RagAnswer:
    """
    端到端 RAG：
    - 检索（复用 Day6）
    - 组上下文
    - 生成答案（带引用）

    Args:
        question: 用户问题
        cfg: Milvus 配置（None 则用环境变量/默认）
        top_k_per_sub: 每个子问题召回条数（越大召回越多，但更慢、更占上下文）
        max_context_chunks: 最终用于生成的最大 chunk 数（控制上下文长度）
    """
    sub_queries, hits = query_multi_subsearch(
        question,
        cfg=cfg,
        top_k_per_sub=top_k_per_sub,
    )

    # 取最相关的前 N 个 chunk 用于生成（hits 已按 distance 排序）
    selected = hits[: max(0, int(max_context_chunks))]
    context = _format_context(selected)

    llm = create_llm()
    user_prompt = f"""用户问题：
{question}

上下文片段（可引用）：
{context if context else "（无上下文命中）"}
"""

    msg = llm.invoke(
        [
            SystemMessage(content=RAG_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
    )
    answer = (msg.content or "").strip()

    # citations：把“用于生成的 chunk 元信息”直接带回（便于 UI 展示/评测）
    citations: List[Dict[str, Any]] = []
    for h in selected:
        citations.append(
            {
                "chunk_id": h.get(PK_FIELD, ""),
                "source": h.get(SOURCE_FIELD, ""),
                "distance": h.get("distance"),
            }
        )

    return RagAnswer(
        question=question,
        answer=answer,
        citations=citations,
        sub_queries=sub_queries,
    )


def _print_result(r: RagAnswer) -> None:
    print("\n" + "=" * 70)
    print("【Day9 RAG 最终回答】")
    print("=" * 70)
    print("\n【问题】")
    print(r.question)
    print("\n【子问题（用于检索）】")
    for i, s in enumerate(r.sub_queries, 1):
        print(f"  {i}. {s}")
    print("\n【回答（带引用）】")
    print(r.answer)
    print("\n【引用元信息（用于生成的 chunks）】")
    print(json.dumps(r.citations, ensure_ascii=False, indent=2))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Day9：端到端 RAG（检索→生成→引用）")
    parser.add_argument("question", type=str, help="用户问题")
    parser.add_argument("--top-k", type=int, default=4, help="每个子问题召回条数")
    parser.add_argument("--max-context-chunks", type=int, default=8, help="用于生成的最大 chunk 数")
    args = parser.parse_args(list(argv) if argv is not None else None)

    r = rag_answer(
        args.question,
        top_k_per_sub=args.top_k,
        max_context_chunks=args.max_context_chunks,
    )
    _print_result(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

