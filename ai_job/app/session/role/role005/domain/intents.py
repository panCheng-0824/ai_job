"""
ROLE005 — 用户回合动作与面试官输出动作枚举。
"""

from __future__ import annotations

from typing import Literal

# 客户端 / server_job 提交的 turn 动作
TurnAction = Literal["answer", "clarify", "hint", "timeout", "abandon", "start"]

# 面试官 Agent 对外 JSON 的 action 字段
InterviewerAction = Literal[
    "ask_question",
    "ask_followup",
    "provide_hint",
    "clarify",
    "acknowledge",
]

# 会话业务状态（与 server_job interview_sessions.status 对齐）
SessionStatus = Literal[
    "planning",
    "ready",
    "in_progress",
    "completed",
    "abandoned",
]

# 面试阶段
InterviewPhase = Literal["self_intro", "question", "summary"]

VALID_TURN_ACTIONS = frozenset(
    {"answer", "clarify", "hint", "timeout", "abandon", "start"}
)
