"""
================================================================================
共享 LLM 配置与工厂（study01 里 Day1 / Day3 / Day6 都会用到）
================================================================================

为什么单独放一个文件？
---------------------
- **单一数据源**：模型名、API 地址、温度等只在这里改一次，其它模块调用 ``create_llm()`` 即可。
- **解耦**：业务代码不关心「底层是 OpenAI 还是 Ollama」，只拿一个 ``ChatOpenAI`` 实例。

默认对接什么？
--------------
- 使用 ``langchain_openai.ChatOpenAI``，但把 ``base_url`` 指向本机 **Ollama** 的 **OpenAI 兼容接口**
  （一般是 ``http://localhost:11434/v1``）。
- ``api_key`` 对 Ollama 往往可以是任意占位字符串（如 ``sk-ollama``），具体以 Ollama 版本为准。

改成官方 OpenAI
---------------
- 把 ``DEFAULT_BASE_URL`` 改回 ``https://api.openai.com/v1``（或你用的代理地址）。
- 把 ``DEFAULT_API_KEY`` 换成真实密钥（建议用环境变量读入，不要写死在仓库里）。
"""

import os
from typing import Optional

from langchain_openai import ChatOpenAI

# =========================
# 默认配置（可在调用时覆盖）
# =========================
# 默认模型名需与你 ``ollama pull`` 的模型一致（示例为 Qwen 系列标签，按本机实际修改）。
# 例如：你本地拉取了 ``qwen3:4b``，这里就要与之完全一致（含大小写与标签）。
DEFAULT_MODEL = "qwen3:4b"
# Ollama OpenAI 兼容 API 的根路径；注意末尾 ``/v1`` 常由客户端再拼具体路径。
# 若你在 Docker / 远程机部署 Ollama，需要改成对应主机地址（如 http://192.168.x.x:11434/v1）。
DEFAULT_BASE_URL = "http://localhost:11434/v1"
# 对本机 Ollama 来说通常是占位符，不会真的做 OpenAI 鉴权。
# 但保留该参数可以让这份代码无缝切换到真实 OpenAI/代理网关。
DEFAULT_API_KEY = os.environ.get("OLLAMA_API_KEY", "sk-ollama")
# temperature=0：输出更稳定、可复现，适合学习与调试；创意写作可调高。
# 常见区间：0~0.3（严谨问答），0.5~0.8（更发散），具体受模型实现影响。
DEFAULT_TEMPERATURE = 0

# =========================
# 本地 OMLX 默认配置（可在调用时覆盖）
# =========================
# 这里按 OpenAI 兼容接口进行调用；若你的 omlx 服务端口不同，调用时覆盖 base_url 即可。
DEFAULT_OMLX_MODEL = "gemma-4-31b-it-4bit"
DEFAULT_OMLX_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_OMLX_API_KEY = os.environ.get("OMLX_API_KEY", "sk-omlx")


def create_llm(
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    base_url: str = DEFAULT_BASE_URL,
    api_key: Optional[str] = None,
) -> ChatOpenAI:
    """
    创建 LangChain 的 ``ChatOpenAI`` 客户端。

    学习要点：
    - 返回值类型标注 ``-> ChatOpenAI``：方便 IDE 提示 ``.invoke()``、``.bind_tools()`` 等方法。
    - 所有参数都有默认值：调用 ``create_llm()`` 即可开箱即用；需要时只覆盖其中几项。

    Args:
        model: 模型名（Ollama 里与 ``ollama list`` 中名称对应）。
        temperature: 采样温度，越大回答越随机。
        base_url: OpenAI 兼容 API 地址。
        api_key: 密钥或占位符；不传时使用 ``OLLAMA_API_KEY`` 或默认占位值。

    Returns:
        已配置好的 ``ChatOpenAI`` 实例，可直接 ``llm.invoke([...])``。
    """
    # 这里统一封装 ChatOpenAI 的初始化，避免在业务模块重复写配置代码。
    # 好处：
    # 1) 配置集中管理：改模型/地址只改这一处；
    # 2) 便于测试：可在测试中传入不同参数构造不同实例；
    # 3) 便于迁移：未来切换到云端 API 时，业务层几乎无需改动。
    return ChatOpenAI(
        # model: 决定底层推理模型（能力、速度、显存占用等）。
        model=model,
        # temperature: 控制采样随机性；越高越“有创造力”，也越不稳定。
        temperature=temperature,
        # base_url: 请求发送到哪个 OpenAI 兼容服务（本机 Ollama / 代理 / 官方）。
        base_url=base_url,
        # api_key: 对 Ollama 可是占位符；对真实服务通常必须是有效密钥。
        api_key=api_key or DEFAULT_API_KEY,
    )


def create_omlx_llm(
    model: str = DEFAULT_OMLX_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    base_url: str = DEFAULT_OMLX_BASE_URL,
    api_key: Optional[str] = None,
) -> ChatOpenAI:
    """
    创建本地 OMLX 的 ``ChatOpenAI`` 客户端（OpenAI 兼容模式）。

    Args:
        model: 本地 OMLX 服务已加载/可用的模型名。
        temperature: 采样温度，越大越随机。
        base_url: OMLX 的 OpenAI 兼容接口地址（通常包含 ``/v1``）。
        api_key: 密钥或占位符；不传时使用 ``OMLX_API_KEY`` 或默认占位值。

    Returns:
        已配置好的 ``ChatOpenAI`` 实例。
    """
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        base_url=base_url,
        api_key=api_key or DEFAULT_OMLX_API_KEY,
    )
