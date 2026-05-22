"""
================================================================================
Day3：AgentSkill 类与工厂函数（「技能」封装层）
================================================================================

「Skill」在这里指什么？
----------------------
- 把 **LLM + 系统提示 + 工具列表 + AgentExecutor + 对话历史** 打成一个对象，
  对外只暴露 ``run("用户一句话")`` —— 像调用一个「会聊天、会调工具」的技能。

与 ``persona_agent.py`` 的取舍
-----------------------------
- **AgentSkill**：系统提示是**固定字符串**（或可构造后固定），**历史存在对象属性** ``chat_history``，
  适合 FastAPI 里 ``每用户一个 skill 实例`` 的演示。
- **persona_agent**：人设来自 **invoke 参数**，历史由**调用方**传入列表，适合 day1/day2 那种模板。

本文件依赖
----------
- ``study01.llm.create_llm``、``study01.tools`` 中的工具列表。
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, List, Optional

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI

from study01.llm import create_llm
from study01.tools import DEFAULT_TOOLS, EXTENDED_TOOLS

# 默认系统提示：约束模型用中文、并在需要时调用指定工具（与 tools 描述配合）。
DEFAULT_SYSTEM_PROMPT = """
            你是一个专业的AI助手。
            请始终用中文回复。
            当需要计算数学题时，必须使用 calculate 工具。
            当需要搜索信息时，必须使用 search 工具。
            """


class AgentSkill:
    """
    封装 LangChain Agent，并维护多轮 ``chat_history``。

    常用方法：
    - ``run(text)``：跑一轮对话（内部 ``invoke`` AgentExecutor），并把本轮问答追加进历史。
    - ``clear_history()``：清空记忆（演示用；生产应使用持久化存储）。
    """

    def __init__(
        self,
        model: str = "qwen3:8b",
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "sk-ollama",
        temperature: float = 0,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 5,
        verbose: bool = True,
    ):
        # 配置项原样保存，便于以后扩展「动态改模型」等能力。
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.tools: List[BaseTool] = list(tools or DEFAULT_TOOLS)
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.chat_history: List[Any] = []

        self.llm = create_llm(
            model=model,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
        )

        self.system_prompt = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
        self.prompt = self._create_prompt()
        self._create_agent()

    def _create_prompt(self) -> ChatPromptTemplate:
        """内部：拼装与 persona 版类似的模板，但 system 为固定字符串。"""
        return ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    def _create_agent(self) -> None:
        """内部：创建 agent 与 executor，结果挂在 ``self.agent_executor``。"""
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt,
        )
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=self.max_iterations,
        )

    def run(self, input_text: str, clear_history: bool = False) -> str:
        """
        执行一轮用户输入，返回模型最终回复字符串。

        Args:
            input_text: 用户本轮消息。
            clear_history: True 时先清空 ``chat_history``，用于「新会话」。

        注意：
        - ``agent_scratchpad`` 每次传空列表，由 ``AgentExecutor`` 在当轮推理中填充。
        """
        if clear_history:
            self.chat_history = []

        result = self.agent_executor.invoke(
            {
                "input": input_text,
                "chat_history": self.chat_history,
                "agent_scratchpad": [],
            }
        )

        self.chat_history.append(HumanMessage(content=input_text))
        self.chat_history.append(AIMessage(content=result["output"]))
        return result["output"]

    def chat(self, input_text: str) -> str:
        """``run`` 的别名，语义上更贴近「聊天」。"""
        return self.run(input_text)

    def clear_history(self) -> None:
        """丢弃当前对象内的所有历史消息。"""
        self.chat_history = []

    def get_history(self) -> List[Any]:
        """返回内部历史列表（调试或序列化前可读）。"""
        return self.chat_history


def create_basic_agent(model: str = "qwen3:8b", temperature: float = 0) -> AgentSkill:
    """工厂：最简配置 + ``DEFAULT_TOOLS``。"""
    return AgentSkill(
        model=model,
        temperature=temperature,
        tools=list(DEFAULT_TOOLS),
        verbose=True,
    )


def create_advanced_agent(
    model: str = "qwen3:8b",
    temperature: float = 0,
    system_prompt: Optional[str] = None,
) -> AgentSkill:
    """工厂：附带 ``weather``、``remember`` 等扩展工具。"""
    return AgentSkill(
        model=model,
        temperature=temperature,
        tools=list(EXTENDED_TOOLS),
        system_prompt=system_prompt,
        verbose=True,
    )


def create_custom_agent(
    model: str = "qwen3:8b",
    tools: Optional[List[BaseTool]] = None,
    system_prompt: str = "你是一个专业的AI助手",
) -> AgentSkill:
    """工厂：自定义工具集与系统提示。"""
    return AgentSkill(
        model=model,
        tools=list(tools or DEFAULT_TOOLS),
        system_prompt=system_prompt,
        verbose=True,
    )


def agent_skill(name: str, description: str):
    """
    装饰器工厂：给 ``@tool`` 再挂 ``skill_name`` / ``skill_description`` 属性（高级用法）。

    学习说明：
    - 内层 ``@wraps(func)`` 保留被装饰函数的元数据（函数名、docstring）。
    - 最外层返回 ``decorator``，因此用法是 ``@agent_skill("名称", "描述")``。
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @tool
        def wrapper(*args: Any, **kwargs: Any):
            return func(*args, **kwargs)

        wrapper.skill_name = name
        wrapper.skill_description = description
        return wrapper

    return decorator
