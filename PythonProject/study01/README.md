# study01 学习说明

本目录是一套**循序渐进**的示例代码：从 LangChain **Agent**（工具调用、FastAPI 暴露接口、Skills 封装、MCP 风格协议），到 **Milvus 向量库**，再到 **大模型 + 嵌入 + 多路子问题检索**（RAG 流水线雏形）。

---

## 推荐阅读顺序

| 顺序 | 文件 | 内容概要 |
|------|------|----------|
| 1 | `llm.py` | 统一创建聊天模型（默认对接本机 Ollama 的 OpenAI 兼容接口）。 |
| 2 | `tools.py` | `@tool` 定义工具（search、calculate 等）及工具列表。 |
| 3 | `persona_agent.py` | 带人设占位符的 Prompt + `AgentExecutor`（供 Day1/Day2）。 |
| 4 | `day1.py` | 终端里跑 Agent：`invoke` 与多轮 `chat_history`。 |
| 5 | `day2.py` | 用 FastAPI 把同一套 Agent 暴露为 HTTP API（默认端口 8000）。 |
| 6 | `agent_skill.py` | `AgentSkill` 类：内置历史、固定系统提示。 |
| 7 | `day3.py` | 门面导出：从本文件 `import AgentSkill` 等，并含自测 `main`。 |
| 8 | `day4_fastapi_skills_mcp_demo.py` | FastAPI + Skills；显式调工具；极简 JSON-RPC 风格 MCP（端口 **8001**）。 |
| 9 | `day5.py` | Milvus 建表、CRUD、Ollama 嵌入、自然语言语义检索（注释最细）。 |
| 10 | `day6.py` | LLM 清洗文本 → 分块 → 嵌入 → 入库；查询时 LLM 拆子问题 → 多路向量检索。 |

---

## 目录结构（核心文件）

```
study01/
├── README.md                      # 本说明
├── __init__.py                    # 包简介（docstring）
├── llm.py                         # ChatOpenAI 工厂
├── tools.py                       # LangChain 工具定义
├── persona_agent.py               # 人设版 AgentExecutor
├── agent_skill.py                 # AgentSkill 与工厂函数
├── day1.py                        # Agent 入门（脚本）
├── day2.py                        # FastAPI + Agent（8000）
├── day3.py                        # Skills 门面 + 测试
├── day4_fastapi_skills_mcp_demo.py # 综合 HTTP + MCP 风格（8001）
├── day5.py                        # Milvus + 嵌入
└── day6.py                        # LLM + 向量库 RAG Demo
```

---

## 环境与前置条件

### 通用（Agent 相关）

- Python 3.9+（与当前项目虚拟环境一致即可）。
- 已安装：`langchain`、`langchain-openai`、`langchain-core`、`fastapi`、`uvicorn`、`pydantic` 等（以你本地 `pip` 为准）。
- **Ollama**：`ollama serve`，并拉取与 `llm.py` / 各 `day` 中 `create_llm("模型名")` **一致**的聊天模型。

### Day5 / Day6（向量）

- **Milvus**（常见为 Docker 启动），默认 `127.0.0.1:19530`。
- **Ollama 嵌入模型**：例如 `ollama pull nomic-embed-text`（维度需与集合 `dim` 一致，常见 768）。
- Python：`pymilvus`、`langchain-ollama`。

---

## 运行方式速查

在项目根目录（`PythonProject`）执行，例如：

```bash
# Day1：终端对话实验
python -m study01.day1

# Day2：API 服务（浏览器打开 http://localhost:8000/docs）
python -m study01.day2

# Day3：Skills 自测
python -m study01.day3

# Day4：综合 Demo（8001）
python -m study01.day4_fastapi_skills_mcp_demo

# Day5：默认语义演示（需 Milvus + Ollama 嵌入）
python -m study01.day5
# 仅随机向量学 Milvus API（无需 Ollama 嵌入）
python -m study01.day5 --legacy-random

# Day6：入库 / 查询
python -m study01.day6 ingest --text "你的长文本" --reset
python -m study01.day6 ingest --file ./某文件.txt --source 文件名 --reset
python -m study01.day6 query "你的问题"
```

---

## 重要概念对照（便于初学者）

| 概念 | 在本仓库中的体现 |
|------|------------------|
| **Tool / 工具** | `tools.py` 中 `@tool`；模型通过 Function Calling 决定调用与否。 |
| **AgentExecutor** | `persona_agent.py` / `agent_skill.py`：模型与工具多轮循环直到最终回复。 |
| **人设 Prompt** | `persona_agent.py`：`{agent_name}`、`{role}` 等由 `invoke` 传入。 |
| **AgentSkill** | `agent_skill.py`：系统提示相对固定，历史挂在对象上。 |
| **Collection / 向量检索** | `day5.py`、`day6.py`：Milvus 表、嵌入、`search`。 |
| **RAG 雏形** | `day6.py`：清洗 → chunk → embed → 存库；查询侧子问题多路召回。 |

---

## 环境变量（节选）

| 变量 | 作用 |
|------|------|
| `MILVUS_HOST` / `MILVUS_PORT` | Milvus 地址与端口。 |
| `MILVUS_COLLECTION` | Day5 集合名（默认见 `day5.py`）。 |
| `MILVUS_COLLECTION_DAY6` | Day6 集合名（默认 `study01_day6_rag`）。 |
| `OLLAMA_BASE_URL` / `OLLAMA_EMBED_MODEL` | Ollama 与嵌入模型名。 |

具体默认值以各文件中的 `os.environ.get` 为准。

---

## 安全与练习提示

- `tools.py` 中 `calculate` 使用 `eval`，**仅用于本地演示**，不可对不可信输入用于生产。
- Day2 / Day4 使用**内存**保存会话，进程重启即丢失；生产请使用 Redis、数据库等。
- Day6 的 LLM 清洗、子问题拆分依赖模型输出格式，代码中已含简单兜底（如 JSON 解析失败则退回单问题）。

---

## 扩展学习方向

- 为 Day6 增加「检索结果 → 再调用 LLM 生成最终答案」的完整 RAG 回答链。
- 将 Day2 的 `user_sessions` 换成持久化存储。
- 阅读 LangChain 官方文档：OpenAI Functions Agent、Tool、Runnable。

如有与当前代码不一致之处，以仓库内源码及注释为准。
