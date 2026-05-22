"""
工具调用型 Agent 的 Prompt 模板（与「用哪個模型」解耦）。

LangChain ``create_tool_calling_agent`` 对 ``ChatPromptTemplate`` 有硬性约定：
- 模板中必须出现名为 ``agent_scratchpad`` 的占位符；
- 中间步骤里，模型思考与工具调用结果会通过该占位符注入为消息序列。

本模块只负责「消息结构」，不在此写死系统提示正文；系统提示由调用方传入，
便于同一套结构复用于不同人设（客服 / 代码助手等）。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def build_tool_calling_prompt(system_prompt: str) -> ChatPromptTemplate:
    """
    构建标准的三段式工具调用 Agent 模板。

    消息顺序及原因：
    1. ``("system", system_prompt)``：人设与行为约束，放在最前，优先级最高；
    2. ``("human", "{input}")``：用户当前轮输入；``AgentExecutor.invoke`` 传入 ``{\"input\": ...}``；
    3. ``MessagesPlaceholder("agent_scratchpad")``：ReAct/工具链路中累积的「Thought / Action / Observation」
       会被 ``format_to_tool_messages`` 转成消息块插入此处。

    若需要多轮对话记忆，请使用 ``build_tool_calling_prompt_with_chat_history``，
    在 system 与 human 之间插入 ``MessagesPlaceholder("chat_history")``，
    并在 invoke 时传入 ``chat_history`` 列表（名称需一致）。
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )


def build_tool_calling_prompt_with_chat_history(system_prompt: str) -> ChatPromptTemplate:
    """
    与 ``build_tool_calling_prompt`` 相同，但在 system 与用户输入之间插入 ``chat_history``。

    ``optional=True``：无历史时可传空列表，不强制占位。
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
