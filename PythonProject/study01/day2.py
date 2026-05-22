"""
================================================================================
Agent 学习 Demo —— Day 2（升级版）：FastAPI + Redis 会话上下文管理
================================================================================

本版新增能力（对应你的需求）：
1) 首次创建会话：生成 `request_id` 返回给客户端（/session/start）
2) 聊天请求必须携带 `request_id`（/chat）
3) 上下文放 Redis，而不是内存变量
4) 默认限制上下文大小；达到 90% 阈值时拒绝请求并提示
5) 可选压缩开关：触发时用 LLM 压缩上下文，再回写 Redis
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from study01.day1 import create_agent
from study01.llm import create_llm

try:
    import redis
except Exception:  # pragma: no cover - 学习环境里可能未安装 redis 包
    redis = None


# -----------------------------------------------------------------------------
# 一、配置（可通过环境变量覆盖）
# -----------------------------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_PREFIX = os.environ.get("REDIS_PREFIX", "study01:ctx:")
REDIS_TTL_SECONDS = int(os.environ.get("REDIS_TTL_SECONDS", str(60 * 60 * 24)))  # 24h

# 上下文大小控制：按字符数计算，简单直观（后续可换 token 计数）
MAX_CONTEXT_CHARS = int(os.environ.get("MAX_CONTEXT_CHARS", "12000"))
CONTEXT_BLOCK_RATIO = float(os.environ.get("CONTEXT_BLOCK_RATIO", "0.9"))  # 90%

# 压缩开关（默认关闭）
ENABLE_CONTEXT_COMPRESSION = os.environ.get("ENABLE_CONTEXT_COMPRESSION", "false").lower() in (
    "1",
    "true",
    "yes",
)


# -----------------------------------------------------------------------------
# 二、FastAPI 与模型
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Agent API (Redis Context)",
    description="request_id + Redis 上下文管理 + 阈值保护 + 可选压缩",
    version="2.0.0",
)

agent_executor = create_agent()


# -----------------------------------------------------------------------------
# 三、Pydantic 模型
# -----------------------------------------------------------------------------
class StartSessionResponse(BaseModel):
    request_id: str
    message: str
    max_context_chars: int
    block_ratio: float


class ChatRequest(BaseModel):
    request_id: str = Field(..., description="必须由 /session/start 先拿到")
    message: str
    enable_compression: Optional[bool] = Field(
        None,
        description="覆盖全局压缩开关；None 表示使用服务端默认配置",
    )


class ChatResponse(BaseModel):
    request_id: str
    message: str
    context_chars: int
    context_ratio: float
    compressed: bool = False


# -----------------------------------------------------------------------------
# 四、Redis 上下文存取
# -----------------------------------------------------------------------------
def _get_redis_client():
    if redis is None:
        raise HTTPException(status_code=500, detail="未安装 redis Python 包，请先 `pip install redis`")
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,  # 直接拿 str，不拿 bytes
        )
        client.ping()
        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis 连接失败: {e}") from e


def _redis_key(request_id: str) -> str:
    return f"{REDIS_PREFIX}{request_id}"


def _load_history(client, request_id: str) -> List[Dict[str, str]]:
    raw = client.get(_redis_key(request_id))
    if not raw:
        raise HTTPException(status_code=404, detail="request_id 不存在或已过期，请重新创建会话")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"上下文反序列化失败: {e}") from e
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="上下文格式非法（应为 list）")
    return data


def _save_history(client, request_id: str, history: List[Dict[str, str]]) -> None:
    client.setex(_redis_key(request_id), REDIS_TTL_SECONDS, json.dumps(history, ensure_ascii=False))


def _history_chars(history: List[Dict[str, str]]) -> int:
    total = 0
    for item in history:
        total += len(item.get("content", ""))
    return total


def _to_langchain_messages(history: List[Dict[str, str]]) -> List[Any]:
    out: List[Any] = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role == "user":
            out.append(HumanMessage(content=content))
        else:
            out.append(AIMessage(content=content))
    return out


def _compress_history_with_llm(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    压缩策略（学习版）：
    - 保留最近 2 轮原文（更贴近当前对话）
    - 较早历史交给 LLM 生成“摘要记忆”作为一条 system note
    """
    if len(history) <= 4:
        return history
    old_part = history[:-4]
    recent_part = history[-4:]
    old_text = "\n".join(f"{h.get('role')}: {h.get('content', '')}" for h in old_part)

    llm = create_llm()
    summary_msg = llm.invoke(
        [
            SystemMessage(
                content=(
                    "你是对话压缩助手。请将以下多轮对话压缩为简洁记忆，保留：用户目标、约束、关键事实、未完成事项。"
                    "输出纯文本，不要markdown。"
                )
            ),
            HumanMessage(content=old_text),
        ]
    )
    summary = (summary_msg.content or "").strip()
    if not summary:
        return history

    # 用 assistant 角色存摘要，保持后续 Agent 仍能读懂上下文
    memory_item = {"role": "assistant", "content": f"[历史摘要]\n{summary}"}
    return [memory_item] + recent_part


# -----------------------------------------------------------------------------
# 五、API 路由
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "欢迎使用 Agent API", "version": "2.0.0", "docs": "/docs"}


@app.get("/health")
def health_check():
    client = _get_redis_client()
    return {"status": "ok", "redis": bool(client.ping())}


@app.post("/session/start", response_model=StartSessionResponse)
def start_session():
    """
    首次会话创建：
    - 生成 request_id
    - 在 Redis 写入空历史
    """
    request_id = uuid.uuid4().hex
    client = _get_redis_client()
    _save_history(client, request_id, [])
    return StartSessionResponse(
        request_id=request_id,
        message="会话创建成功，请在 /chat 请求中携带 request_id",
        max_context_chars=MAX_CONTEXT_CHARS,
        block_ratio=CONTEXT_BLOCK_RATIO,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    聊天接口（必须携带 request_id）。
    核心流程：
    1) 从 Redis 读取上下文
    2) 检查上下文容量（>=90% 触发保护）
    3) 可选压缩（LLM 压缩后写回 Redis）
    4) 调 Agent 并把新问答写回 Redis
    """
    client = _get_redis_client()
    history = _load_history(client, request.request_id)

    current_chars = _history_chars(history)
    ratio = current_chars / max(1, MAX_CONTEXT_CHARS)
    threshold = MAX_CONTEXT_CHARS * CONTEXT_BLOCK_RATIO
    compressed = False

    compression_enabled = ENABLE_CONTEXT_COMPRESSION if request.enable_compression is None else request.enable_compression

    # 当快接近上限时：默认拒绝；若启用压缩，则先尝试压缩再判断
    if current_chars >= threshold:
        if compression_enabled:
            history = _compress_history_with_llm(history)
            _save_history(client, request.request_id, history)
            compressed = True
            current_chars = _history_chars(history)
            ratio = current_chars / max(1, MAX_CONTEXT_CHARS)
        if current_chars >= threshold:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"上下文已接近容量上限（{ratio:.1%} >= {CONTEXT_BLOCK_RATIO:.0%}），已拒绝本次请求。"
                    "你可以：1) 开启压缩开关；2) 新建 request_id；3) 清理会话历史。"
                ),
            )

    # 转为 LangChain 消息类型
    chat_history = _to_langchain_messages(history)

    try:
        result = agent_executor.invoke(
            {
                "agent_name": "小潼",
                "personality": "你说话的语气特别温柔",
                "language": "中文",
                "role": "助手",
                "input": request.message,
                "chat_history": chat_history,
                "agent_scratchpad": [],
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模型调用失败: {e}") from e

    answer = str(result.get("output", ""))
    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": answer})
    _save_history(client, request.request_id, history)

    final_chars = _history_chars(history)
    final_ratio = final_chars / max(1, MAX_CONTEXT_CHARS)

    return ChatResponse(
        request_id=request.request_id,
        message=answer,
        context_chars=final_chars,
        context_ratio=final_ratio,
        compressed=compressed,
    )


@app.get("/history/{request_id}")
def get_history(request_id: str):
    client = _get_redis_client()
    history = _load_history(client, request_id)
    return {"request_id": request_id, "history": history, "context_chars": _history_chars(history)}


@app.delete("/history/{request_id}")
def clear_history(request_id: str):
    client = _get_redis_client()
    key = _redis_key(request_id)
    deleted = client.delete(key)
    return {"request_id": request_id, "deleted": bool(deleted)}


if __name__ == "__main__":
    print("=" * 60)
    print("启动 Agent API 服务（Redis Context 版）...")
    print("API 文档: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run(
        "study01.day2:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
