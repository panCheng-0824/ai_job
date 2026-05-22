"""
================================================================================
综合学习 Demo：FastAPI + LangChain + Skills + Function Calling + MCP（概念对齐）
================================================================================

**框架约定（本仓库 Demo 一致）：智能体侧统一使用 LangChain**
- `langchain`：`AgentExecutor`、`create_openai_functions_agent` 等 Agent 编排
- `langchain-core`：`@tool` / `BaseTool`、消息与 Runnable 抽象
- `langchain-openai`：`ChatOpenAI`（你可接 OpenAI，也可像 day1 那样接 Ollama 兼容端点）

FastAPI / uvicorn 只负责 **HTTP 外壳**；推理、工具绑定、多轮 tool 循环均在 LangChain 内完成。

你现有代码里的对应关系（建议对照阅读）：
- day1.py：LangChain `create_openai_functions_agent` + `@tool`
  → OpenAI 兼容的 **Function Calling**：模型输出结构化调用，由框架执行工具。
- day2.py：FastAPI 把 LangChain Agent 暴露成 HTTP API。
- day3.py：`AgentSkill` / 工厂函数 → 在 LangChain 之上封一层「可复用技能」。

本文件做三件事（都由详细注释说明）：
1) HTTP 聊天：FastAPI + day3 的 `AgentSkill`（内部仍是 LangChain `AgentExecutor`）。
2) 直接调工具：对 `langchain_core` 的 `BaseTool` 调用 `.invoke()`（不经 LLM）。
3) MCP 风格 JSON-RPC：极简 `tools/list` 与 `tools/call`，工具元数据来自 LangChain Tool。

说明（重要）：
- 真实的 MCP 协议由 Anthropic 推动，常用 JSON-RPC 2.0，还可能包含 resources/prompts 等能力；
  这里只实现最常用的「列出工具 / 调用工具」，避免引入额外依赖，专注概念。
- 生产环境通常：一个共享的 LLM + `AgentExecutor` + 外部存储的 `chat_history`，
  而不是为每个用户 new 一个 `AgentSkill`（本 Demo 为清晰起见按用户隔离技能实例）。

写给 Python / Web 初学者（速查）
--------------------------------
- **FastAPI**：用普通函数 + 类型标注定义接口；``@app.post("/chat")`` 表示接受 HTTP POST。
- **Pydantic v2**：``BaseModel`` 描述 JSON 长什么样；``Field(...)`` 可写描述、默认值、是否必填。
- **三条路由对照学**：
  1) ``POST /chat``：大模型**自己决定**是否调工具（Function Calling 循环在 LangChain 内）。
  2) ``POST /tools/invoke``：**你指定**工具名和参数，不经过模型（调试工具、理解 RPC）。
  3) ``POST /mcp``：JSON-RPC 形态的 list/call，接近真实 MCP 客户端与服务端对话方式。
- **端口**：本文件默认 **8001**，与 day2 的 8000 错开，可同时跑两个服务做对比。
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
from fastapi.responses import HTMLResponse

# LangChain Core：工具基类；``@tool`` 装饰器生成的对象也继承 ``BaseTool``，统一有 ``.name``、``.invoke()``。
from langchain_core.tools import BaseTool

# 用于把 Redis 存的历史转回 LangChain 消息
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# ---------------------------------------------------------------------------
# 从你自己的 day3 引入「技能」封装与默认工具列表（内部全是 LangChain）
# AgentSkill：ChatOpenAI + ChatPromptTemplate + create_openai_functions_agent + AgentExecutor
# DEFAULT_TOOLS：langchain_core.tools @tool → 绑定到 LLM 的 function schema
# ---------------------------------------------------------------------------
from study01.day3 import AgentSkill, DEFAULT_TOOLS, create_basic_agent
from study01.llm import create_llm

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


# =============================================================================
# 一、FastAPI 应用与 Pydantic 模型（Web 层）
# =============================================================================

app = FastAPI(
    title="FastAPI + LangChain Agent + MCP-style Demo",
    description="HTTP 由 FastAPI 提供；Agent、Tools、Function Calling 由 LangChain（见 study01/day1~day3）",
    version="1.0.0",
)

# 说明：Web UI 是纯静态 HTML（无前端依赖），用来演示 request_id + Redis 上下文 + MCP 调用。
_DAY4_UI_PATH = os.path.join(os.path.dirname(__file__), "day4_ui.html")


class ChatRequest(BaseModel):
    """聊天请求：必须提供 request_id，用于从 Redis 取出上下文。"""

    request_id: str = Field(..., description="由 /session/start 生成并返回")
    message: str = Field(..., description="用户本轮输入")
    enable_compression: Optional[bool] = Field(
        None,
        description="覆盖服务端默认压缩开关；None 表示使用服务端默认",
    )


class ChatResponse(BaseModel):
    """聊天响应：模型最终自然语言回复。"""

    reply: str = Field(..., description="Agent 最终回复")
    request_id: str = Field(..., description="会话 request_id")
    context_chars: int = Field(..., description="当前上下文字符数（粗略）")
    context_ratio: float = Field(..., description="当前上下文占用比例（0~1）")
    compressed: bool = Field(False, description="本轮是否执行了上下文压缩")


# =============================================================================
# 二、按用户管理 AgentSkill（Skills + Agent 生命周期）
# =============================================================================
# Function Calling 发生在哪里？
# - 在 AgentSkill 内部的 agent_executor.invoke(...) 里：
#   LLM 会先「想」要不要调用工具；若要，则发出 tool_calls（函数名+JSON 参数），
#   框架执行对应 @tool，再把结果塞回模型，直到得到最终 assistant 文本。
# 这与下面「MCP 风格 tools/call」不同：后者是**你**指定调用哪个工具，不经过模型决策。
# =============================================================================

_skills_by_user: Dict[str, AgentSkill] = {}


def _create_basic_agent_compat(model: str = "qwen35-unc-9b") -> AgentSkill:
    """
    兼容不同版本的 `create_basic_agent` 签名。
    - 有的版本支持 `verbose=...`
    - 有的版本不支持（如你当前 day3 门面导出的实现）
    """
    try:
        return create_basic_agent(model)
    except TypeError:
        return create_basic_agent()


def get_skill_for_user(user_id: str) -> AgentSkill:
    """
    每个 user_id 懒加载一个 AgentSkill。

    为何这样写（学习向）：
    - AgentSkill 内部自带 chat_history，适合演示「多用户各有一份记忆」。
    - 若只有一个全局 AgentSkill，多用户对话会串味。

    代价：
    - 每个用户持有一份 LLM 客户端与执行器引用；高并发下应改为共享 executor + 外部会话存储。
    """
    if user_id not in _skills_by_user:
        # verbose=False：避免在服务器日志里刷屏链式思考；学习时可改 True
        _skills_by_user[user_id] = _create_basic_agent_compat('qwen35-unc-9b')
    return _skills_by_user[user_id]


# =============================================================================
# 2.5 Redis 上下文（让 /chat 与 /mcp 共享一份上下文）
# =============================================================================

REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_PREFIX = os.environ.get("REDIS_PREFIX", "study01:ctx:")
REDIS_TTL_SECONDS = int(os.environ.get("REDIS_TTL_SECONDS", str(60 * 60 * 24)))
REDIS_USERNAME = os.environ.get("REDIS_USERNAME","default") or None
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "pc0824tq") or None

MAX_CONTEXT_CHARS = int(os.environ.get("MAX_CONTEXT_CHARS", "12000"))
CONTEXT_BLOCK_RATIO = float(os.environ.get("CONTEXT_BLOCK_RATIO", "0.9"))
ENABLE_CONTEXT_COMPRESSION = os.environ.get("ENABLE_CONTEXT_COMPRESSION", "false").lower() in (
    "1",
    "true",
    "yes",
)


def _get_redis_client():
    if redis is None:
        raise HTTPException(status_code=500, detail="未安装 redis Python 包，请先 `pip install redis`")
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis 连接失败: {e}") from e


def _redis_key(request_id: str) -> str:
    return f"{REDIS_PREFIX}{request_id}"


def _save_history(client, request_id: str, history: List[Dict[str, str]]) -> None:
    client.setex(_redis_key(request_id), REDIS_TTL_SECONDS, json.dumps(history, ensure_ascii=False))


def _load_history(client, request_id: str) -> List[Dict[str, str]]:
    raw = client.get(_redis_key(request_id))
    if not raw:
        raise HTTPException(status_code=404, detail="request_id 不存在或已过期，请先 /session/start")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"上下文反序列化失败: {e}") from e
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="上下文格式非法（应为 list）")
    return data


def _history_chars(history: List[Dict[str, str]]) -> int:
    return sum(len(h.get("content", "")) for h in history)


def _to_langchain_messages(history: List[Dict[str, str]]) -> List[Any]:
    out: List[Any] = []
    for h in history:
        role = h.get("role")
        content = h.get("content", "")
        if role == "user":
            out.append(HumanMessage(content=content))
        else:
            out.append(AIMessage(content=content))
    return out


def _compress_history_with_llm(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if len(history) <= 4:
        return history
    old_part = history[:-4]
    recent_part = history[-4:]
    old_text = "\n".join(f"{h.get('role')}: {h.get('content', '')}" for h in old_part)

    llm = create_llm()
    msg = llm.invoke(
        [
            SystemMessage(
                content=(
                    "你是对话压缩助手。请将以下对话压缩为简洁记忆，保留：用户目标、约束、关键事实、未完成事项。"
                    "输出纯文本，不要markdown。"
                )
            ),
            HumanMessage(content=old_text),
        ]
    )
    summary = (msg.content or "").strip()
    if not summary:
        return history
    memory_item = {"role": "assistant", "content": f"[历史摘要]\n{summary}"}
    return [memory_item] + recent_part


# =============================================================================
# 三、路由：/chat —— FastAPI 暴露 Agent（带 Function Calling 的推理循环）
# =============================================================================


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "docs": "/docs",
        "ui": "/ui",
        "health": "GET /health",
        "session_start": "POST /session/start",
        "chat": "POST /chat",
        "direct_tool": "POST /tools/invoke",
        "mcp_style": "POST /mcp",
    }


@app.get("/health")
def health() -> Dict[str, str]:
    """轻量存活探针：不依赖外部服务。"""
    return {"status": "ok"}


@app.get("/ui", response_class=HTMLResponse)
def ui() -> HTMLResponse:
    """
    Day4 的演示页面（纯 HTML + JS）。
    用途：在浏览器里完成 /session/start、/chat、/mcp 的完整链路测试。
    """
    try:
        with open(_DAY4_UI_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"找不到 UI 文件：{_DAY4_UI_PATH}")


class StartSessionResponse(BaseModel):
    request_id: str
    message: str
    max_context_chars: int
    block_ratio: float


@app.post("/session/start", response_model=StartSessionResponse)
def session_start() -> StartSessionResponse:
    request_id = uuid.uuid4().hex
    client = _get_redis_client()
    _save_history(client, request_id, [])
    return StartSessionResponse(
        request_id=request_id,
        message="会话创建成功，请在 /chat 与 /mcp 中携带 request_id",
        max_context_chars=MAX_CONTEXT_CHARS,
        block_ratio=CONTEXT_BLOCK_RATIO,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    典型「Agent API」：
    1) HTTP 收到自然语言 message
    2) 交给 AgentSkill.run → 内部 AgentExecutor 可能多轮：LLM ⇄ Tools
    3) 返回最终字符串

    这里的「工具调用」对你是黑盒，由大模型根据 system prompt 与工具描述决定。
    """
    client = _get_redis_client()
    history = _load_history(client, req.request_id)

    current_chars = _history_chars(history)
    ratio = current_chars / max(1, MAX_CONTEXT_CHARS)
    threshold = MAX_CONTEXT_CHARS * CONTEXT_BLOCK_RATIO
    compressed = False

    compression_enabled = ENABLE_CONTEXT_COMPRESSION if req.enable_compression is None else req.enable_compression
    if current_chars >= threshold:
        if compression_enabled:
            history = _compress_history_with_llm(history)
            _save_history(client, req.request_id, history)
            compressed = True
            current_chars = _history_chars(history)
            ratio = current_chars / max(1, MAX_CONTEXT_CHARS)
        if current_chars >= threshold:
            raise HTTPException(
                status_code=413,
                detail=f"上下文已接近容量上限（{ratio:.1%} >= {CONTEXT_BLOCK_RATIO:.0%}），已拒绝本次请求。",
            )

    # Redis 是上下文真相来源：把历史转成 LangChain messages 传给 agent_executor
    chat_history_msgs = _to_langchain_messages(history)
    skill = _create_basic_agent_compat('qwen35-unc-9b')
    try:
        result = skill.agent_executor.invoke(
            {"input": req.message, "chat_history": chat_history_msgs, "agent_scratchpad": []}
        )
        reply = str(result.get("output", ""))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e

    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    _save_history(client, req.request_id, history)

    final_chars = _history_chars(history)
    final_ratio = final_chars / max(1, MAX_CONTEXT_CHARS)

    return ChatResponse(
        reply=reply,
        request_id=req.request_id,
        context_chars=final_chars,
        context_ratio=final_ratio,
        compressed=compressed,
    )


# =============================================================================
# 四、路由：/tools/invoke —— **显式**工具调用（对照 Function Calling）
# =============================================================================
# - LLM Function Call：模型选择 name + arguments
# - 本接口：调用方（前端/另一个服务）直接指定 name + arguments
#   这更接近「MCP 客户端调用服务器工具」或「内部微服务 RPC」的形态。
# =============================================================================


class ToolInvokeRequest(BaseModel):
    request_id: Optional[str] = Field(None, description="可选：若提供则把工具调用结果写入该会话上下文")
    name: str = Field(..., description="工具名，与 @tool 函数名一致，如 search、calculate")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数，键值与函数参数对应")


class ToolInvokeResponse(BaseModel):
    name: str
    result: str
    request_id: Optional[str] = None


def _tool_by_name() -> Dict[str, BaseTool]:
    """把 LangChain `DEFAULT_TOOLS` 编成 name -> BaseTool 映射，便于按名字 `.invoke()`。"""
    return {t.name: t for t in DEFAULT_TOOLS}


@app.post("/tools/invoke", response_model=ToolInvokeResponse)
def invoke_tool(req: ToolInvokeRequest) -> ToolInvokeResponse:
    """
    直接调用 LangChain Tool（@tool 生成），不经过大模型。

    用途：
    - 调试工具本身是否正确
    - 理解「工具 = 带 schema 的可调用单元」，与是否由 LLM 触发无关
    """
    mapping = _tool_by_name()
    tool = mapping.get(req.name)
    if tool is None:
        raise HTTPException(
            status_code=404,
            detail=f"未知工具: {req.name}，可用: {list(mapping.keys())}",
        )
    try:
        # LangChain StructuredTool：invoke 接受参数字典
        out = tool.invoke(req.arguments)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e
    if req.request_id:
        client = _get_redis_client()
        history = _load_history(client, req.request_id)
        history.append({"role": "assistant", "content": f"[Tool:{req.name}]\n{str(out)}"})
        _save_history(client, req.request_id, history)
        return ToolInvokeResponse(name=req.name, result=str(out), request_id=req.request_id)
    return ToolInvokeResponse(name=req.name, result=str(out), request_id=None)


# =============================================================================
# 五、路由：POST /mcp —— 极简 MCP 风格 JSON-RPC（tools/list & tools/call）
# =============================================================================
# MCP 核心直觉：
# - 服务端「注册」一批工具（名称、描述、JSON Schema）
# - 客户端发 JSON-RPC 请求列出或调用
# - Cursor / IDE 里的 MCP：常通过 stdio 或 HTTP 传这些消息
#
# 本 Demo 用 HTTP 承载两条 method，方便你用 curl 或 Swagger 试验。
# =============================================================================


class JsonRpcRequest(BaseModel):
    """极简 JSON-RPC 2.0 请求体（只支持本文件实现的 method）。"""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[int, str] = Field(..., description="请求 ID，原样带回")
    method: str = Field(..., description="tools/list 或 tools/call")
    params: Optional[Dict[str, Any]] = Field(
        None,
        description="tools/call 时传入 name 与 arguments；可选 request_id 用于写入上下文",
    )


class JsonRpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[int, str]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


def _mcp_tools_list() -> Dict[str, Any]:
    """
    对应 MCP 的 tools/list 语义（简化）：返回每个工具的名称、描述与参数 schema。

    元数据来自 LangChain `BaseTool`：`.name`、`.description`、`.args_schema`（Pydantic，用于 JSON Schema）。
    """
    tools_payload: List[Dict[str, Any]] = []
    for t in DEFAULT_TOOLS:
        schema = {}
        if getattr(t, "args_schema", None) is not None:
            # Pydantic v2：model_json_schema()
            schema = t.args_schema.model_json_schema()
        tools_payload.append(
            {
                "name": t.name,
                "description": t.description or "",
                "inputSchema": schema,
            }
        )
    return {"tools": tools_payload}


def _mcp_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
    """对应 MCP 的 tools/call：params 里含 name 与 arguments。"""
    name = params.get("name")
    if not isinstance(name, str):
        raise ValueError("params.name 必须是字符串")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise ValueError("params.arguments 必须是对象/dict")
    mapping = _tool_by_name()
    tool = mapping.get(name)
    if tool is None:
        raise ValueError(f"未知工具: {name}")
    content = tool.invoke(arguments)

    # 可选：把本次 MCP 工具调用结果写入 request_id 的上下文（让 /chat 能看到）
    req_id = params.get("request_id")
    if isinstance(req_id, str) and req_id.strip():
        client = _get_redis_client()
        history = _load_history(client, req_id)
        history.append({"role": "assistant", "content": f"[MCP Tool:{name}]\n{str(content)}"})
        _save_history(client, req_id, history)

    # MCP 里常见返回 structuredContent / content；这里用统一字符串 content
    return {"content": [{"type": "text", "text": str(content)}]}


@app.post("/mcp", response_model=JsonRpcResponse)
def mcp_jsonrpc(body: JsonRpcRequest) -> JsonRpcResponse:
    """
    极简 MCP 网关：
    - method == "tools/list" → 列出 DEFAULT_TOOLS
    - method == "tools/call" → 执行指定工具

    与 /chat 的区别：
    - /chat：大模型**自主** function calling（多步推理）
    - /mcp：协议层显式调用工具（你写客户端或在别的 Agent 里拼 JSON-RPC）

    示例（curl）：
    curl -s localhost:8001/mcp -H "Content-Type: application/json" -d \\
      '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

    curl -s localhost:8001/mcp -H "Content-Type: application/json" -d \\
      '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"calculate","arguments":{"expression":"1+2"}}}'
    """
    try:
        if body.method == "tools/list":
            return JsonRpcResponse(jsonrpc="2.0", id=body.id, result=_mcp_tools_list())
        if body.method == "tools/call":
            if not body.params:
                raise ValueError("tools/call 需要 params")
            return JsonRpcResponse(jsonrpc="2.0", id=body.id, result=_mcp_tools_call(body.params))
        raise ValueError(f"不支持的 method: {body.method}")
    except Exception as e:  # noqa: BLE001
        return JsonRpcResponse(
            jsonrpc="2.0",
            id=body.id,
            error={"code": -32000, "message": str(e)},
        )


# =============================================================================
# 六、入口：运行方式与端口
# =============================================================================
# 注意：day2 默认用 8000。本 Demo 使用 8001，避免与你已有服务冲突。
# 启动：在项目根目录执行
#   python -m study01.day4_fastapi_skills_mcp_demo
# 或
#   uvicorn study01.day4_fastapi_skills_mcp_demo:app --reload --port 8001
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "study01.day4_fastapi_skills_mcp_demo:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
