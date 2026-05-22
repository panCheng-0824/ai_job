"""用户轮次：展示用卡片 vs 送入模型的附加上下文。"""

from __future__ import annotations

from typing import Any, Dict, List

# 写入「近期对话摘录」时，含岗位推荐摘录的助手轮次使用更大截断预算（见 recent_dialog_excerpt）
JOB_RECOMMEND_MEMORY_MARKER = "【本轮推荐岗位摘录】"
_JOB_REC_MEMORY_MAX_CHARS = 2400
_JOB_REC_MEMORY_MAX_JOBS = 10


def build_llm_user_text(*, display: str, hidden: str, fallback: str = "") -> str:
    """合并可见文案与隐藏附加上下文，供本轮 ``ctx.text`` 使用。"""
    base = (display or "").strip() or (fallback or "").strip()
    hidden = (hidden or "").strip()
    if not hidden:
        return base
    block = f"【用户附加上下文】\n{hidden}"
    return f"{base}\n\n{block}" if base else block


def user_turn_content_for_memory(turn: Dict[str, Any]) -> str:
    """历史轮次还原为模型可读的用户内容（含 ``message_context``）。"""
    content = str(turn.get("content", "")).strip()
    hidden = str(turn.get("message_context", "")).strip()
    if not hidden:
        return content
    block = f"【附加上下文】\n{hidden}"
    return f"{content}\n\n{block}".strip() if content else block


def _pick_job_list(job_recommend: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从持久化的 ``job_recommend`` 块取出岗位列表。"""
    rec = job_recommend.get("recommendation") if isinstance(job_recommend.get("recommendation"), dict) else {}
    jobs = rec.get("recommended_jobs") if isinstance(rec.get("recommended_jobs"), list) else []
    if jobs:
        return [j for j in jobs if isinstance(j, dict)]
    raw = job_recommend.get("jobs")
    if isinstance(raw, list):
        return [j for j in raw if isinstance(j, dict)]
    return []


def format_job_recommend_for_memory(job_recommend: Dict[str, Any]) -> str:
    """
    将岗位推荐结构化结果转为可写入对话历史的文本。

    界面气泡仍用 ``content`` 短摘要 + 卡片组件；本函数供「近期对话摘录」与后续追问使用。
    """
    if not isinstance(job_recommend, dict) or not job_recommend:
        return ""

    lines: List[str] = [JOB_RECOMMEND_MEMORY_MARKER]

    llm = job_recommend.get("llm") if isinstance(job_recommend.get("llm"), dict) else {}
    reason = str(llm.get("reason") or "").strip()
    if reason:
        lines.append(f"综合分析：{reason}")

    rec = job_recommend.get("recommendation") if isinstance(job_recommend.get("recommendation"), dict) else {}
    status = str(rec.get("match_status") or "").strip()
    if status:
        lines.append(f"推荐状态：{status}")

    jobs = _pick_job_list(job_recommend)[:_JOB_REC_MEMORY_MAX_JOBS]
    if jobs:
        lines.append(f"共 {len(jobs)} 条推荐岗位（按模型排序）：")
        for i, job in enumerate(jobs, 1):
            title = str(job.get("job_title") or job.get("job_name") or "未知岗位").strip()
            jid = str(job.get("job_id") or "").strip()
            city = str(job.get("city") or "").strip()
            salary = str(job.get("salary_range_month") or job.get("salary") or "").strip()
            company = str(job.get("company_name") or "").strip()
            rel = job.get("company_relation") if isinstance(job.get("company_relation"), dict) else {}
            if not company:
                company = str(rel.get("company_name") or "").strip()
            score = job.get("score")
            match_reason = str(job.get("match_reason") or "").strip()
            if len(match_reason) > 160:
                match_reason = match_reason[:160] + "…"

            head = f"{i}. {title}"
            if jid:
                head += f"（ID:{jid}）"
            lines.append(head)
            meta = " / ".join(p for p in (city, salary, company) if p)
            if meta:
                lines.append(f"   {meta}")
            if score is not None and str(score).strip() not in ("", "0"):
                lines.append(f"   匹配分：{score}")
            if match_reason:
                lines.append(f"   匹配理由：{match_reason}")
    else:
        detail = rec.get("no_match_detail") if isinstance(rec.get("no_match_detail"), dict) else {}
        title = str(detail.get("title") or "").strip()
        if title:
            lines.append(f"说明：{title}")
        for c in detail.get("causes") or []:
            c = str(c).strip()
            if c:
                lines.append(f"- {c}")

    cache = job_recommend.get("cache")
    if isinstance(cache, dict) and cache.get("hit"):
        lines.append("（该推荐结果来自语义相似缓存）")

    text = "\n".join(lines).strip()
    if len(text) > _JOB_REC_MEMORY_MAX_CHARS:
        return text[:_JOB_REC_MEMORY_MAX_CHARS] + "\n…（岗位摘录已截断）"
    return text


def assistant_turn_content_for_memory(turn: Dict[str, Any]) -> str:
    """
    助手轮次写入对话记忆：合并界面摘要与 ``job_recommend`` 结构化摘录。

    解决「卡片里有岗位、但历史只有一句综合分析」导致追问「哪个更适合我」时上下文不足。
    """
    content = str(turn.get("content", "")).strip()
    jr = turn.get("job_recommend")
    if isinstance(jr, dict) and jr:
        excerpt = format_job_recommend_for_memory(jr)
        if excerpt:
            return f"{content}\n\n{excerpt}".strip() if content else excerpt
    return content


def append_user_turn_to_history(
    history_turns: List[Dict[str, Any]],
    *,
    ts: str,
    display_content: str,
    message_context: str = "",
    context_cards: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """写入一条用户轮次：界面只展示 ``content`` + ``context_cards``。"""
    turn: Dict[str, Any] = {
        "role": "user",
        "content": (display_content or "").strip(),
        "ts": ts,
    }
    cards = context_cards or []
    if cards:
        turn["context_cards"] = cards
    hidden = (message_context or "").strip()
    if hidden:
        turn["message_context"] = hidden
    history_turns.append(turn)
    return turn
