"""OCR / 简历文档识别：路径 / 上传字节 / URL 下载后统一走 run_recognition。"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from ocr.core import run_recognition
from ocr.resume_document import is_allowed_suffix

from app.portal.errors import PortalError
from app.portal.paths import AI_JOB_ROOT

logger = logging.getLogger(__name__)

_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_FORMAT_HINT = "png/jpg/jpeg/bmp/webp/tif/tiff、pdf、docx（简历）"


def _lines_to_payload(
    lines: List[Any],
    extra: Dict[str, Any],
) -> Dict[str, Any]:
    out = {**extra, "count": len(lines), "items": [line.to_dict() for line in lines]}
    if lines:
        logger.info("识别结果(前3条): %s", [line.to_dict() for line in lines[:3]])
    return out


def _recognize_local(path: Path, lang: str, use_angle_cls: bool, extra: Dict[str, Any]) -> Dict[str, Any]:
    try:
        lines, meta = run_recognition(path, lang, use_angle_cls)
    except FileNotFoundError as exc:
        raise PortalError(str(exc), 404) from exc
    except ImportError as exc:
        raise PortalError(str(exc), 500) from exc
    except ValueError as exc:
        raise PortalError(str(exc), 400) from exc
    except Exception as exc:
        raise PortalError(f"识别失败: {exc}", 500) from exc

    lang_norm = (lang or "ch").strip() or "ch"
    return _lines_to_payload(
        lines,
        {
            **extra,
            "lang": lang_norm,
            "use_angle_cls": bool(use_angle_cls),
            **meta,
        },
    )


def recognize_by_path(image_path: str, lang: str, use_angle_cls: bool) -> Dict[str, Any]:
    path_str = image_path.strip()
    if not path_str:
        raise PortalError("image_path 不能为空", 400)
    path = Path(path_str)
    suffix = path.suffix.lower()
    if suffix and not is_allowed_suffix(suffix):
        raise PortalError(f"不支持的文件类型，仅支持：{_FORMAT_HINT}", 400)

    logger.info("路径识别开始: path=%s lang=%s", path_str, lang)
    result = _recognize_local(path, lang, use_angle_cls, {"image_path": path_str})
    logger.info("路径识别完成: path=%s count=%s mode=%s", path_str, result.get("count"), result.get("mode"))
    return result


def recognize_upload_bytes(
    content: bytes,
    filename: str,
    lang: str,
    use_angle_cls: bool,
) -> Dict[str, Any]:
    raw_name = (filename or "").strip() or "uploaded_file"
    suffix = Path(raw_name).suffix.lower()
    if suffix and not is_allowed_suffix(suffix):
        raise PortalError(f"仅支持：{_FORMAT_HINT}", 400)
    logger.info("上传识别开始: filename=%s lang=%s", raw_name, lang)
    if not content:
        raise PortalError("上传文件不能为空", 400)
    if len(content) > _MAX_UPLOAD_BYTES:
        raise PortalError("上传文件过大，限制 20MB", 400)

    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix or ".png",
            prefix="ocr-upload-",
            delete=False,
            dir=str(AI_JOB_ROOT),
        ) as tmp:
            tmp.write(content)
            temp_path = Path(tmp.name)

        result = _recognize_local(temp_path, lang, use_angle_cls, {"filename": raw_name})
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    logger.info(
        "上传识别完成: filename=%s count=%s mode=%s",
        raw_name,
        result.get("count"),
        result.get("mode"),
    )
    return result


def recognize_by_url(image_url: str, lang: str, use_angle_cls: bool) -> Dict[str, Any]:
    url = (image_url or "").strip()
    if not url:
        raise PortalError("image_url 不能为空", 400)
    if not (url.startswith("http://") or url.startswith("https://")):
        raise PortalError("image_url 必须以 http:// 或 https:// 开头", 400)
    logger.info("链接识别开始: url=%s lang=%s", url, lang)

    temp_path: Optional[Path] = None
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            raise PortalError(f"文件链接访问失败，HTTP {resp.status_code}", 400)
        content = resp.content or b""
        if not content:
            raise PortalError("链接内容为空", 400)
        if len(content) > _MAX_UPLOAD_BYTES:
            raise PortalError("文件过大，限制 20MB", 400)

        path_from_url = Path(url.split("?", 1)[0])
        suffix = path_from_url.suffix.lower()
        if suffix and not is_allowed_suffix(suffix):
            suffix = ".png"
        if not suffix:
            suffix = ".png"

        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix,
            prefix="ocr-url-",
            delete=False,
            dir=str(AI_JOB_ROOT),
        ) as tmp:
            tmp.write(content)
            temp_path = Path(tmp.name)

        result = _recognize_local(temp_path, lang, use_angle_cls, {"image_url": url})
    except PortalError:
        logger.warning("链接识别请求不合法: url=%s", url)
        raise
    except requests.RequestException as exc:
        logger.exception("链接识别失败，下载异常: url=%s", url)
        raise PortalError(f"下载失败: {exc}", 502) from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    logger.info("链接识别完成: url=%s count=%s mode=%s", url, result.get("count"), result.get("mode"))
    return result
