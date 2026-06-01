"""
兼容入口 — 逻辑已迁至 ``api.handlers``。
"""

from app.session.role.role005.api.handlers.plan_preview import handle_plan_preview
from app.session.role.role005.api.handlers.turn import handle_interview_turn

__all__ = ["handle_plan_preview", "handle_interview_turn"]
