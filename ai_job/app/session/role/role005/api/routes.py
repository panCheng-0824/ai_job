"""
兼容入口 — 实现已迁至 ``api.internal.routes``。

保留本路径避免 ``from app.session.role.role005.api.routes import router`` 失效。
"""

from app.session.role.role005.api.internal.routes import router

__all__ = ["router"]
