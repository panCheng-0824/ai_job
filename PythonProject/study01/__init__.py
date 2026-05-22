"""
study01 学习包：从 Agent（day1~day4）到 Milvus 向量库（day5），再到 LLM+检索（day6）。

模块速览（建议按顺序打开阅读）
----------------------------
- ``llm.py``：统一创建聊天模型（默认接 Ollama OpenAI 兼容口）。
- ``tools.py``：LangChain ``@tool`` 工具定义与工具列表。
- ``persona_agent.py``：带人设占位符的 ``AgentExecutor``（day1/day2）。
- ``agent_skill.py``：``AgentSkill`` 封装与工厂函数（day3）。
- ``day1.py`` ~ ``day4_*``：可运行的渐进示例。
- ``day5.py``：Milvus CRUD 与嵌入检索（注释最细，适合啃概念）。
- ``day6.py``：文本清洗入库 + 子问题多路检索（学习型长注释）。

本包不设 ``__all__``：请从具体 ``dayN`` 或子模块显式 import，避免初学者被星号导入隐藏依赖。
"""
