"""
近期对话原文摘录（ROLE001 岗位规划师等在上下文压缩失败时使用）。

职责：
- 按轮次策略选取 ``user/assistant`` 记录（不足阈值全量；否则头尾各若干条）；
- 单轮正文在句读或换行处优先截断，并对整块摘录做总字符预算分配。
"""

from __future__ import annotations

from typing import List

from app.session.user_turn_context import JOB_RECOMMEND_MEMORY_MARKER
from user_model import MemoryTurn

# 轮次少于此时摘录全部；不少于此时改为「开场 N 条 + 最近 M 条」。
USE_ALL_BELOW = 8
HEAD_TURNS = 4
TAIL_TURNS = 4
MIDDLE_OMITTED_LINE = "…（对话中部已省略）…"

TOTAL_MAX = 3200  # 整块摘录（含 role 前缀与章节标题侧开销）的大致上限
PER_TURN_SOFT = 520
PER_TURN_HARD_CAP = 800
# 含岗位推荐摘录的助手轮次：需保留岗位 ID/理由供追问「哪个更适合我」
JOB_REC_TURN_SOFT = 1400
JOB_REC_TURN_HARD_CAP = 2000
# 章节标题、首尾换行、轮次之间的换行等未计入 overhead 时的预留
WRAPPER_SLACK = 48


def truncate_at_sentence_boundary(text: str, *, soft_limit: int, hard_limit: int) -> str:
    """
    在 soft / hard 字符窗口内优先落在句末标点或换行处截断，尽量避免半句话被切开。

    - 不超过 soft_limit 的文本原样返回；
    - 超过时取前缀至 hard_limit，自尾向前寻找 ``。！？；`` 或换行，且截断点不低于约 1/3 窗口处；
      找不到合适边界则硬截并加省略号。
    """
    s = (text or "").strip()
    if not s:
        return ""
    hl = max(soft_limit, hard_limit)
    if len(s) <= soft_limit:
        return s
    window = s[:hl]
    min_cut = max(32, min(soft_limit // 2, len(window) // 3))
    sentence_end = "。！？；"
    cut = -1
    for i in range(len(window) - 1, min_cut - 1, -1):
        if window[i] in sentence_end:
            cut = i + 1
            break
    if cut < 0:
        for i in range(len(window) - 1, min_cut - 1, -1):
            if window[i] == "\n":
                cut = i + 1
                break
    if cut > 0:
        return window[:cut].rstrip()
    return window.rstrip() + "…"


def select_memory_turns_for_excerpt(memory: List[MemoryTurn]) -> tuple[List[MemoryTurn], bool]:
    """
    选取写入摘录的轮次。

    - 总轮次 < ``USE_ALL_BELOW``：全部摘录；
    - 否则：开头 ``HEAD_TURNS`` + 末尾 ``TAIL_TURNS``（时间顺序不变）。
    第二个返回值表示是否应在两段之间插入 ``MIDDLE_OMITTED_LINE``（仅当总轮次严格大于 ``USE_ALL_BELOW``）。
    """
    n = len(memory)
    if n < USE_ALL_BELOW:
        return list(memory), False
    merged = memory[:HEAD_TURNS] + memory[-TAIL_TURNS:]
    omit_middle = n > USE_ALL_BELOW
    return merged, omit_middle


def format_recent_dialog_excerpt(memory: List[MemoryTurn]) -> str:
    """
    将 memory 格式化为带章节标题的「近期对话摘录」Markdown 块。

    ``memory`` 须非空；选取与截断规则见本模块常量及 ``select_memory_turns_for_excerpt``。
    """
    excerpt_turns, omit_middle = select_memory_turns_for_excerpt(memory)
    overhead = sum(len(f"{t['role']}: ") for t in excerpt_turns)
    if omit_middle:
        overhead += len(MIDDLE_OMITTED_LINE) + 1
    available = max(0, TOTAL_MAX - overhead - WRAPPER_SLACK)
    n_ex = len(excerpt_turns)
    per_hard = min(PER_TURN_HARD_CAP, max(160, available // n_ex))
    per_soft = max(160, min(PER_TURN_SOFT, int(per_hard * 0.72)))
    per_soft = min(per_soft, per_hard - 1)

    def one_line(t: MemoryTurn) -> str:
        raw = str(t.get("content", ""))
        if t.get("role") == "assistant" and JOB_RECOMMEND_MEMORY_MARKER in raw:
            soft, hard = JOB_REC_TURN_SOFT, JOB_REC_TURN_HARD_CAP
        else:
            soft, hard = per_soft, per_hard
        body = truncate_at_sentence_boundary(
            raw,
            soft_limit=soft,
            hard_limit=hard,
        )
        return f"{t['role']}: {body}"

    if omit_middle:
        lines = (
            [one_line(t) for t in excerpt_turns[:HEAD_TURNS]]
            + [MIDDLE_OMITTED_LINE]
            + [one_line(t) for t in excerpt_turns[HEAD_TURNS:]]
        )
    else:
        lines = [one_line(t) for t in excerpt_turns]
    return "\n【近期对话摘录】\n" + "\n".join(lines) + "\n"
