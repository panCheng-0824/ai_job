"""OCR demo package."""

from .core import run_ocr
from .models import OCRLine, OCRSettings

__all__ = ["run_ocr", "OCRLine", "OCRSettings"]
