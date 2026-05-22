"""
================================================================================
Day1 / Day2：带「人设 + 多轮历史」的 AgentExecutor 工厂
================================================================================

本模块和 ``agent_skill.py`` 有什么区别？
----------------------------------------
- **persona_agent（本文件）**：系统提示里带 ``{agent_name}``、``{personality}`` 等**占位符**，
  每次 ``invoke`` 时由调用方传入具体值 —— 适合「同一套逻辑、不同人设」的 HTTP API（见 day2）。
- **AgentSkill**：系统提示是一段固定字符串，历史由对象自己维护 —— 适合封装成可复用「技能组件」（day3）。

技术栈（均在 LangChain 内）
--------------------------
- ``create_openai_functions_agent``：把 **聊天模型 + 工具列表 + Prompt 模板** 绑成「会做 function call 的 agent」。
- ``AgentExecutor``：负责**循环**：模型思考 → 若要调工具则执行工具 → 把结果喂回模型，直到产出最终回复。

阅读顺序建议
------------
1. ``persona_chat_prompt``：看清有哪些占位符、``MessagesPlaceholder`` 插在哪。
2. ``create_persona_agent_executor``：看清 agent 与 executor 如何组装。
3. 回到 ``day1.py`` / ``day2.py`` 看 ``invoke`` 时传入的字典键名必须与模板变量一致。
"""

from __future__ import annotations

from typing import Optional, Sequence

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from study01.llm import create_llm
from study01.tools import DEFAULT_TOOLS


def persona_chat_prompt() -> ChatPromptTemplate:
    """
    构造多轮对话用的 ChatPromptTemplate。

    模板里三类东西（初学重点）：
    1. ``("system", "...{role}...")``：系统消息，里面的花括号是**变量**，invoke 时要传。
    2. ``MessagesPlaceholder(variable_name="chat_history")``：**预先留空位**，运行时塞入历史消息列表。
    3. ``("human", "{input}")``：本轮用户输入。
    4. ``MessagesPlaceholder(variable_name="agent_scratchpad")``：Agent 推理过程（工具调用轨迹等），
       ``AgentExecutor`` 会自动填充，初学者可先当「黑盒」。

    想对照官方模板：可在 LangChain Hub 搜 ``openai-functions-agent`` 看社区标准写法。
    """
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
            你是一个专业的{role}助手，名字叫做{agent_name}。
            你的特点是：{personality}
            请始终使用{language}回复。
            当需要计算数学题时，必须使用 calculate 工具。
            当需要搜索信息时，必须使用 search 工具。""",
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )


def create_persona_agent_executor(
    llm: Optional[ChatOpenAI] = None,
    tools: Optional[Sequence] = None,
    *,
    max_iterations: int = 3,
    verbose: bool = True,
) -> AgentExecutor:
    """
    构建带 Function Calling 的 ``AgentExecutor``。

    Args:
        llm: 不传则使用 ``study01.llm.create_llm()`` 默认配置。
        tools: 不传则使用 ``DEFAULT_TOOLS``（search、calculate）。传入时请传**工具对象列表**。
        max_iterations: 模型与工具之间最多循环几步，防止死循环刷爆 token。
        verbose: True 时在终端打印 ReAct/工具调用轨迹，**学习阶段强烈建议开**。

    Returns:
        可直接 ``.invoke({...})`` 的执行器；字典里需包含 prompt 中全部变量（如 ``agent_name``、
        ``input``、``chat_history``、``agent_scratchpad``）。
    """
    _llm = llm or create_llm()
    _tools = list(tools) if tools is not None else list(DEFAULT_TOOLS)
    prompt = persona_chat_prompt()
    agent = create_openai_functions_agent(llm=_llm, tools=_tools, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=_tools,
        verbose=verbose,
        max_iterations=max_iterations,
    )
