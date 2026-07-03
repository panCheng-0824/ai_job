# 智慧就业平台 — 四层技术架构深度解析

> 适用于 PPT 讲解，按四层分层递进组织，每层覆盖核心组件、技术选型与设计亮点。

---

## 总览：四层架构全景图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    01. 业务应用层 (Application Layer)                      │
│   学生端 · 企业端 · 校方端  →  FastAPI REST + SSE + RocketMQ               │
├──────────────────────────────────────────────────────────────────────────┤
│                    02. AI 能力中台 (AI Middle Platform)                    │
│   多模型编排 · LangGraph · RAG · 知识图谱 · 语音 · OCR · 联网搜索           │
├──────────────────────────────────────────────────────────────────────────┤
│                    03. 数据底座层 (Data Foundation)                        │
│   本地 JSON 数据 · Redis 缓存 · LightRAG/GrepRAG 向量/图存储 · 文件持久化   │
├──────────────────────────────────────────────────────────────────────────┤
│                    04. 基础设施层 (Infrastructure)                         │
│   云原生 · Python 微服务 · RocketMQ 服务间通信 · 多模型 API 网关            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 01. 业务应用层 — 面向学生、企业、校方三大主体

### 1.1 角色体系设计 (7 大 AI 角色)

项目采用 **usercode → 角色注册表** 模式，每个角色是一个独立分包，通过 `role_registry.py` 统一路由：

| usercode | 角色名 | 核心职责 | 实现方式 |
|----------|--------|---------|----------|
| ROLE001 | 岗位规划师 | 岗位推荐快车道 + 职业咨询慢车道 | LangGraph Plan-and-Execute |
| ROLE002 | 心理咨询师 | 心理疏导、情绪支持 | LLM 直连 |
| ROLE003 | 贴心辅导员 | 学业生活指导 | LLM 直连 |
| ROLE004 | 简历优化师 | 简历解析、优化、模板 | LangGraph + OCR 联动 |
| ROLE005 | 模拟面试官 | 多阶段模拟面试（规划→出题→追问→评测） | LangGraph 复杂图 + MQ |
| ROLE006 | 制度咨询师 | 学校制度/政策问答 | LLM 直连 |
| ROLE007 | 测试机器人 | 默认回退角色 | LLM 直连 |

**关键文件：**
- [role_registry.py](app/session/stream/role_registry.py) — 角色注册表
- [role001/graph.py](app/session/role/role001/graph.py) — 岗位规划状态图
- [role005/graph/](app/session/role/role005/graph/) — 模拟面试状态图

### 1.2 核心业务模块

#### 学生端
- **智能对话** — SSE 流式对话，支持多角色切换、历史管理、取消生成
- **岗位推荐** — 查询改写 → 知识库检索 → LLM 分析 → 评分过滤 → 个性化推荐
- **模拟面试** — 行业分类 → 大纲规划 → 逐题提问 → 追问澄清 → 多题型评测 → 阶段转换
- **简历解析** — PaddleOCR 图片/PDF/Word 文档识别 → 多源合并
- **语音交互** — ASR 语音转文字 (上传录音) + TTS 文字转语音 (流式输出)

**关键文件：**
- [web_app.py](web_app.py) — API 网关（50+ 个端点）
- [chat_stream_service.py](app/portal/chat_stream_service.py) — 流式对话入口
- [job_info/pipeline.py](app/skills/job_info/pipeline.py) — 岗位推荐完整流水线

#### 企业端
- **岗位数据管理** — 企业信息、岗位发布、JD 文本管理
- **LightRAG 增量同步** — 岗位 JD 入库 → 图文抽取 → 向量化 → 知识图谱关联

#### 校方端
- **学生档案管理** — Redis 存储学生基本信息+奖励信息，注入系统提示增强个性化
- **数据搜索** — 跨学生/岗位/企业关键词检索

**关键文件：**
- [data_catalog.py](app/portal/data_catalog.py) — 本地数据目录
- [student_redis.py](app/student_redis.py) — 学生画像 Redis 读取

### 1.3 流式交互架构 (SSE)

两条 SSE 路径：
1. **openai_direct** — 直接透传 OpenAI 兼容 API 的 token 流
2. **by_model** — 按 usercode 注册表分发到各角色 LangGraph 流

支持 thinking/content 分离输出、结构化事件 (job_recommend / resume_render / interview_*) 统一转发。

**关键文件：**
- [chat_stream_pipeline.py](app/session/chat_stream_pipeline.py) — SSE 兼容入口
- [stream/token_forward.py](app/session/stream/token_forward.py) — structured event 统一转发

---

## 02. AI 能力中台 — 整合大模型、知识图谱、RAG、智能推荐

### 2.1 多模型编排引擎 (model_cfg + lc_agent)

**模型配置中心** → `config/modelCfg.json` 管理全部模型 (chat / embedding / tts / asr)

```
model_type | model_level | model_provider | model_name | model_api | model_key
-----------|-------------|----------------|------------|-----------|----------
chat       | low         | deepseek       | v4-pro     | http://... | sk-...
chat       | mid         | openai         | gpt-4o     | http://... | sk-...
embedding  | mid         | openai         | text-3-lg  | http://... | sk-...
tts        | mid         | openai         | tts-1      | http://... | sk-...
asr        | mid         | openai         | whisper-1  | http://... | sk-...
```

**LangChain Agent 工厂** (`lc_agent/factory.py`) 统一组装：配置 → LLM → 工具 → Prompt → AgentExecutor

**关键文件：**
- [model_cfg.py](model_cfg.py) — 模型配置加载与校验
- [lc_agent/factory.py](lc_agent/factory.py) — Agent 组装工厂
- [lc_agent/selection.py](lc_agent/selection.py) — 模型选择策略（type + level 逐级回退）

### 2.2 双 RAG 架构 (LightRAG + GrepRAG)

| 维度 | LightRAG (生产级) | GrepRAG (轻量级) |
|------|-------------------|-------------------|
| 底层引擎 | lightrag-hku (图+向量双存储) | 本地文本正则匹配 |
| 存储 | Neo4j / Milvus / 文件 | 内存 dict + JSON |
| 特点 | 实体抽取、关系图谱、mix/local/global/hybrid 四模式 | 快速部署、零依赖 |
| 适用场景 | 岗位推荐、面试题库、文档问答 | Agent 工具 Markdown 检索 |
| 文档管理 | 写入→异步处理→终态轮询→积压清理 | 即时写入/检索 |

**关键文件：**
- [lightrag/service.py](app/rag/lightrag/service.py) — 单例服务、全生命周期管理
- [lightrag/router.py](app/rag/lightrag/router.py) — REST API（insert / query / 图谱 CRUD / 积压管理）
- [greprag/service.py](app/rag/greprag/service.py) — 轻量检索实现

### 2.3 语义缓存系统

解决岗位推荐场景中「相似问法重复走完整链路」的成本问题：

```
请求 → 精确缓存(rag_q SHA256) → 语义缓存(全维 embedding 余弦相似度) → 完整链路
        命中: 直接返回                 命中: threshold≥0.94 直接返回      未命中: 走完链路并写入缓存
```

- 基于 Redis 的 scope 分桶隔离 (不同引擎/KB版本/推荐参数互不干扰)
- LRU 淘汰 + TTL 过期
- 全维向量余弦相似度 (不低于 0.94 阈值)

**关键文件：**
- [semantic_cache.py](app/skills/job_info/semantic_cache.py) — 语义缓存完整实现

### 2.4 知识图谱 (LightRAG 图引擎)

基于 LightRAG 的图存储，提供：
- 实体 CRUD (create / get / update / delete entity)
- 关系 CRUD (create / get / update / delete relation)
- 岗位-企业-技能-城市等知识图谱关联

### 2.5 智能采集 (AI Search)

多模式智能网页采集引擎：

| 模式 | 说明 |
|------|------|
| AUTO | LLM 自动决策 Drission/Scrapy |
| SCRAPY | 全站爬取 (Scrapy + cookie 复用) |
| DRISSION | 单页渲染 (DrissionPage 浏览器引擎) |
| HYBRID | 混合模式 (须交互登录) |

核心链路：**URL → 会话管理/人工登录 → Scrapy/Drission 采集 → LLM 字段 enrichment → JSON 输出**

**关键文件：**
- [ai_search/orchestrator.py](ai_search/orchestrator.py) — 采集任务编排
- [ai_search/llm/mode_advisor.py](ai_search/llm/mode_advisor.py) — LLM 模式决策
- [ai_search/llm/parse_agent.py](ai_search/llm/parse_agent.py) — LLM 字段抽取

### 2.6 语音能力 (ASR + TTS)

- **ASR**: 上传音频 → OpenAI 兼容 `/audio/transcriptions` → 兼容多种响应格式 (plain/segment/JSON)
- **TTS**: 文本 → OpenAI 兼容 `/audio/ speech` → 支持流式 + 非流式
- **口语摘要**: 面试/咨询长回答 → LLM 压缩为口语短文本 → TTS 朗读

**关键文件：**
- [voice/openai_audio.py](app/voice/openai_audio.py) — 音频核心服务
- [voice/spoken_summary.py](app/voice/spoken_summary.py) — 口语摘要

### 2.7 OCR 能力 (PaddleOCR)

- 支持图片 + PDF + Word 文档识别
- 多版本 PaddleOCR API 兼容 (旧版 cls 参数 + 新版 batch 结果)
- 验证码桥接 (供 ai_search 使用)

**关键文件：**
- [ocr/core.py](ocr/core.py) — OCR 核心引擎

### 2.8 LangGraph 状态图设计 (复杂推理引擎)

**ROLE001 岗位规划师图：**
```
intent_router ─┬─ job_recommend (快车道) ────────────→ END
               └─ planner (慢车道) → executor ⇄ executor
                    → structured_return | plain_finalize → END
```

**ROLE005 模拟面试官双图架构：**
- **PlannerGraph**: 行业分类 → 考题规划 → 大纲入库 → MQ 消息
- **InterviewGraph**: 自我介绍 → 逐题提问/追问/提示/澄清/评测 → 阶段转换 → 最终总结

**关键文件：**
- [role001/graph.py](app/session/role/role001/graph.py) — 规划师状态图
- [role005/graph/planner_graph.py](app/session/role/role005/graph/planner_graph.py) — 面试规划图
- [role005/graph/interview_graph.py](app/session/role/role005/graph/interview_graph.py) — 面试执行图

---

## 03. 数据底座层 — 全量业务数据采集、清洗、整合、存储与治理

### 3.1 数据存储架构

| 存储层 | 技术 | 数据范围 |
|--------|------|---------|
| 本地 JSON | 文件系统 (data/*.json) | 学生、企业、岗位、用户模型、会话 |
| Redis | Redis 5.x+ | 学生画像(server_job 写入)、语义缓存、面试上下文 |
| 向量存储 | Milvus (LightRAG) | 岗位 JD 向量、知识库文档向量 |
| 图存储 | Neo4j (LightRAG) | 实体-关系知识图谱 |
| 消息队列 | RocketMQ 5.x Proxy | 面试大纲题库 MQ、服务间异步消息 |
| RAG 文件 | 本地文件系统 (rag_storage/) | LightRAG 工作目录(kv_store + graph + vector) |
| GrepRAG | 本地 JSON (data/greprag/) | 文档正文持久化 + db 索引 |

### 3.2 数据处理流水线

**岗位入库链路：**
```
JD 文本 → LightRAG insert → 文档清洗 (LLM) → ainsert 写入
→ 异步处理 (等待终态 processed/failed)
→ 写入后校验 (增量统计、磁盘兜底)
```

**积压治理：**
- 实时统计 pending / processing / failed / processed
- 批量清理非 processed 文档 (含 Neo4j/Milvus 关联删除)
- 磁盘 kv_store doc_status 兜底同步

**关键文件：**
- [lightrag/service.py](app/rag/lightrag/service.py) — insert_texts / query / 积压管理完整实现
- [lightrag/doc_clean.py](app/rag/lightrag/doc_clean.py) — LLM 文档清洗

### 3.3 数据规范与治理

- **模型配置** — `modelCfg.json` 严格 Schema (TypedDict 校验，必填键缺失即报错)
- **用户模型** — `usermodel.json` 统一角色信息、目标、工具、流式选项
- **会话持久化** — `chat_sessions.json` 文件存储，支持 CRUD + 分页历史
- **文档状态追踪** — 全链路 op_id / trace_id 日志追踪

---

## 04. 基础设施层 — 云原生、容器化、微服务化

### 4.1 服务架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vite/React)                      │
│                  http://127.0.0.1:5173                    │
└──────────┬──────────────┬──────────────┬─────────────────┘
           │ SSE/REST     │ REST         │
           ▼              ▼              ▼
┌──────────────────┐ ┌──────────┐ ┌──────────────┐
│   ai_job (8001)  │ │server_job│ │   web_job    │
│  AI 能力服务      │ │ 业务服务  │ │  门户服务     │
│  FastAPI+SSE     │ │ Java     │ │  前端渲染     │
│  Python 3.10+    │ │ MySQL    │ │              │
└────────┬─────────┘ └────┬─────┘ └──────────────┘
         │                │
         │ RocketMQ 5.x   │
         │◄──────────────►│
         │                │
         ▼                ▼
┌──────────────────────────────────────┐
│         Redis (共享存储)              │
│  学生画像 | 语义缓存 | 面试上下文     │
├──────────────────────────────────────┤
│   Milvus (向量) | Neo4j (图)         │
│   LightRAG 双存储                    │
└──────────────────────────────────────┘
```

### 4.2 与 server_job 分工

| 职责 | ai_job (Python) | server_job (Java) |
|------|----------------|-------------------|
| AI 推理 | LangGraph / RAG / LLM | — |
| 业务数据 | — | MySQL (学生/企业/岗位/面试) |
| 会话管理 | 文件持久化 + Redis 读取 | 数据库 CRUD |
| 面试报告 | — | 报告生成与存储 |
| 服务间通信 | MQ Producer (大纲入库) | MQ Consumer + REST API |
| 流式输出 | SSE 实时推理 | — |

ai_job **不直连 MySQL 业务库**，通过 HTTP 从 server_job 拉取 context-bundle，保持数据边界清晰。

### 4.3 微服务间通信

- **REST API**: ai_job ↔ server_job (HTTP + X-Service-Token 鉴权)
- **RocketMQ**: 面试大纲题库 → MQ → server_job 消费
  - 5.x Proxy gRPC (macOS 开发)
  - 兼容 Apache legacy client (Linux)
  - SDK 不可用时降级为日志模式
- **CORS**: 允许 localhost 任意端口跨域 (开发环境)

**关键文件：**
- [mq/client.py](app/mq/client.py) — RocketMQ 客户端 (v5 + legacy 双兼容)
- [role005/mq/producer.py](app/session/role/role005/mq/producer.py) — 面试大纲 MQ 生产

### 4.4 运行时配置

| 配置项 | 机制 | 示例 |
|--------|------|------|
| 模型 | `config/modelCfg.json` | chat/embedding/tts/asr 多档位 |
| 运行时 | 环境变量 (`.env`) | REDIS_HOST, ROCKETMQ_*, SERVER_JOB_BASE_URL |
| 角色开关 | 环境变量 | ROLE005_INTERVIEW_ENABLED |
| 功能特性 | 环境变量 toggle | JOB_INFO_SEM_CACHE_ENABLED, JOB_RAG_ANALYZE_DISABLED |

### 4.5 安全设计

- API Key / Token 全部走环境变量，**禁止硬编码**
- 服务间鉴权 `X-Service-Token` (server_job ↔ ai_job)
- 路径越界保护 (GrepRAG `delete_markdown_file` 限制在 docs_dir 内)
- 输入校验全覆盖 (URL 协议校验、参数边界、空值守卫)
- 取消机制 (流式 `cancel_event` + `stream_registry`)

---

## PPT 讲解建议

### Slide 1: 四层全景
展示四层总览图，一句话概括每层定位

### Slide 2: 业务应用层 — 7 大角色
用表格列出 7 个角色，突出 "岗位规划师" 和 "模拟面试官" 采用 LangGraph 复杂图

### Slide 3: 业务应用层 — 岗位推荐 & 模拟面试
分别展示两个核心业务流的步骤图 (4-5 步)

### Slide 4: AI 能力中台 — 模型编排 & RAG
展示 modelCfg 多档位模型矩阵 + LightRAG/GrepRAG 双引擎对比

### Slide 5: AI 能力中台 — LangGraph 状态图
展示 ROLE001 和 ROLE005 的状态图拓扑

### Slide 6: AI 能力中台 — 语义缓存
展示精确缓存 → 语义缓存 → 完整链路的三级命中策略

### Slide 7: 数据底座层
展示三层存储架构 (Redis / Milvus+Neo4j / 文件) 与数据流转路径

### Slide 8: 基础设施层
展示 ai_job ↔ server_job ↔ Redis/MQ 的服务拓扑图

### Slide 9: 关键技术栈总览
一张表格汇总所有技术选型

---

## 关键技术栈总览

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| AI 编排 | LangGraph + LangChain |
| 大模型 | OpenAI 兼容 API (多模型多档位) |
| RAG 引擎 | LightRAG (lightrag-hku) + GrepRAG (自研) |
| 知识图谱 | Neo4j (LightRAG 图存储) |
| 向量存储 | Milvus (LightRAG 向量存储) |
| OCR | PaddleOCR 3.x + PaddlePaddle |
| 语音 | OpenAI 兼容 ASR + TTS |
| 消息队列 | RocketMQ 5.x (Proxy gRPC) |
| 缓存 | Redis |
| 智能采集 | Scrapy + DrissionPage |
| 语言 | Python 3.10+ |
| 通信协议 | REST + SSE + NDJSON + gRPC |
