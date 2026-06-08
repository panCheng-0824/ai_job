"""LightRAG 离线分词回退：tiktoken 不可用时按字符切分（无需联网）。"""

from __future__ import annotations

from typing import List


class CharSliceBackend:
    """按字符索引切分；decode 依赖最近一次 encode 的原文。"""

    def __init__(self) -> None:
        self._text = ""

    def encode(self, content: str) -> List[int]:
        self._text = content or ""
        return list(range(len(self._text)))

    def decode(self, tokens: List[int]) -> str:
        if not self._text or not tokens:
            return ""
        return "".join(self._text[i] for i in tokens if 0 <= i < len(self._text))


def build_char_tokenizer(model_name: str):
    """构建字符级 Tokenizer（chunk 粒度偏粗，但可保证离线可用）。"""
    from lightrag.utils import Tokenizer

    name = (model_name or "gpt-4o-mini").strip() or "gpt-4o-mini"
    return Tokenizer(model_name=name, tokenizer=CharSliceBackend())
