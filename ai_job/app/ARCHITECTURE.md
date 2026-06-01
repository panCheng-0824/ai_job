# ai_job 分层架构

## 总览

```
portal/          # HTTP/SSE 门户（组装 session 层，不写业务图）
session/
  stream/        # SSE 派发：config、role_registry、token_forward、by_model
  chat_stream_*  # 兼容 re-export
  role/
    role00N/     # 按角色分包（domain / graph / agents / stream_handlers / api）
skills/          # 可复用技能（对抗 harness、面试占位等）
```

## 职责边界

| 层 | 职责 | 禁止 |
|----|------|------|
| **portal** | 鉴权、会话 CRUD、调用 `iter_chat_stream_sse_*` | LangGraph 节点逻辑 |
| **session/stream** | handler 解析、usercode 注册表、Token→SSE | 角色业务 Prompt |
| **session/role/role00N** | 该角色的图、意图、素材、流式分片 | 写 MySQL 业务表 |
| **skills** | 跨角色通用能力 | 角色专属状态机 |

## 角色包约定（以 role005 为范本）

- `domain/` — Pydantic / dataclass 契约
- `graph/` + `graph/nodes/` — LangGraph 编译与节点
- `agents/` — 单职责 LLM 调用封装
- `materials/` — 卡片、素材块、截断
- `stream_handlers/` — `entry.py` 组装 LLM；按模式拆 `plan_preview` / `turn_loop` 等
- `stream.py` — 薄 re-export，保持 `role_00N.py` 兼容
- `bindings.py` / `bindings_factory.py` — `build_graph_bindings`
- `api/`（可选）— 内部 REST，供 server_job 回调

## SSE 两条路径

1. **`iter_chat_stream_sse`** — `openai_direct` 或 `adversarial_harness`（通用 `chat_service`）
2. **`iter_chat_stream_sse_by_model`** — 按 `role_registry` 调用各角色 `stream_chat_service_tokens`

结构化事件（`job_recommend`、`resume_render`、`interview_*`）在 `stream/token_forward.py` 统一转发。

## 与 server_job 分工

- **server_job**：MySQL、面试 REST、报告、MQ 消费
- **ai_job**：LangGraph 实时推理、SSE；通过 HTTP 读 `context-bundle`，不直连业务库
