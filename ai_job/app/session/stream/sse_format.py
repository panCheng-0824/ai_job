"""SSE 文本格式与 thinking 增量去重。"""

from __future__ import annotations


def sse_chunk(event: str, data: str) -> str:
    """组装标准 SSE 帧：event + data。"""
    return f"event: {event}\ndata: {data}\n\n"


def thinking_delta_from_piece(current: str, piece: str) -> str:
    """
    将可能为累计文本的 thinking 片段转为增量。

    减轻前端重复滚动；兼容模型重复推送整段 thinking 的情况。
    """
    if not piece:
        return ""
    if not current:
        return piece
    if piece == current:
        return ""
    if piece.startswith(current):
        return piece[len(current) :]
    if current.startswith(piece):
        return ""

    max_overlap = min(len(current), len(piece))
    for overlap in range(max_overlap, 0, -1):
        if current.endswith(piece[:overlap]):
            return piece[overlap:]
    return piece
