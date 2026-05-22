from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _to_json_safe(value: Any) -> Any:
    """将 numpy/自定义容器递归转换为 JSON 可序列化的原生类型。"""
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(v) for v in value]
    # numpy.ndarray / 其他支持 tolist 的对象
    if hasattr(value, "tolist") and callable(getattr(value, "tolist")):
        try:
            return _to_json_safe(value.tolist())
        except Exception:
            pass
    # numpy 标量 / 其他支持 item 的对象
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return _to_json_safe(value.item())
        except Exception:
            pass
    return value


@dataclass(frozen=True)
class OCRSettings:
    """OCR运行配置，便于CLI/API共享同一份参数结构。"""

    image_path: Path
    lang: str = "ch"
    use_angle_cls: bool = False


@dataclass(frozen=True)
class OCRLine:
    """单行OCR结果：文本、置信度和检测框。"""

    text: str
    score: float
    box: Any

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化字典，用于JSON输出。"""
        return {
            "text": str(self.text),
            "score": float(self.score),
            "box": _to_json_safe(self.box),
        }
