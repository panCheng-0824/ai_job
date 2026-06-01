# Interview JSON Schema（ROLE005）

与 `ai_job/app/session/role/role005/domain/models.py` 保持字段一致，供前后端与 CI 契约校验。

| 文件 | 说明 |
|------|------|
| `interview_plan.schema.json` | 面试大纲 |
| `interview_session.schema.json` | 会话快照（context-bundle 中的 session） |
| `interview_turn_result.schema.json` | ai_job `/turn` 返回 |

实施建议：在 CI 中对 ai_job Pydantic 与本文目录做 snapshot diff。
