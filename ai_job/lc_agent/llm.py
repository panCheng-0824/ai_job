"""
语言模型构造（仅负责 ``ModelEntry`` → ``ChatOpenAI``）。

职责边界：
- 只封装 **OpenAI 兼容** Chat 接口需要哪些字段（model / api_key / base_url）；
- 不负责加载 ``modelCfg.json``、不负责选档位；调用方传入已选好的 ``ModelEntry``。

解耦收益：更换为其它 ``BaseChatModel`` 实现时，可在此处集中替换，而不影响工具、Prompt 与 Agent 工厂代码。
"""

from typing import Any

from langchain_openai import ChatOpenAI

from model_cfg import ModelEntry


def chat_model_from_entry(entry: ModelEntry, **kwargs: Any) -> ChatOpenAI:
    """
    将一条 ``ModelEntry`` 映射为 ``langchain_openai.ChatOpenAI`` 实例。

    ``ModelEntry`` 与 OpenAI SDK 字段对应关系：
    - ``model_name``  → ``model``：服务端路由到具体权重；
    - ``model_key``   → ``api_key``：鉴权（本地服务常填占位字符串）；
    - ``model_api``   → ``base_url``：OpenAI 兼容 Base URL（通常以 ``/v1`` 结尾）。

    额外参数 ``**kwargs`` 会原样传给 ``ChatOpenAI``，常见项包括：
    - ``temperature``、``max_tokens``、``timeout`` 等。

    注意：工具调用型 Agent 需要底层实现 ``bind_tools``；``ChatOpenAI`` 满足该要求。
    """
    return ChatOpenAI(
        model=entry["model_name"],
        api_key=entry["model_key"],
        base_url=entry["model_api"],
        **kwargs,
    )
