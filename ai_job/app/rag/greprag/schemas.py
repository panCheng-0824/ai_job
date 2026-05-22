"""GrepRAG 路由请求模型定义。"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel


class GrepRAGInsertRequest(BaseModel):
    """批量写入文本请求体。"""

    texts: List[str]
    source: str = "manual"


class GrepRAGQueryRequest(BaseModel):
    """检索问答请求体。"""

    query: str
    top_k: int = 5


class GrepRAGReindexRequest(BaseModel):
    """重建索引请求体。"""

    clear_existing: bool = False


class GrepRAGTextToMdRequest(BaseModel):
    """文本落盘为 Markdown 请求体。"""

    filename: str
    text: str
