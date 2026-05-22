"""语音：ASR / TTS / 口语摘要（封装 app.voice）。"""

import logging
from pathlib import Path
from typing import Any, Dict, Tuple

from app.voice.openai_audio import open_tts_stream, synthesize_speech, transcribe_bytes
from app.voice.spoken_summary import resolve_spoken_text_for_tts, spoken_summary_to_audio

from app.portal.errors import PortalError

logger = logging.getLogger(__name__)

_MAX_AUDIO_BYTES = 25 * 1024 * 1024
_MAX_TTS_CHARS = 8000
_ALLOWED_AUDIO = {".webm", ".wav", ".mp3", ".mp4", ".m4a", ".ogg", ".flac"}


def transcribe_upload(
    content: bytes,
    filename: str,
    content_type: str,
    model_level: str,
) -> Dict[str, Any]:
    raw_name = (filename or "").strip() or "recording.webm"
    suffix = Path(raw_name).suffix.lower()
    if suffix and suffix not in _ALLOWED_AUDIO:
        raise PortalError(
            "音频格式不支持，请使用 webm/wav/mp3/mp4/m4a/ogg/flac",
            400,
        )
    ml = (model_level or "mid").strip()
    logger.info("语音转写开始: filename=%s model_level=%s", raw_name, ml)
    if not content:
        raise PortalError("音频文件为空", 400)
    if len(content) > _MAX_AUDIO_BYTES:
        raise PortalError("音频过大，限制 25MB", 400)
    try:
        text = transcribe_bytes(content, raw_name, content_type or "application/octet-stream", ml)
    except ValueError as exc:
        logger.warning("语音转写配置错误: %s", exc)
        raise PortalError(str(exc), 400) from exc
    except RuntimeError as exc:
        logger.warning("语音转写失败: %s", exc)
        raise PortalError(str(exc), 502) from exc
    except Exception as exc:
        logger.exception("语音转写异常")
        raise PortalError(f"语音转写失败: {exc}", 500) from exc
    logger.info("语音转写完成: chars=%s", len(text))
    return {"text": text, "model_level": ml}


def speech_binary(text: str, model_level: str, voice: str) -> Tuple[bytes, str]:
    t = (text or "").strip()
    if not t:
        raise PortalError("text 不能为空", 400)
    if len(t) > _MAX_TTS_CHARS:
        raise PortalError("文本过长，请控制在 8000 字符内", 400)
    ml = (model_level or "mid").strip()
    v = (voice or "serena").strip()
    logger.info("TTS 开始: chars=%s model_level=%s", len(t), ml)
    try:
        audio, ctype = synthesize_speech(t, ml, voice=v)
    except ValueError as exc:
        logger.warning("TTS 配置错误: %s", exc)
        raise PortalError(str(exc), 400) from exc
    except RuntimeError as exc:
        logger.warning("TTS 失败: %s", exc)
        raise PortalError(str(exc), 502) from exc
    except Exception as exc:
        logger.exception("TTS 异常")
        raise PortalError(f"TTS 失败: {exc}", 500) from exc
    logger.info("TTS 完成: bytes=%s ctype=%s", len(audio), ctype)
    return audio, ctype


def spoken_summary_audio(
    answer_text: str,
    chat_model_level: str,
    tts_model_level: str,
    voice: str,
) -> Tuple[bytes, str]:
    logger.info(
        "spoken-summary 开始: chat_level=%s tts_level=%s",
        chat_model_level,
        tts_model_level,
    )
    try:
        audio, ctype = spoken_summary_to_audio(
            answer_text,
            (chat_model_level or "mid").strip(),
            (tts_model_level or "mid").strip(),
            voice=(voice or "serena").strip(),
        )
    except ValueError as exc:
        logger.warning("spoken-summary 参数错误: %s", exc)
        raise PortalError(str(exc), 400) from exc
    except RuntimeError as exc:
        logger.warning("spoken-summary 失败: %s", exc)
        raise PortalError(str(exc), 502) from exc
    except Exception as exc:
        logger.exception("spoken-summary 异常")
        raise PortalError(f"语音摘要失败: {exc}", 500) from exc
    logger.info("spoken-summary 完成: bytes=%s ctype=%s", len(audio), ctype)
    return audio, ctype


def open_tts_stream_for_text(text: str, model_level: str, voice: str) -> Any:
    t = (text or "").strip()
    if not t:
        raise PortalError("text 不能为空", 400)
    if len(t) > _MAX_TTS_CHARS:
        raise PortalError("文本过长，请控制在 8000 字符内", 400)
    logger.info("TTS 流式开始: chars=%s model_level=%s", len(t), model_level)
    try:
        return open_tts_stream(
            t,
            (model_level or "mid").strip(),
            voice=(voice or "serena").strip(),
        )
    except ValueError as exc:
        logger.warning("TTS 流式配置错误: %s", exc)
        raise PortalError(str(exc), 400) from exc
    except RuntimeError as exc:
        logger.warning("TTS 流式失败: %s", exc)
        raise PortalError(str(exc), 502) from exc
    except Exception as exc:
        logger.exception("TTS 流式异常")
        raise PortalError(f"TTS 失败: {exc}", 500) from exc


def spoken_summary_stream(
    answer_text: str,
    chat_model_level: str,
    tts_model_level: str,
    voice: str,
) -> Any:
    logger.info(
        "spoken-summary 流式: chat_level=%s tts_level=%s",
        chat_model_level,
        tts_model_level,
    )
    try:
        spoken = resolve_spoken_text_for_tts(
            answer_text,
            (chat_model_level or "mid").strip(),
        )
        return open_tts_stream(
            spoken,
            (tts_model_level or "mid").strip(),
            voice=(voice or "serena").strip(),
        )
    except ValueError as exc:
        logger.warning("spoken-summary 流式参数错误: %s", exc)
        raise PortalError(str(exc), 400) from exc
    except RuntimeError as exc:
        logger.warning("spoken-summary 流式失败: %s", exc)
        raise PortalError(str(exc), 502) from exc
    except Exception as exc:
        logger.exception("spoken-summary 流式异常")
        raise PortalError(f"语音摘要失败: {exc}", 500) from exc


def resolve_spoken_summary_text(answer_text: str, chat_model_level: str) -> str:
    try:
        return resolve_spoken_text_for_tts(
            answer_text,
            (chat_model_level or "mid").strip(),
        )
    except ValueError as exc:
        logger.warning("spoken-summary/text 参数错误: %s", exc)
        raise PortalError(str(exc), 400) from exc
    except RuntimeError as exc:
        logger.warning("spoken-summary/text 失败: %s", exc)
        raise PortalError(str(exc), 502) from exc
    except Exception as exc:
        logger.exception("spoken-summary/text 异常")
        raise PortalError(f"朗读稿生成失败: {exc}", 500) from exc
