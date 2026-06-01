"""
ROLE005 HTTP API 层。

结构
----
- ``schemas/``：请求/响应 Pydantic 模型
- ``auth.py``：服务间 Token
- ``handlers/``：业务处理（规划预览、单轮 turn）
- ``internal/routes.py``：FastAPI 路由注册（web_app include_router）
"""

from app.session.role.role005.api.internal.routes import router as internal_interview_router

__all__ = ["internal_interview_router"]
