"""OCR demo package."""

from .core import run_ocr, run_ocr_bytes
from .models import OCRLine, OCRSettings

__all__ = ["run_ocr", "run_ocr_bytes", "OCRLine", "OCRSettings"]
