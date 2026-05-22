## 学习路线总览（从 Java 转 Python / Agent 框架）

你的目录 `study01/` 已经是一套「循序渐进可运行」的 demo。本 README 的目标是把它变成**关卡式学习路径**：每一关你要理解什么、跑什么、看哪些代码、输出什么结果。

---

## 你要掌握的知识地图（按依赖关系排序）

- **Python 基础（面向工程）**
  - 你需要的不是“语法大全”，而是能读懂并改得动本项目：
  - 模块与包：`study01/` 是一个包（有 `__init__.py`）
  - 类型标注：`str | int | list`、`Optional[str]`、`dict[str, Any]`（FastAPI/LangChain 大量依赖）
  - 数据类：`@dataclass`（`day7.py` 的 LangGraph 状态）
  - 依赖管理：`pip` + 虚拟环境 `.venv`

- **FastAPI（做一个“可调试的 AI 服务外壳”）**
  - 路由：`@app.get` / `@app.post`
  - 请求/响应模型：`pydantic.BaseModel`
  - 自动文档：`/docs`
  - 会话存储（学习版）：内存 dict；生产版：Redis/DB

- **LangChain（把 LLM + Prompt + Tools 组织起来）**
  - LLM 客户端：`study01/llm.py`（默认对接 Ollama 的 OpenAI 兼容口）
  - Tools：`study01/tools.py`（`@tool` 生成 schema，供 Function Calling）
  - AgentExecutor：模型 ↔ 工具 的多轮循环（`persona_agent.py`、`agent_skill.py`）

- **RAG（检索增强生成）**
  - 本仓库的 RAG 主要体现在：
    - Milvus + embedding（`day5.py`）
    - 清洗/分块/入库 + 子问题拆分多路召回（`day6.py`）

- **LangGraph（把 Agent 变成可控工作流）**
  - 节点/边/状态/分支/循环（`day7.py`）
  - 适合做：可观测、可回放、可控的生产级流程（比“纯 Agent 黑盒”更容易调试）

- **MCP（工具服务化的一种协议形态）**
  - 本仓库用“JSON-RPC 风格最小实现”对齐概念（`day4_fastapi_skills_mcp_demo.py`）
  - 你先理解：`tools/list`、`tools/call` 的语义即可

- **Harness engineering / 评测（让系统可回归、可对比、可持续迭代）**
  - 你最终需要一套：
    - 固定测试集（questions + gold answers/criteria）
    - 指标（正确性/引用命中/延迟/成本）
    - 回归脚本（每次改 prompt/检索/工具都跑一遍）

---

## 关卡式学习流程（直接对照你的代码）

### Level 0：环境确认（只做一次）

- **目标**：能跑 Python 模块、能连上本机 Ollama。
- **你要做的事**：
  - 启动 Ollama：`ollama serve`
  - 确保模型存在：`ollama list`，并与 `study01/llm.py` 的 `DEFAULT_MODEL` 一致（默认 `qwen3:4b`）

### Level 1：LLM 工厂（统一入口）

- **看代码**：`study01/llm.py`
- **你要理解**：
  - 为什么把 `model/base_url/temperature` 集中管理
  - `create_llm().invoke([...])` 的基本调用方式

### Level 2：Tools（让模型“会用外部能力”）

- **看代码**：`study01/tools.py`
- **你要理解**：
  - `@tool` 做了什么：函数 → 带描述+参数 schema 的工具
  - 为什么 `calculate` 用 `eval` 只适合本地演示（安全边界）

### Level 3：Agent（模型 ↔ 工具 的多轮循环）

- **跑 demo**：

```bash
python -m study01.day1
```

- **看代码**：`study01/day1.py`、`study01/persona_agent.py`
- **你要理解**：
  - `AgentExecutor.invoke()` 的输入输出 shape（尤其是 `chat_history`）

### Level 4：FastAPI 把 Agent 暴露成服务

- **跑 demo**：

```bash
python -m study01.day2
```

- **然后打开**：`http://localhost:8000/docs`
- **看代码**：`study01/day2.py`
- **你要理解**：
  - `BaseModel` 如何定义请求/响应
  - 内存 session 的优缺点（学习 vs 生产）

### Level 5：Skills（把“可复用能力”封装起来）

- **跑 demo**：

```bash
python -m study01.day3
```

- **看代码**：`study01/agent_skill.py`、`study01/day3.py`
- **你要理解**：
  - Skill = 固定系统提示 + 内置历史 + 工具集合
  - 什么时候该用 Skill（复用/产品化），什么时候直接用 agent（实验/探索）

### Level 6：MCP 风格（工具服务化的“协议外壳”）

- **跑 demo**：

```bash
python -m study01.day4_fastapi_skills_mcp_demo
```

- **打开**：`http://localhost:8001/docs`
- **你要理解**：
  - `/chat`（LLM 自主工具调用） vs `/tools/invoke`（你显式调用工具） vs `/mcp`（JSON-RPC 风格）

### Level 7：Milvus + embedding（RAG 的“检索”部分）

- **跑 demo**（需要 Milvus + embedding 模型）：

```bash
python -m study01.day5
```

- **看代码**：`study01/day5.py`
- **你要理解**：
  - collection/schema/vector 搜索的基本概念
  - embedding 维度与集合 dim 必须一致

### Level 8：RAG 流水线雏形（入库 + 多路召回）

- **跑 demo**：

```bash
python -m study01.day6 ingest --text "你的长文本" --reset
python -m study01.day6 query "你的问题"
```

- **看代码**：`study01/day6.py`
- **你要理解**：
  - 清洗/分块/入库
  - LLM 拆子问题 → 多路检索 → 汇总（这是走向可用 RAG 的关键）

### Level 9：LangGraph（可控工作流）

- **跑 demo**：

```bash
python -m study01.day7 simple
python -m study01.day7 with-tools
python -m study01.day7 loop
```

- **看代码**：`study01/day7.py`
- **你要理解**：
  - State（状态）如何流动
  - conditional edges 如何分支
  - loop 如何实现“像 Agent 一样的循环”，以及为什么必须有 `max_steps`

### Level 10：Harness engineering（评测/回归）

- **跑 demo**：

```bash
python -m study01.day8
```

- **看代码**：`study01/day8.py`、`study01/eval_questions_day8.jsonl`
- **你要理解**：
  - 题集（jsonl）= 可回归基准
  - 评测指标先从简单的 keyword hit 开始，后续再升级为更严谨的判分

### Level 11：端到端 RAG（生成 + 引用）

- **跑 demo**（确保你已 Day6 ingest 过）：

```bash
python -m study01.day9 "你的问题"
```

- **看代码**：`study01/day9.py`（复用 `day6.query_multi_subsearch`）
- **你要理解**：
  - 为什么要把检索结果格式化成 context
  - 为什么要强制引用格式 `[chunk_id]`（可解释、可回归）

---

## 下一步：我会在这个项目里补什么（用于你后续迭代）

- **`requirements.txt`**：把学习必需依赖列出来（不绑定你机器里的 `.venv`）
- **评测/回归骨架（harness）**：给你一个最小可用的 “questions.jsonl + pytest” 模板（后续关卡）

