from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .models import OCRLine, OCRSettings

logger = logging.getLogger(__name__)


def _to_float(value: Any) -> float:
    """尽最大努力将分数字段转换为 float。"""
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _extract_line_from_item(item: Any) -> OCRLine | None:
    """兼容多种 OCR 返回结构，提取单行文本结果。"""
    # 旧结构: [box, (text, score)] 或 [box, [text, score]]
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        box = item[0]
        text_info = item[1]
        if isinstance(text_info, (list, tuple)) and text_info:
            text = str(text_info[0] or "")
            score = _to_float(text_info[1] if len(text_info) > 1 else 0.0)
            return OCRLine(text=text, score=score, box=box)
        if isinstance(text_info, dict):
            text = str(
                text_info.get("text")
                or text_info.get("transcription")
                or text_info.get("label")
                or ""
            )
            score = _to_float(
                text_info.get("score")
                or text_info.get("confidence")
                or text_info.get("rec_score")
            )
            return OCRLine(text=text, score=score, box=box)

    # 新结构: dict
    if isinstance(item, dict):
        text = str(
            item.get("text")
            or item.get("transcription")
            or item.get("label")
            or ""
        )
        score = _to_float(
            item.get("score")
            or item.get("confidence")
            or item.get("rec_score")
            or item.get("prob")
        )
        box = (
            item.get("box")
            or item.get("bbox")
            or item.get("points")
            or item.get("poly")
            or []
        )
        if text or box:
            return OCRLine(text=text, score=score, box=box)
    return None


def _extract_lines_from_result_object(item: Any) -> list[OCRLine]:
    """从新版 PaddleOCR 结果对象中批量提取文本行。"""
    # 新版常见字段: rec_texts / rec_scores / dt_polys
    # 可能是 dict，也可能是自定义对象
    if isinstance(item, dict):
        texts = item.get("rec_texts")
        scores = item.get("rec_scores")
        boxes = item.get("dt_polys") or item.get("rec_polys") or item.get("dt_boxes")
    else:
        texts = getattr(item, "rec_texts", None)
        scores = getattr(item, "rec_scores", None)
        boxes = (
            getattr(item, "dt_polys", None)
            or getattr(item, "rec_polys", None)
            or getattr(item, "dt_boxes", None)
        )

    if not isinstance(texts, (list, tuple)):
        return []
    if not isinstance(scores, (list, tuple)):
        scores = [0.0] * len(texts)
    if not isinstance(boxes, (list, tuple)):
        boxes = [[] for _ in texts]

    lines: list[OCRLine] = []
    for idx, text in enumerate(texts):
        score = _to_float(scores[idx] if idx < len(scores) else 0.0)
        box = boxes[idx] if idx < len(boxes) else []
        lines.append(OCRLine(text=str(text or ""), score=score, box=box))
    return lines


def _normalize_result(raw_result: Any) -> list[OCRLine]:
    """将PaddleOCR原始结构转换为稳定的业务结构。"""

    normalized: list[OCRLine] = []
    if not raw_result:
        logger.warning("OCR原始结果为空")
        return normalized

    # 兼容旧版二维列表、单层列表、字典列表等返回结构
    candidates: list[Any] = []
    if isinstance(raw_result, list):
        if raw_result and isinstance(raw_result[0], list):
            candidates = raw_result[0]
        else:
            candidates = raw_result
    elif isinstance(raw_result, dict):
        # 常见新结构字段兜底
        for key in ("data", "result", "results", "lines"):
            value = raw_result.get(key)
            if isinstance(value, list):
                candidates = value
                break
        if not candidates:
            candidates = [raw_result]
    logger.info(
        "OCR结果归一化: raw_type=%s candidate_count=%s",
        type(raw_result).__name__,
        len(candidates),
    )

    failed_count = 0
    for idx, item in enumerate(candidates or []):
        # 先尝试新版“批量字段”结构
        batch_lines = _extract_lines_from_result_object(item)
        if batch_lines:
            normalized.extend(batch_lines)
            continue

        # 再尝试旧版“单行结构”提取
        line = _extract_line_from_item(item)
        if line is None:
            failed_count += 1
            if failed_count <= 3:
                logger.warning(
                    "OCR结果项解析失败: idx=%s type=%s sample=%s",
                    idx,
                    type(item).__name__,
                    str(item)[:300],
                )
            continue
        normalized.append(line)
    logger.info(
        "OCR结果归一化完成: success=%s failed=%s",
        len(normalized),
        failed_count,
    )
    return normalized


def _create_ocr_engine(use_angle_cls: bool, lang: str) -> Any:
    """创建OCR引擎并在依赖缺失时给出明确安装提示。"""

    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise ImportError(
            "PaddleOCR is not installed. Install it with:\n"
            "  pip install paddleocr\n"
            "And install PaddlePaddle according to your environment:\n"
            "  https://www.paddlepaddle.org.cn/install/quick"
        ) from exc
    try:
        return PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)
    except RuntimeError as exc:
        err = str(exc).lower()
        if "paddlepaddle" in err or "paddle_static" in err:
            raise ImportError(
                "未检测到可用的 PaddlePaddle（PaddleOCR 3.x / PaddleX 需要）。"
                " CPU 环境可执行：\n"
                "  pip install paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/\n"
                "或在本项目 requirements.txt 已配置的 extra-index-url 下 pip install -r requirements.txt。\n"
                "安装说明：https://www.paddlepaddle.org.cn/install/quick\n"
                f"详情：{exc}"
            ) from exc
        raise


def run_ocr(settings: OCRSettings) -> list[OCRLine]:
    """执行一次OCR识别并返回标准化结果列表。"""

    image_path = Path(settings.image_path).expanduser().resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    logger.info("OCR核心执行开始: path=%s lang=%s", image_path, settings.lang)

    ocr_engine = _create_ocr_engine(
        use_angle_cls=settings.use_angle_cls,
        lang=settings.lang,
    )
    try:
        # 兼容旧版 PaddleOCR（支持 cls 参数）
        raw_result = ocr_engine.ocr(str(image_path), cls=settings.use_angle_cls)
    except TypeError as exc:
        # 新版 PaddleOCR 已移除 cls 参数，直接调用即可
        if "unexpected keyword argument 'cls'" not in str(exc):
            raise
        logger.info("检测到新版PaddleOCR，自动切换无cls参数调用")
        raw_result = ocr_engine.ocr(str(image_path))
    normalized = _normalize_result(raw_result)
    logger.info("OCR核心执行完成: path=%s count=%s", image_path, len(normalized))
    if normalized:
        preview = [line.to_dict() for line in normalized[:3]]
        logger.info("OCR识别结果预览(最多3条): %s", preview)
    else:
        logger.warning("OCR未识别到文本: path=%s", image_path)
    return normalized


def run_ocr_bytes(
    data: bytes,
    *,
    lang: str = "ch",
    use_angle_cls: bool = False,
    suffix: str = ".png",
) -> list[OCRLine]:
    """对内存图片执行 OCR（供 ai_search 验证码等场景）。"""
    import tempfile

    if not data:
        raise ValueError("image bytes 不能为空")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        return run_ocr(
            OCRSettings(
                image_path=path,
                lang=lang,
                use_angle_cls=use_angle_cls,
            )
        )
    finally:
        Path(path).unlink(missing_ok=True)


def run_recognition(
    file_path: Path | str,
    lang: str = "ch",
    use_angle_cls: bool = False,
) -> tuple[list[OCRLine], dict[str, Any]]:
    """
    统一识别入口：图片走 PaddleOCR；PDF/Word 优先抽文本，扫描 PDF 回退分页 OCR。

    返回 (结果行, 元信息)，元信息含 mode、file_type。
    """
    from .resume_document import recognize_resume_file

    return recognize_resume_file(Path(file_path), lang, use_angle_cls)
