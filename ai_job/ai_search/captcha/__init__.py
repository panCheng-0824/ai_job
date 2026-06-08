"""采集中验证码辅助（调用 ocr 底层）。"""

from .ocr_bridge import recognize_captcha_from_bytes, recognize_captcha_from_path

__all__ = ["recognize_captcha_from_path", "recognize_captcha_from_bytes"]
