"""浏览器截图 / 图片 → ocr 识别（薄封装）。"""

from __future__ import annotations

import logging
from pathlib import Path

from ai_search.step_log import log_phase

logger = logging.getLogger(__name__)


def recognize_captcha_from_path(
    image_path: str | Path,
    *,
    lang: str = "ch",
    use_angle_cls: bool = True,
) -> str:
    """识别图片中的文字，拼接为单行（用于简单文字验证码）。"""
    from ocr.core import run_ocr
    from ocr.models import OCRSettings

    lines = run_ocr(
        OCRSettings(
            image_path=str(Path(image_path).expanduser().resolve()),
            lang=lang,
            use_angle_cls=use_angle_cls,
        )
    )
    text = "".join(line.text for line in lines if line.text).strip()
    log_phase(
        logger,
        "OCR",
        "验证码文字识别完成",
        path=str(image_path),
        text_len=len(text),
        line_count=len(lines),
    )
    return text


def recognize_captcha_from_bytes(
    data: bytes,
    *,
    lang: str = "ch",
    use_angle_cls: bool = True,
) -> str:
    from ocr.core import run_ocr_bytes

    lines = run_ocr_bytes(data, lang=lang, use_angle_cls=use_angle_cls)
    text = "".join(line.text for line in lines if line.text).strip()
    log_phase(
        logger,
        "OCR",
        "截图验证码识别完成",
        bytes_len=len(data),
        text_len=len(text),
    )
    return text
