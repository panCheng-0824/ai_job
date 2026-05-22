"""
================================================================================
Day 6 —— 大模型 + 向量库：清洗入库 & 子问题多路检索 Demo（学习型注释版）
================================================================================

写给初学者：本文件在讲什么？
----------------------------
你可以把整条链路想成「图书馆」：

1. **写入（ingest）**：别人交来一叠草稿（原始文本）→ 你先请「编辑」（大模型）删掉废话、理顺句子
   → 再切成一页一页（chunk）→ 每页做成「指纹」（embedding 向量）→ 指纹放进 **Milvus 向量库**。

2. **查询（query）**：读者问一个问题 → 再请大模型把大问题拆成几个小问题（多路子问题）
   → 每个小问题也做成指纹 → 去库里找最像的几页 → 合并结果。

这和 **Agent** 的关系
---------------------
严格说，本 Demo **没有**用到「会自己循环调工具」的 Agent（那是 Day1~4 的路线）。
但用到的 **大模型 + 明确步骤的流水线**，和 Agent 里「模型理解意图 → 再交给下游模块」是同一类思路：
这里下游是 **嵌入模型** 和 **Milvus**，而不是 search/calculate 等 Tool。

前置条件（与 Day5 一致）
------------------------
- Milvus（Docker 等）监听默认 ``127.0.0.1:19530``。
- Ollama：``ollama serve``，聊天模型（与 ``study01/llm.py`` 默认一致，如 qwen3:8b），
  嵌入模型 ``ollama pull nomic-embed-text``。

环境变量（可选）
----------------
- ``MILVUS_COLLECTION_DAY6``：集合名，默认 ``study01_day6_rag``。
- 其余 ``MILVUS_HOST`` / ``MILVUS_PORT`` / ``OLLAMA_*`` 与 Day5 相同。

运行示例
--------
    python -m study01.day6 ingest --text "（一段带噪音的笔记……）"
    python -m study01.day6 ingest --file ./notes.txt
    python -m study01.day6 query "这个问题涉及哪几方面？"

建议阅读顺序（学习路径）
------------------------
1. 先看「常量与配置」→ 知道数据长什么样。
2. 再看「Milvus 表结构」→ 知道向量存在哪些列里。
3. 看 ``chunk_text`` → 理解为什么要切块。
4. 看 ``llm_clean_for_index`` / ``llm_split_sub_queries`` → 理解怎么跟大模型对话。
5. 最后看 ``ingest_text_pipeline`` 和 ``query_multi_subsearch`` → 把整条链串起来。
"""

# -----------------------------------------------------------------------------
# 「from __future__ import annotations」是做什么的？
# -----------------------------------------------------------------------------
# Python 3.7+ 可用：让类型标注里的名字（如 Day6MilvusConfig）可以先使用后定义，
# 解析器会把标注当成「字符串」延迟处理。初学可略过细节，知道「写在大文件里更方便」即可。
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# LangChain：用大模型时，通常把「系统人设」和「用户说的话」分成两类 Message。
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# PyMilvus：这里只保留 utility（是否存在集合等），具体 CRUD 细节已下沉到独立模块。
from pymilvus import utility

# 嵌入配置类型仍复用 Day5（OllamaEmbeddings 等细节在存储层模块里做）
from study01.day5 import OllamaEmbedConfig
from study01.llm import create_llm

# 向量库（Milvus）相关：已抽到独立模块，Day6 只负责编排调用
from study01.milvus_day6_store import (
    CONTENT_FIELD,
    PK_FIELD,
    SOURCE_FIELD,
    Day6MilvusConfig,
    ingest_chunks_to_milvus,
    query_chunks_from_milvus,
)

# 知识图谱（Neo4j）相关：独立模块；若未配置环境变量则自动降级为“不启用”
from study01.neo4j_kg_store import Neo4jConfig, search_chunks_fulltext, upsert_chunks

# =============================================================================
# 一、存储层已拆分（重要）
# =============================================================================
#
# 你现在的 Day6 是“编排层”：
# - 文本清洗/分块/子问题拆分：仍在本文件
# - Milvus（向量库）细节：`study01/milvus_day6_store.py`
# - Neo4j（知识图谱）细节：`study01/neo4j_kg_store.py`
#
# 注意：
# - 字段常量 `PK_FIELD` / `CONTENT_FIELD` / `SOURCE_FIELD` 现在来自 `milvus_day6_store.py`
# - 你不需要在 Day6 重复定义它们（避免两份定义不一致）


# =============================================================================
# 二、配置类：dataclass 是什么？
# =============================================================================
# @dataclass 会自动生成 __init__ 等方法，让你用「数据容器」少写样板代码。
# frozen=True 表示创建后不能改字段（像元组一样不可变），避免不小心改坏配置。


"""
Milvus/Neo4j 的配置与 CRUD 细节已移动到：
- `study01/milvus_day6_store.py`
- `study01/neo4j_kg_store.py`

Day6 不再重复定义 `Day6MilvusConfig`、建表、insert/search 等函数，避免两套实现不一致。
"""


# =============================================================================
# 三、文本处理：读文件与分块（chunk）
# =============================================================================
# 嵌入模型一次能处理的文字长度有限，且太长时语义会被「平均」掉。
# 所以实践中常把长文切成多段，每段单独向量化 —— 这叫 chunking。


def read_uploaded_text(path: Path) -> str:
    """
    从磁盘读入文本。

    Path：pathlib 里的路径对象，比字符串路径更好用（拼接用 / 运算符）。
    errors="replace"：遇到非法 UTF-8 字节时用替换字符，避免整个程序崩溃。
    """
    return path.read_text(encoding="utf-8", errors="replace")


def chunk_text(text: str, max_chars: int = 800, overlap: int = 120) -> List[str]:
    """
    简单滑动窗口分块。

    Args:
        text: 清洗后的正文。
        max_chars: 每块最大字符数（演示用固定值，真实项目可按 token 数切）。
        overlap: 相邻块重叠字符数，减少「关键句刚好被切成两半」的情况。

    算法简述：
    - 从头开始取 [start, end) 子串；下一块从 end - overlap 开始，形成重叠。
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


# =============================================================================
# 四、大模型：提示词（Prompt）与 invoke
# =============================================================================
# LangChain 里常见模式：
# - SystemMessage：告诉模型「你是谁、遵守什么规则」。
# - HumanMessage：用户的具体输入。
# - llm.invoke([...])：发一次请求，拿到模型的回复消息对象，用 .content 取字符串。

CLEAN_SYSTEM = """你是文本预处理助手。任务：
1) 理解用户给出的原始内容，去掉明显噪音：重复无意义的符号、乱码片段、与正文无关的页眉页脚广告等。
2) 保留可检索的事实与表述，语言通顺即可，不要添加原文没有的重要信息。
3) 只输出清洗后的正文，不要任何解释或前后缀。"""

SUBQ_SYSTEM = """你是检索助手。用户会提出一个问题，你需要将其拆成 2～4 个**互补**的子问题，
用于在向量库中分别检索（多路召回）。要求：
- 每个子问题简短、可独立作为检索查询；
- 覆盖原问题的不同侧面（实体、时间、原因、步骤等）；
- 必须用 JSON 输出，格式严格为：{"sub_queries": ["子问题1", "子问题2", ...]}
不要输出 markdown 代码块，不要其它字段。"""


def llm_clean_for_index(llm: ChatOpenAI, raw_text: str) -> str:
    """
    调用大模型做「去噪 + 语义整理」，便于后续向量化。

    学习要点：
    - 这是**单次调用**，没有工具、没有循环；适合明确的一步预处理。
    - 若 Ollama 没开或模型名不对，这里会抛错；可先 `skip_llm_clean` 调试嵌入与 Milvus。
    """
    msg = llm.invoke(
        [
            SystemMessage(content=CLEAN_SYSTEM),
            HumanMessage(content=f"原始内容：\n\n{raw_text}"),
        ]
    )
    return (msg.content or "").strip()


def llm_split_sub_queries(llm: ChatOpenAI, user_question: str) -> List[str]:
    """
    让大模型把用户问题拆成多个子问题，用于多路检索（multi-query retrieval）。

    解析逻辑说明（写给新人）：
    1. 模型应返回 JSON；但真实世界里模型偶尔会包 ```json ... ```，所以用正则剥掉。
    2. json.loads 失败：退化为「只用一个原问题」，保证程序不崩。
    3. 结构不对或列表为空：同样退回单问题。

    这就是典型的「尽量结构化输出 + 失败兜底」，工程里很常见。
    """
    msg = llm.invoke(
        [
            SystemMessage(content=SUBQ_SYSTEM),
            HumanMessage(content=user_question),
        ]
    )
    text = (msg.content or "").strip()
    # 兼容模型偶尔包一层 markdown 代码围栏
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [user_question]
    subs = data.get("sub_queries") if isinstance(data, dict) else None
    if not isinstance(subs, list):
        return [user_question]
    out = [str(s).strip() for s in subs if str(s).strip()]
    return out if out else [user_question]


# =============================================================================
# 五、对外主流程：入库与查询
# =============================================================================


def ingest_text_pipeline(
    raw_text: str,
    *,
    source_label: str,
    cfg: Optional[Day6MilvusConfig] = None,
    ecfg: Optional[OllamaEmbedConfig] = None,
    reset_collection: bool = False,
    skip_llm_clean: bool = False,
    enable_neo4j: bool = True,
) -> Tuple[Day6MilvusConfig, int]:
    """
    完整写入流水线：清洗（可选）→ 分块 → 嵌入 → 写入 Milvus。

    参数里的星号 * 是什么意思？
    - `*,` 后面的参数**必须用关键字**传入，例如 source_label="xxx"。
    - 避免以后加参数时，调用方把 bool 顺序传错。

    Args:
        raw_text: 用户或文件读入的原始字符串。
        source_label: 记录在 SOURCE_FIELD，方便知道数据出处。
        cfg / ecfg: 可传入自定义配置；默认 None 时用环境变量与 Day5 默认嵌入配置。
        reset_collection: True 时先删集合再建，学习阶段「清空重来」很有用。
        skip_llm_clean: True 时跳过 LLM，直接对原文分块（排查 Milvus/嵌入问题时用）。

    Returns:
        (最终生效的 cfg, 写入的 chunk 条数)

    关于 replace(cfg, vector_dim=...)：
    - dataclasses.replace 会在**拷贝** cfg 的同时改某一个字段。
    - 因为 frozen=True 不能直接 cfg.vector_dim = ...，所以用 replace。
    """
    llm = create_llm()
    cleaned = raw_text.strip() if skip_llm_clean else llm_clean_for_index(llm, raw_text)
    chunks = chunk_text(cleaned)
    if not chunks:
        return cfg or Day6MilvusConfig(), 0

    # A) 写入 Milvus（向量库）
    cfg, n = ingest_chunks_to_milvus(
        chunks,
        source_label=source_label,
        cfg=cfg,
        ecfg=ecfg,
        reset_collection=reset_collection,
    )

    # B) 可选：写入 Neo4j（知识图谱“证据层”）
    # - 若你没有配置 NEO4J_URI/NEO4J_PASSWORD，本步骤会自动变成 no-op
    if enable_neo4j:
        neo_cfg = Neo4jConfig()
        rows = [
            {
                "chunk_id": f"{source_label}:{i}",
                "content": c,
                "source": source_label,
            }
            for i, c in enumerate(chunks)
        ]
        upsert_chunks(rows, cfg=neo_cfg)

    return cfg, n


def query_multi_subsearch(
    question: str,
    cfg: Optional[Day6MilvusConfig] = None,
    ecfg: Optional[OllamaEmbedConfig] = None,
    top_k_per_sub: int = 4,
    enable_neo4j: bool = True,
    neo4j_top_k: int = 5,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    查询流水线：子问题拆分 → 多次向量检索 → 按 chunk_id 合并去重。

    合并规则（学习用）：
    - 同一个 chunk 可能被多个子问题检索到；我们只保留「distance 最小」的那条，
      表示在当前度量下它是最像的命中之一。
    - 最后用 sorted(..., key=距离) 把去重后的结果按相似度排序打印。

    Returns:
        (子问题列表, 命中字典列表；字典里含 chunk_id、content、source、distance、matched_sub_query)
    """
    llm = create_llm()
    sub_queries = llm_split_sub_queries(llm, question)

    # A) Milvus：多子问题语义检索
    milvus_hits = query_chunks_from_milvus(
        question,
        sub_queries=sub_queries,
        cfg=cfg,
        ecfg=ecfg,
        top_k_per_sub=top_k_per_sub,
    )

    # B) Neo4j：学习版 KG-RAG 召回（全文索引）
    neo_hits: List[Dict[str, Any]] = []
    if enable_neo4j:
        neo_hits = search_chunks_fulltext(question, cfg=Neo4jConfig(), top_k=neo4j_top_k)

    # C) 合并：两套检索的 chunk_id 不一定一致，所以先按 content 做去重再排序
    def _content_key(h: Dict[str, Any]) -> str:
        return (h.get(CONTENT_FIELD, "") or "").strip()[:300]

    merged: Dict[str, Dict[str, Any]] = {}
    for h in neo_hits + milvus_hits:
        k = _content_key(h)
        if not k:
            continue
        if k not in merged:
            merged[k] = h
            continue
        # 同一 content 的命中：把 backend/source 补全，保留更“信息丰富”的那条
        if merged[k].get("backend") != h.get("backend"):
            merged[k]["backend"] = f"{merged[k].get('backend')},{h.get('backend')}"
        if not merged[k].get(SOURCE_FIELD) and h.get(SOURCE_FIELD):
            merged[k][SOURCE_FIELD] = h.get(SOURCE_FIELD)

    def _rank(h: Dict[str, Any]) -> float:
        # Milvus 有 distance（越小越相似）；Neo4j 只有 score（这里先简单放后面）
        d = h.get("distance")
        return float(d) if d is not None else 1e9

    hits_out = sorted(merged.values(), key=_rank)
    return sub_queries, hits_out


def _print_hits(sub_queries: List[str], hits: List[Dict[str, Any]]) -> None:
    """命令行友好输出；逻辑简单，初学可看 f-string 与 enumerate 的用法。"""
    print("\n【子问题】")
    for i, s in enumerate(sub_queries, 1):
        print(f"  {i}. {s}")
    print("\n【检索命中】（已按向量距离去重合并）")
    if not hits:
        print("  （无）")
        return
    for j, h in enumerate(hits, 1):
        print(f"\n--- #{j} distance={h['distance']:.4f} sub={h.get('matched_sub_query', '')!r} ---")
        print(f"  id={h[PK_FIELD]} source={h.get(SOURCE_FIELD, '')}")
        body = h.get(CONTENT_FIELD, "") or ""
        preview = body[:500] + ("…" if len(body) > 500 else "")
        print(f"  {preview}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    命令行入口。

    argparse 要点：
    - subparsers：子命令，如 git commit 里的 commit。
    - add_argument(..., action="store_true")：出现该 flag 即为 True（布尔开关）。
    - main 返回整数退出码：0 表示成功，非 0 表示错误（shell / CI 可判断）。
    """
    parser = argparse.ArgumentParser(description="Day6：LLM 清洗入库 + 子问题多路检索")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="写入文本或文件")
    p_ingest.add_argument("--text", type=str, default=None, help="直接传入文本")
    p_ingest.add_argument("--file", type=str, default=None, help="上传文件路径")
    p_ingest.add_argument("--source", type=str, default="cli", help="来源标签（展示用）")
    p_ingest.add_argument("--reset", action="store_true", help="删除并重建集合")
    p_ingest.add_argument("--no-llm-clean", action="store_true", help="跳过 LLM 清洗（调试用）")
    p_ingest.add_argument("--no-neo4j", action="store_true", help="不写入 Neo4j（只写 Milvus）")

    p_query = sub.add_parser("query", help="多子问题检索")
    p_query.add_argument("question", type=str, help="用户问题")
    p_query.add_argument("--top-k", type=int, default=4, help="每个子问题返回条数")
    p_query.add_argument("--no-neo4j", action="store_true", help="不使用 Neo4j 召回（只用 Milvus）")
    p_query.add_argument("--neo4j-top-k", type=int, default=5, help="Neo4j 全文索引召回条数")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.cmd == "ingest":
        if args.text and args.file:
            print("请只指定 --text 或 --file 之一", file=sys.stderr)
            return 2
        if args.text:
            raw = args.text
            src = args.source
        elif args.file:
            path = Path(args.file)
            if not path.is_file():
                print(f"文件不存在: {path}", file=sys.stderr)
                return 2
            raw = read_uploaded_text(path)
            src = args.source or path.name
        else:
            print("需要 --text 或 --file", file=sys.stderr)
            return 2
        cfg, n = ingest_text_pipeline(
            raw,
            source_label=src,
            reset_collection=args.reset,
            skip_llm_clean=args.no_llm_clean,
            enable_neo4j=not args.no_neo4j,
        )
        print(f"完成：集合={cfg.collection_name}，写入 chunk 数={n}，向量维度={cfg.vector_dim}")
        return 0

    if args.cmd == "query":
        subs, hits = query_multi_subsearch(
            args.question,
            top_k_per_sub=args.top_k,
            enable_neo4j=not args.no_neo4j,
            neo4j_top_k=args.neo4j_top_k,
        )
        _print_hits(subs, hits)
        return 0

    return 1


# `if __name__ == "__main__"`：只有「直接运行本文件」时才执行 main；
# 若被别的模块 import，则不会误跑命令行逻辑。
if __name__ == "__main__":
    raise SystemExit(main())
