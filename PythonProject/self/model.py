"""根据 modelCfg 创建对话客户端；本环节不挂载 Tool / AgentExecutor。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, List, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

_SELF_DIR = Path(__file__).resolve().parent
if str(_SELF_DIR) not in sys.path:
    sys.path.insert(0, str(_SELF_DIR))

from modelCfg import ModelConfig, model_list

_DEFAULT_SYSTEM_PROMPT = """你是一个专业的AI助手。请始终用中文回复。"""


class CfgAgent:
    """由配置文件驱动的对话封装（仅 LLM + 多轮历史，无工具调用）。"""

    def __init__(
        self,
        cfg: ModelConfig,
        *,
        temperature: float = 0,
        system_prompt: Optional[str] = None,
        **_ignored: Any,
    ):
        self.cfg = cfg
        self.model = cfg.model_name
        self.base_url = cfg.model_api
        self.api_key = cfg.model_key
        self.temperature = temperature
        self.chat_history: List[Any] = []

        self.llm = ChatOpenAI(
            model=cfg.model_name,
            temperature=temperature,
            base_url=cfg.model_api,
            api_key=cfg.model_key,
        )
        self.system_prompt = system_prompt if system_prompt is not None else _DEFAULT_SYSTEM_PROMPT
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )
        self.chain = self.prompt | self.llm | StrOutputParser()

    def run(self, input_text: str, clear_history: bool = False) -> str:
        if clear_history:
            self.chat_history = []
        output = self.chain.invoke(
            {"input": input_text, "chat_history": self.chat_history}
        )
        self.chat_history.append(HumanMessage(content=input_text))
        self.chat_history.append(AIMessage(content=output))
        return output

    def chat(self, input_text: str) -> str:
        return self.run(input_text)

    def clear_history(self) -> None:
        self.chat_history = []

    def get_history(self) -> List[Any]:
        return self.chat_history


def create_agent(cfg: ModelConfig, **kwargs: Any) -> CfgAgent:
    """使用单条 ``ModelConfig`` 构造 ``CfgAgent``。"""
    return CfgAgent(cfg, **kwargs)


def agents_by_level() -> dict[str, CfgAgent]:
    """每条配置按其 ``model_level`` 对应一个实例。"""
    return {cfg.model_level: CfgAgent(cfg) for cfg in model_list}


def get_agent(level: str, **kwargs: Any) -> CfgAgent:
    """按 ``model_level`` 取配置并创建；不存在则 ``KeyError``。"""
    for cfg in model_list:
        if cfg.model_level == level:
            return CfgAgent(cfg, **kwargs)
    raise KeyError(
        f"未知 model_level: {level!r}，可选: {[c.model_level for c in model_list]}"
    )
