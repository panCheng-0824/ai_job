"""
``lc_agent`` 包：基于 ``modelCfg.json`` 与 LangChain 的工具调用型 Agent。

子模块分工（由外向内阅读即可理解全链路）：
- ``constants``：默认档位、默认系统提示、默认温度；
- ``selection``：从已加载的模型列表里按档位选一条（不读文件）；
- ``llm``：``ModelEntry`` → ``ChatOpenAI``；
- ``builtin_tools``：未传工具时的保底工具；
- ``prompts``：含 ``agent_scratchpad`` 的 Chat 模板；
- ``factory``：``create_agent_executor`` 组装 ``AgentExecutor``。

对外稳定 API 见 ``__all__``。
"""

from .factory import create_agent_executor
from .llm import chat_model_from_entry
from .selection import select_model_by_level

# 兼容旧命名：原先单文件 lc_agent.py 中的 select_model
select_model = select_model_by_level

__all__ = [
    "create_agent_executor",
    "chat_model_from_entry",
    "select_model_by_level",
    "select_model",
]
