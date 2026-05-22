#!/usr/bin/env python3
"""
Simple PaddleOCR demo script.

Usage:
    python ocr/paddleocr_demo.py --image /path/to/image.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    # 兼容 "python ocr/paddleocr_demo.py" 直接运行场景。
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from ocr.cli import build_settings, parse_args
from ocr.core import run_ocr


def _save_json(output_json: str, result_dicts: list[dict]) -> None:
    """将识别结果落盘为JSON，便于后处理或调试。"""

    output_path = Path(output_json).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result_dicts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved JSON result to: {output_path}")


def main() -> None:
    # 入口层只负责“编排”，具体OCR逻辑下沉到core模块。
    args = parse_args()
    settings = build_settings(args)
    results = run_ocr(settings)

    if not results:
        print("No text detected.")
        return

    print(f"Detected {len(results)} text lines:")
    result_dicts = [line.to_dict() for line in results]
    for idx, line in enumerate(results, start=1):
        print(f"{idx:02d}. {line.text} (score={line.score:.4f})")

    if args.output_json:
        _save_json(args.output_json, result_dicts)


if __name__ == "__main__":
    main()
