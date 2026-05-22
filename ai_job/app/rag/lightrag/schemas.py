"""LightRAG 路由请求模型定义。"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class LightRAGInsertRequest(BaseModel):
    """写入文本请求体。"""

    texts: List[str]
    # 与 texts 等长、按索引一一对应；每条非空文本建议传岗位 ID，将作为知识库文档 id（上传 id）写入 LightRAG
    job_ids: List[str] | None = None


class LightRAGQueryRequest(BaseModel):
    """问答请求体。"""

    query: str
    mode: str = "mix"
    top_k: int = 20
    # True：只做检索拼上下文，不调大模型生成综合回答（返回体仍为 answer 字段，内容为检索 JSON 等）
    only_need_context: bool = False
    # True：返回将发给模型的完整 system prompt，仍不调用大模型生成最终回答（调试用）
    only_need_prompt: bool = False


class GraphEntityCreateRequest(BaseModel):
    """创建图实体请求体。"""

    entity_name: str
    data: Dict[str, Any] = {}


class GraphEntityUpdateRequest(BaseModel):
    """更新图实体请求体。"""

    data: Dict[str, Any]


class GraphRelationCreateRequest(BaseModel):
    """创建图关系请求体。"""

    src_id: str
    tgt_id: str
    data: Dict[str, Any] = {}


class GraphRelationUpdateRequest(BaseModel):
    """更新图关系请求体。"""

    data: Dict[str, Any]
