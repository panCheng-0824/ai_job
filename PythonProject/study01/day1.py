"""
================================================================================
Agent 学习 Demo —— Day 1：最小 Agent 长什么样？
================================================================================

Agent（智能体）在本 Demo 里的三部分
----------------------------------
1. **LLM**：大语言模型，负责「下一步说什么、要不要调工具」。
2. **Tools**：普通 Python 函数 + ``@tool``，对外暴露为可调用的「能力」。
3. **AgentExecutor**：执行器，按 LangChain 约定循环：模型 ⇄ 工具，直到得到最终回复。

代码放在哪些文件里？（本文件只负责「拼起来」）
---------------------------------------------
- ``study01/llm.py``：创建聊天模型 ``ChatOpenAI``。
- ``study01/tools.py``：``search``、``calculate`` 等工具定义。
- ``study01/persona_agent.py``：``create_persona_agent_executor``，内部调用
  ``create_openai_functions_agent`` + ``AgentExecutor``。

建议你怎么学
------------
1. 先通读本文件 ``if __name__ == "__main__"``，看 ``invoke`` 传了哪些键。
2. 打开 ``persona_agent.py`` 对照 prompt 里的 ``{agent_name}`` 等变量。
3. 把 ``verbose=True``（在 ``create_persona_agent_executor``）打开，观察终端里的工具调用轨迹。

前置：本机 Ollama 已运行，且已拉取你在 ``create_llm(...)`` 里写的模型。
"""

# ============================================
# 第一步：导入必要的库
# ============================================
from langchain_core.messages import AIMessage, HumanMessage

from study01.llm import create_llm,create_omlx_llm
from study01.persona_agent import create_persona_agent_executor
from study01.tools import DEFAULT_TOOLS as tools
from study01.tools import calculate, search

# ============================================
# 第二步：初始化 LLM（大语言模型）
# ============================================
# 方式一：使用 OpenAI 官方 API —— 在 study01/llm.py 的 create_llm 里改默认参数。
# 方式二：本地 Ollama（OpenAI 兼容）：先运行 ollama serve，模型名与 ollama list 一致。

llm = create_omlx_llm(api_key='pc0824tq')

# ============================================
# 第三步：Tools（工具）
# ============================================
# 工具定义在 study01/tools.py；这里的 search、calculate 与上面 tools 列表里是同一组对象，
# 单独 import 只是为了你在交互式解释器里方便 ``search.invoke(...)`` 做实验。

# ============================================
# 第四步 & 第五步：Agent + AgentExecutor
# ============================================
# create_openai_functions_agent 等在 persona_agent 内完成封装。
agent_executor = create_persona_agent_executor(llm=llm, tools=tools)


def print_history(chat_history):
    """
    把 LangChain 消息列表打印成人可读格式。

    Args:
        chat_history: 元素多为 ``HumanMessage`` / ``AIMessage``；用 ``isinstance`` 分支处理。
    """
    print("\n📜 对话历史：")
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            print(f"[用户] {msg.content}")
        elif isinstance(msg, AIMessage):
            print(f"[小潼] {msg.content}")
        else:
            print(f"[{msg.type}] {msg.content}")


if __name__ == "__main__":
    # 在内存里维护多轮对话；注意这是「脚本级全局」，重启进程历史会丢。
    chat_history = []

    def chat(input_text):
        """
        调一次 Agent，并把本轮问答追加进 chat_history。

        invoke 的字典键必须与 ChatPromptTemplate 中变量名一致（见 persona_agent）。
        """
        result = agent_executor.invoke(
            {
                "agent_name": "小潼",
                "personality": "你说话的语气特别温柔",
                "language": "中文",
                "role": "文学专家",
                "input": input_text,
                "chat_history": chat_history,
                "agent_scratchpad": [],
            }
        )
        chat_history.append(HumanMessage(content=input_text))
        chat_history.append(AIMessage(content=result["output"]))
        return result["output"]

    print("=" * 50)
    print("测试 1：叫什么名字")
    print("=" * 50)
    result1 = chat("你叫什么名字")
    print(f"最终回答：{result1}")

    print("=" * 50)
    print("测试 2：有哪些工具")
    print("=" * 50)
    result2 = chat("你现在有哪些工具可以调用")
    print(f"最终回答：{result2}")

    print("=" * 50)
    print("测试 3：有哪些工具")
    print("=" * 50)
    result3 = chat("帮我用春天写一首诗")
    print(f"最终回答：{result3}")

    print_history(chat_history)


def create_agent():
    """
    返回与模块级相同的 ``AgentExecutor`` 单例，供 Day2 等模块复用。

    Returns:
        已配置好的 ``AgentExecutor``（与文件顶部 ``agent_executor`` 是同一对象）。

    学习提示：
    - 「单例」在演示里省事；生产环境通常按请求/用户创建或从池里取，避免状态串线。
    """
    return agent_executor
