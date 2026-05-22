"""
Agent 组装工厂：把「配置 + LLM + 工具 + Prompt + LangChain Agent」串成可执行的 ``AgentExecutor``。

依赖关系（单向）：
- ``model_cfg.load_model_list``：唯一读盘入口，可替换为测试中的假数据加载器；
- ``selection`` / ``llm`` / ``prompts`` / ``builtin_tools``：均无全局状态，纯函数为主。

若需单测 ``create_agent_executor`` 而不访问真实 ``modelCfg.json``，可考虑后续为
``load_model_list`` 注入可替换的 Callable（当前保持简单默认实现）。
"""

from typing import Callable, List, Optional, Sequence

from langchain_core.tools import BaseTool

from model_cfg import ModelEntry, load_model_list

from .agent_executor_compat import AgentExecutor, create_tool_calling_agent
from .builtin_tools import build_default_tools
from .constants import (
    DEFAULT_MODEL_LEVEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
)
from .llm import chat_model_from_entry
from .prompts import (
    build_tool_calling_prompt,
    build_tool_calling_prompt_with_chat_history,
)
from .selection import select_model_by_level


def _coalesce_tools(user_tools: Optional[Sequence[BaseTool]]) -> List[BaseTool]:
    """若调用方未提供工具，则退回内置列表，保证后续 ``bind_tools`` 非空列表（在实现上允许空，但业务上不建议）。"""
    if user_tools is not None:
        return list(user_tools)
    return build_default_tools()


def create_agent_executor(
    *,
    model_level: str = DEFAULT_MODEL_LEVEL,
    tools: Optional[Sequence[BaseTool]] = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    verbose: bool = False,
    temperature: float = DEFAULT_TEMPERATURE,
    model_loader: Callable[[], List[ModelEntry]] = load_model_list,
    with_chat_history: bool = False,
) -> AgentExecutor:
    """
    根据 ``modelCfg`` 中指定档位的模型创建 ``AgentExecutor``。

    步骤概览：
    1. ``model_loader()`` 拉取全部 ``ModelEntry``（默认识别项目根附近的 ``modelCfg.json``）；
    2. ``select_model_by_level`` 选中目标档位；
    3. ``chat_model_from_entry`` 实例化 ``ChatOpenAI``；
    4. 解析工具列表（用户自定义或内置）；
    5. ``build_tool_calling_prompt`` 或（``with_chat_history=True`` 时）
       ``build_tool_calling_prompt_with_chat_history`` 生成模板；
    6. ``create_tool_calling_agent`` 得到 Runnable Agent；
    7. ``AgentExecutor`` 包装为带工具执行循环的可调用对象。

    :param model_level: 与 JSON 里 ``model_level`` 对齐；未命中时见 ``select_model_by_level`` 兜底策略。
    :param tools: 传入则完全使用你的工具集；不传则使用内置 ``ping`` 等。
    :param system_prompt: 系统消息文本，覆盖 ``DEFAULT_SYSTEM_PROMPT``。
    :param verbose: 为 True 时 executor 打印中间推理（调试用）。
    :param temperature: 传给 ``ChatOpenAI`` 的采样温度。
    :param model_loader: 可注入的模型列表加载器，默认 ``load_model_list``，测试时可替换成内存数据。
    :param with_chat_history: 为 True 时使用带 ``chat_history`` 占位符的模板；
        invoke 时需额外传入 ``{"chat_history": [...]}``（可为空列表）。
    """
    entries = model_loader()
    entry = select_model_by_level(entries, model_level)
    llm = chat_model_from_entry(entry, temperature=temperature)
    tool_list = _coalesce_tools(tools)

    if with_chat_history:
        prompt = build_tool_calling_prompt_with_chat_history(system_prompt)
    else:
        prompt = build_tool_calling_prompt(system_prompt)
    agent = create_tool_calling_agent(llm, tool_list, prompt)
    return AgentExecutor(agent=agent, tools=tool_list, verbose=verbose)
