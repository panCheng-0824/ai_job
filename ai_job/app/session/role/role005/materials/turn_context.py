"""
ROLE005 — 从 message_context / 卡片解析面试 turn 与快照。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def parse_interview_turn_from_context(message_context: str) -> Dict[str, Any]:
    """
    从隐藏上下文中解析面试 turn 指令（web 经 message_context 传入）。

    期望 JSON::

        {
          "interview_session_id": "...",
          "turn_id": "...",
          "action": "start|answer|clarify|hint|timeout",
          "payload": { "answer_text": "..." }
        }
    """
    raw = (message_context or "").strip()
    if not raw:
        return {}
    if not raw.startswith("{"):
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def build_snapshots_from_cards(
    context_cards: List[Dict[str, Any]] | None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    从上下文卡片构建 job / company / resume 快照（dev 模式构造 ContextBundle 用）。

    返回 (job_snap, company_snap, resume_snap)。
    """
    job: Dict[str, Any] = {}
    company: Dict[str, Any] = {}
    resume: Dict[str, Any] = {}
    for card in context_cards or []:
        if not isinstance(card, dict):
            continue
        kind = str(card.get("kind") or card.get("type") or "").strip()
        payload = card.get("payload") if isinstance(card.get("payload"), dict) else card
        if not isinstance(payload, dict):
            continue
        if kind == "job":
            job = dict(payload)
        elif kind == "company":
            company = dict(payload)
        elif kind in ("resume", "ocr", "resume_draft"):
            resume = dict(payload)
    return job, company, resume


_RESUME_CARD_KINDS = frozenset({"resume", "ocr", "resume_draft"})
_JOB_CARD_KIND = "job"


def _card_kind(card: Dict[str, Any]) -> str:
    return str(card.get("kind") or card.get("type") or "").strip()


def context_cards_include_resume_and_job(
    context_cards: List[Dict[str, Any]] | None,
) -> bool:
    """
    上下文卡片是否同时包含简历与岗位（规划预览前置条件）。

    - 简历：``resume`` / ``ocr`` / ``resume_draft``
    - 岗位：``job``
    """
    has_resume = False
    has_job = False
    for card in context_cards or []:
        if not isinstance(card, dict):
            continue
        kind = _card_kind(card)
        if kind in _RESUME_CARD_KINDS:
            has_resume = True
        elif kind == _JOB_CARD_KIND:
            has_job = True
        if has_resume and has_job:
            return True
    return False
