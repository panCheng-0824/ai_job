from __future__ import annotations

import argparse
from pathlib import Path

from .models import OCRSettings


def parse_args() -> argparse.Namespace:
    """定义命令行参数，集中管理CLI输入。"""

    parser = argparse.ArgumentParser(description="Run a local PaddleOCR demo.")
    parser.add_argument(
        "--image",
        required=True,
        help="Path to input image file, e.g. ./ocr/test.png",
    )
    parser.add_argument(
        "--lang",
        default="ch",
        help="OCR language model, e.g. ch / en / chinese_cht",
    )
    parser.add_argument(
        "--use-angle-cls",
        action="store_true",
        help="Enable angle classification for rotated text.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional output json path, e.g. ./ocr/result.json",
    )
    return parser.parse_args()


def build_settings(args: argparse.Namespace) -> OCRSettings:
    """将命令行参数映射为核心层可直接使用的配置对象。"""

    return OCRSettings(
        image_path=Path(args.image),
        lang=args.lang,
        use_angle_cls=args.use_angle_cls,
    )
