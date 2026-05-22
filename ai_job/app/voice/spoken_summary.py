"""用 chat 模型将助手回答压缩为适合朗读的摘要，再交给 TTS。"""

from __future__ import annotations

import logging
from typing import Tuple

from openai import OpenAI

from app.voice.openai_audio import pick_model_entry, synthesize_speech

logger = logging.getLogger(__name__)

_SUMMARY_SYSTEM = """你是语音播报助理。下面是一段助手给用户的书面回答。
请浓缩为适合语音朗读的中文摘要（约2～5句话，总共不超过220字）：
- 说清楚核心结论和行动建议，避免念 Markdown 符号、编号和表格；
- 语气自然口语化，不要用「综上所述」「摘要如下」等套话；
- 只输出摘要正文。"""

_SHORT_THRESHOLD = 120


def summarize_for_speech(answer_text: str, chat_model_level: str) -> str:
    """调用 chat 模型生成口语化朗读稿。"""
    entry = pick_model_entry("chat", chat_model_level)
    client = OpenAI(
        api_key=entry["model_key"],
        base_url=entry["model_api"],
    )
    user_part = (answer_text or "").strip()
    if len(user_part) > 12000:
        user_part = user_part[:12000]
    logger.info("spoken summary chat: model=%s chars=%s", entry["model_name"], len(user_part))
    resp = client.chat.completions.create(
        model=entry["model_name"],
        messages=[
            {"role": "system", "content": _SUMMARY_SYSTEM},
            {"role": "user", "content": user_part},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    msg = resp.choices[0].message
    raw = (getattr(msg, "content", None) or "").strip()
    if not raw:
        raise RuntimeError("摘要模型返回为空")
    return raw


def resolve_spoken_text_for_tts(answer_text: str, chat_model_level: str) -> str:
    """先得到要朗读的文本（短答跳过 chat，长答先摘要）。"""
    text = (answer_text or "").strip()
    if not text:
        raise ValueError("answer_text 不能为空")
    if len(text) <= _SHORT_THRESHOLD:
        return text
    return summarize_for_speech(text, chat_model_level)


def spoken_summary_to_audio(
    answer_text: str,
    chat_model_level: str,
    tts_model_level: str,
    voice: str,
) -> Tuple[bytes, str]:
    """短文本跳过 chat，直接 TTS；长文本先摘要再 TTS。返回 (audio_bytes, content_type)。"""
    spoken = resolve_spoken_text_for_tts(answer_text, chat_model_level)
    return synthesize_speech(spoken, tts_model_level, voice=voice)
