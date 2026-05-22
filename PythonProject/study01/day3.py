"""
================================================================================
Agent 学习 Demo —— Day 3：Skills（技能）与模块导出
================================================================================

Day3 在代码结构上做了什么事？
-----------------------------
- **实现**主要在 ``study01/agent_skill.py``（``AgentSkill`` 类、各种 ``create_*_agent``）。
- **本文件（day3.py）** 作为「课程入口」：把符号再 ``export`` 出去，这样你可以写::

      from study01.day3 import AgentSkill, DEFAULT_TOOLS

  而无需记住实现到底在哪个模块 —— 这叫 **facade（门面）**，利于学习路径统一。

Skills（技能）直观理解
----------------------
- 把 Agent 的一整套配置封装成「可插拔组件」：换工具集、换系统提示、换模型，都像换技能皮肤。
- 与游戏中技能类比：不同技能（基础/高级）共用同一套「施法框架」（LangChain AgentExecutor）。

``__all__`` 是什么？
--------------------
- 列出 ``from study01.day3 import *`` 时会导入的名字；也明确**公共 API** 边界，便于阅读。

下一步
------
- 运行本文件 ``if __name__ == "__main__"`` 里的测试块，对照 ``agent_skill.py`` 里 ``run`` 的实现。
"""

# 从共享实现导入，保持对外 API 不变（门面层）。
from study01.agent_skill import (
    AgentSkill,
    agent_skill,
    create_advanced_agent,
    create_basic_agent,
    create_custom_agent,
)
from study01.tools import DEFAULT_TOOLS, EXTENDED_TOOLS, calculate, remember, search, weather

__all__ = [
    "AgentSkill",
    "DEFAULT_TOOLS",
    "EXTENDED_TOOLS",
    "agent_skill",
    "calculate",
    "create_advanced_agent",
    "create_basic_agent",
    "create_custom_agent",
    "remember",
    "search",
    "weather",
]

# ============================================
# 使用示例和测试（直接运行本文件时执行）
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Agent Skills 测试")
    print("=" * 60)

    print("\n【测试 1】创建并使用基础 Agent")
    print("-" * 40)
    basic_agent = create_basic_agent()
    result1 = basic_agent.run("你好，请介绍一下自己")
    print(f"回答：{result1}")

    print("\n【测试 2】使用计算工具")
    print("-" * 40)
    result2 = basic_agent.run("计算 (10+5) * 2 的结果")
    print(f"回答：{result2}")

    print("\n【测试 3】创建并使用高级 Agent")
    print("-" * 40)
    advanced_agent = create_advanced_agent(system_prompt="你是一个幽默风趣的助手")
    result3 = advanced_agent.run("今天天气怎么样？")
    print(f"回答：{result3}")

    print("\n【测试 4】使用 AgentSkill 类")
    print("-" * 40)
    skill = AgentSkill(
        model="qwen3:8b",
        tools=list(EXTENDED_TOOLS),
        system_prompt="你是一个文学专家",
        verbose=False,
    )
    result4 = skill.run("用夏天写一首诗")
    print(f"回答：{result4}")

    print("\n【测试 5】测试对话历史记忆")
    print("-" * 40)
    skill.run("请记住我的名字是小明")
    result5 = skill.run("你知道我的名字是什么吗？")
    print(f"回答：{result5}")

    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
