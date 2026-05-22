"""
LangChain 1.x 起 ``AgentExecutor`` / ``create_tool_calling_agent`` 不再从 ``langchain.agents`` 导出。

优先尝试旧路径；失败则使用 ``langchain-classic``（须 ``pip install langchain-classic``）。
"""

from __future__ import annotations

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    try:
        from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
    except ImportError as exc:
        raise ImportError(
            "无法从 langchain.agents 导入 AgentExecutor / create_tool_calling_agent。"
            "若当前为 LangChain>=1.0，请安装兼容包：pip install langchain-classic"
        ) from exc

__all__ = ["AgentExecutor", "create_tool_calling_agent"]
