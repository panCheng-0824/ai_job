# ai_search

AI 驱动智能网页采集（**核心编排模块**）。`ocr`、`online_search` 仅提供 OCR 与 Scrapy 基础能力。

## 快速开始

在 `ai_job` 目录下：

```bash
pip install -r requirements.txt

# 公开页 HTTP 采集
python -m ai_search --url "https://example.com" --mode scrapy --prompt "提取页面标题和主要段落"

# 需登录：有头浏览器人工登录 → 导出 session → Scrapy 批量采集
python -m ai_search \
  --url "https://your-site.com/list" \
  --mode hybrid \
  --require-login true \
  --prompt "提取列表中的标题和链接" \
  --follow-links true \
  --max-pages 5

# 强动态单页
python -m ai_search --url "https://example.com/app" --mode drission --prompt "提取表格数据"
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `AI_SEARCH_MODEL_LEVEL` | LLM 档位，默认 `mid`（与 `config/modelCfg.json` 对齐） |
| `AI_SEARCH_MODEL_NAME` / `API` / `KEY` | 三项均设置时覆盖 JSON 配置 |
| CLI `--model-level` | 单次任务指定档位 |

LLM 与项目其他模块一致，通过 `modelCfg.json` + `lc_agent.chat_model_from_entry` 构造 OpenAI 兼容客户端。模型不可用时，采集仍可进行，LLM 字段解析会降级。

## 运行日志

关键步骤会输出结构化 STEP 日志（风格对齐 `online_search`）：

| 标签 | 含义 |
|------|------|
| `[INIT]` | 任务/Spider 初始化 |
| `[STEP N]` | 主编排步骤（orchestrator） |
| `[STEP N.M]` | 子步骤（登录、Scrapy、LLM 等） |
| `[BROWSER]` / `[SCRAPY]` / `[LLM]` / `[SESSION]` / `[OUTPUT]` | 子模块阶段日志 |
| `[DONE]` | 任务或 Spider 结束 |
| `[STEP ERROR]` / `[WARN …]` | 异常与降级 |

示例：

```
[INIT] 采集任务启动: url=https://example.com, mode=scrapy, ...
[STEP 1] 检查本地会话状态: has_cached_session=False, ...
[STEP 2] 执行采集: mode=scrapy
[STEP 2.scrapy-start] Scrapy 进程即将启动: start_url=...
[SCRAPY] 采集完成: pages=3, spider_pages=3
[DONE] 采集任务结束: mode=scrapy, pages=3, errors=0
```

## 目录

- `orchestrator.py` — 任务编排入口
- `browser/` — DrissionPage 有头登录与会话导出
- `scrapy_engine/` — 通用 Spider 与正文提取
- `llm/` — 模式建议、选择器、字段解析
- `captcha/` — 调用 `ocr` 的薄封装
- `sessions/` — 本地会话（已 gitignore）

详细设计见 [设计步骤.md](./设计步骤.md)。
