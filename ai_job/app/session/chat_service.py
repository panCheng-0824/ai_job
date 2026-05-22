"""会话式对话调用的标准服务层。"""

from __future__ import annotations

from threading import Event
from typing import Any, Callable, Dict, Iterator, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from openai import OpenAI
from openai import NotFoundError as OpenAINotFoundError

from model_cfg import load_model_list
from lc_agent.selection import select_model_by_level
from role_pipeline import compress_context_to_messages, denoise_question
from app.session.user_turn_context import (
    assistant_turn_content_for_memory,
    user_turn_content_for_memory,
)
from user_model import build_system_prompt_from_user, load_role_profiles, load_user_model
from user_session import run_user_query_for_runtime_session


class ChatServiceResult(TypedDict):
    """HTTP/控制器层使用的统一返回结构。"""

    answer: str
    raw_result: Dict[str, Any]


class ChatTokenStreamContext(TypedDict):
    """SSE 流式输出所需的上下文结构。"""

    usercode: str
    model_level: str
    token_iter: Iterator[Dict[str, str]]
    cancel: Callable[[], None]


def _history_to_messages(history: List[Dict[str, Any]]) -> List[BaseMessage]:
    """把历史轮次转换为 LangChain 消息对象列表。"""
    out: List[BaseMessage] = []
    for turn in history:
        role = turn.get("role")
        if role == "user":
            out.append(HumanMessage(content=user_turn_content_for_memory(turn)))
        elif role == "assistant":
            out.append(AIMessage(content=assistant_turn_content_for_memory(turn)))
    return out


def _history_to_memory_turns(history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """把历史轮次规整为仅含 role/content 的轻量结构。"""
    out: List[Dict[str, str]] = []
    for turn in history:
        role = turn.get("role")
        if role == "user":
            out.append({"role": role, "content": user_turn_content_for_memory(turn)})
        elif role == "assistant":
            out.append({"role": role, "content": assistant_turn_content_for_memory(turn)})
    return out


def _to_openai_messages(system_prompt: str, history: List[BaseMessage], question: str) -> List[Dict[str, str]]:
    """拼装 OpenAI 兼容消息数组（system + history + 当前问题）。"""
    msgs: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "assistant" if isinstance(msg, AIMessage) else "user"
        msgs.append({"role": role, "content": str(msg.content)})
    msgs.append({"role": "user", "content": question})
    return msgs


def stream_chat_service_tokens(
    *,
    usercode: str,
    message: str,
    history: List[Dict[str, Any]],
    temperature: float = 0.0,
    use_role_pipeline: bool = True,
    system_prompt_extra: Optional[str] = None,
) -> ChatTokenStreamContext:
    """
    构建用于 SSE 的真实 Token 级流式输出。

    这里直接调用 OpenAI 兼容流式接口，产出的分片是模型增量内容，
    而不是服务端对整段文本的二次切片。
    """
    user = load_user_model(usercode=usercode)
    model_level = str(user.get("model_level", "mid"))
    entry = select_model_by_level(load_model_list(), model_level)

    question = (message or "").strip()
    hist_msgs = _history_to_messages(history)
    if use_role_pipeline:
        profiles = load_role_profiles()
        question = denoise_question(question, profiles["question_denoiser"])
        hist_msgs, _ = compress_context_to_messages(
            _history_to_memory_turns(history),
            profiles["context_compressor"],
        )

    sys_prompt = build_system_prompt_from_user(user)
    extra = (system_prompt_extra or "").strip()
    if extra:
        sys_prompt = sys_prompt + "\n\n" + extra

    messages = _to_openai_messages(sys_prompt, hist_msgs, question)
    client = OpenAI(
        api_key=entry["model_key"],
        base_url=entry["model_api"],
    )
    stream = client.chat.completions.create(
        model=entry["model_name"],
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    cancel_event = Event()

    def _close_stream() -> None:
        closer = getattr(stream, "close", None)
        if callable(closer):
            try:
                closer()
            except Exception:
                pass

    def _cancel() -> None:
        cancel_event.set()
        _close_stream()

    def _iter_tokens() -> Iterator[Dict[str, str]]:
        try:
            for chunk in stream:
                if cancel_event.is_set():
                    break
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                thinking_piece = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None) or ""
                content_piece = delta.content or ""
                if thinking_piece:
                    yield {"type": "thinking", "content": str(thinking_piece)}
                if content_piece:
                    yield {"type": "answer", "content": str(content_piece)}
        except Exception:
            if not cancel_event.is_set():
                raise
        finally:
            _close_stream()

    return {
        "usercode": usercode,
        "model_level": model_level,
        "token_iter": _iter_tokens(),
        "cancel": _cancel,
    }


def run_chat_service(
    *,
    usercode: str,
    message: str,
    history: List[Dict[str, Any]],
    verbose: bool = False,
    temperature: float = 0.0,
    use_role_pipeline: bool = False,
    system_prompt_extra: Optional[str] = None,
) -> ChatServiceResult:
    """
    单轮对话的标准服务调用入口。

    执行流程（与 demo.py 主链路保持一致）：
    1) 通过 ``usercode`` 从 usermodel.json 解析角色；
    2) 调用会话编排入口；
    3) 执行主 Agent（可选启用角色管道）。
    """
    try:
        result = run_user_query_for_runtime_session(
            usercode=usercode,
            question=message,
            context_memory=history,
            verbose=verbose,
            temperature=temperature,
            use_role_pipeline=use_role_pipeline,
            system_prompt_extra=system_prompt_extra,
        )
    except OpenAINotFoundError as exc:
        raise RuntimeError(
            "模型服务返回 404。请检查 modelCfg.json 的 model_api/model_name 是否正确；"
            "如果你把 Web 服务也启动在 8000 端口，且 model_api 也是 http://127.0.0.1:8000/v1，"
            "通常是请求打到了本项目 FastAPI，而不是模型服务。"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"会话调用失败: {exc}") from exc
    return {
        "answer": str(result.get("output", "")).strip(),
        "raw_result": result,
    }
