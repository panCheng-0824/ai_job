---
name: skilldemo
description: 用于指导 study01 学习代码的运行、讲解与排错（LangChain Agent、FastAPI、Skills、MCP 风格 API、RAG 流程）。当用户提出学习、演示、调试或练习 study01 相关文件时使用。
---

# study01 学习技能示例

## 适用范围

本技能用于当前项目 `study01/` 下的学习代码：
- `day1.py`：基础 Agent 运行
- `day4_fastapi_skills_mcp_demo.py`：FastAPI + Skills + MCP 风格接口
- `day6.py`：RAG 入库与查询流程
- `tools.py` 与 `llm.py`：通用工具与模型配置

## 触发场景

当用户请求包含以下内容时，启用本技能：
- "学习代码", "study01", "day1/day4/day6"
- 运行 demo、讲解流程、排查启动或运行时报错
- 验证本地 API 接口（`/docs`、`/chat`、`/mcp`）
- 对比 Agent 自动工具调用与显式工具调用的区别

## 默认工作流

1. 先确认目标脚本和任务目标（运行、讲解、排错或扩展）。
2. 按项目文档检查运行前提：
   - Python 虚拟环境可用
   - `study01/llm.py` 中模型端点可访问
   - 仅在目标脚本需要时再检查 Redis、Milvus、Ollama 等外部服务
3. 执行最小可复现命令。
4. 用学习友好的结构输出结果：
   - 执行了什么
   - 出现了什么现象
   - 原因是什么
   - 下一步做什么

## 常用命令

在项目根目录执行：

```bash
# day1：终端 Agent 演示
python -m study01.day1

# day4：FastAPI + Skills + MCP 风格 API
python -m study01.day4_fastapi_skills_mcp_demo

# day6：入库与查询
python -m study01.day6 ingest --text "测试文本" --reset
python -m study01.day6 query "测试问题"
```

## 排错规则

- 若模型连接失败，优先检查 `study01/llm.py` 中 `model` 与 `base_url`。
- 若 `day4` 接口异常，先确认 Redis 服务与相关环境变量是否可用。
- 若 `day6` 失败，先分类定位：
  - embedding 或模型调用问题
  - Milvus 连接或 schema 问题
  - 入库/查询流程逻辑问题
- 优先采用小步、可复现的验证方式，避免一次性大改。

## 讲解输出模板

讲解时优先按以下结构输出：

```markdown
目标：<本次学习目标>
执行：<运行的命令>
现象：<关键输出或报错>
原因：<对应代码机制>
下一步：<1个最小可执行动作>
```

## 约束

- 未经用户要求，不修改 `study01/` 之外的无关文件。
- 不泄露、展示或硬编码真实密钥。
- 示例保持最小可运行，优先适配本地环境。
