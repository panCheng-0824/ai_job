"""
================================================================================
LangChain 工具（@tool）与工具列表
================================================================================

什么是 Tool？
------------
- 在 LangChain / Agent 语境里，**工具**是「带名字、描述、参数结构」的**可调用函数**。
- 大模型通过 **Function Calling**（函数调用）决定「要不要调、调哪个、传什么参数」；
  框架负责真正执行 Python 函数并把结果塞回对话。

为什么集中写在本文件？
----------------------
- Day1 演示、Day3 ``AgentSkill``、Day4 MCP Demo 都从这里 ``import``，
  避免 ``search`` / ``calculate`` 在多处复制粘贴、改一处漏一处。

学习扩展
--------
- 想加新能力：写一个普通函数，加上 ``@tool``，再把函数对象放进 ``DEFAULT_TOOLS`` 列表即可。
- 读 LangChain 文档关键词：``StructuredTool``、``@tool``、``bind_tools``。
"""

from langchain_core.tools import tool


@tool(description="搜索信息工具。输入检索关键词，返回匹配到的文本结果摘要。")
def search(query: str) -> str:
    """
    搜索信息工具 —— Agent 的「眼睛」（本 Demo 为假数据）。

    ``@tool`` 装饰器会做几件事（概念层面）：
    - 从函数签名推断参数名与类型，生成给模型看的 JSON Schema。
    - 把 ``docstring`` 当作工具描述，帮助模型判断何时调用。

    Args:
        query: 用户或模型给出的检索关键词。

    Returns:
        固定格式的演示字符串；真实项目里可换 HTTP 请求搜索引擎/内部 API。
    """
    return f"搜索结果：关于 '{query}' 的信息"


@tool(description="数学计算工具。输入算术表达式字符串，返回计算结果或错误信息。")
def calculate(expression: str) -> str:
    """
    数学计算工具 —— 演示用。

    ⚠️ 安全警告（写给初学者）：
    - ``eval()`` 会执行任意 Python 表达式。**永远不要**对不可信用户输入在生产环境使用。
    - 正确做法：用 ``ast`` 限制允许的节点、或专用数学库解析表达式。

    Args:
        expression: 类似 ``(10+5)*2`` 的算术表达式字符串。

    Returns:
        计算结果或错误信息字符串。
    """
    try:
        result = eval(expression)
        return f"计算结果：{result}"
    except Exception as e:
        return f"计算错误：{str(e)}"


@tool(description="天气查询工具。输入城市名，返回该城市的天气信息（示例为模拟数据）。")
def weather(city: str) -> str:
    """天气查询工具 —— 扩展示例，返回模拟数据，便于观察「多工具」行为。"""
    return f"{city}今天天气：晴，温度 20°C"


@tool(description="记忆存储工具。输入键和值，返回写入确认信息（示例不做持久化）。")
def remember(key: str, value: str) -> str:
    """
    记忆存储工具 —— 扩展示例（并未真正持久化到数据库）。

    用途：演示 Agent 可以调用「写操作」类工具；与 Day3 ``EXTENDED_TOOLS`` 搭配。
    """
    return f"已记住：{key} = {value}"


# 默认给「基础 Agent」用的最短工具集（Day1 / Day4 等）。
DEFAULT_TOOLS = [search, calculate]

# 进阶示例：更多工具，用于 ``create_advanced_agent`` 等。
EXTENDED_TOOLS = [search, calculate, weather, remember]
