"""流式会话运行上下文：供 pipeline 与各角色 stream_chat_service_tokens 共用，避免循环导入。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ChatStreamRunContext:
    session_id: str
    usercode: str
    user_model: Dict[str, Any]
    text: str
    history_turns: List[Dict[str, Any]]
    handler_id: str
    use_role_pipeline: bool
    use_adversarial_harness: bool
    adversarial_max_rounds: int
    adversarial_desc: str
    model_level_fallback: str
    system_prompt_extra: str
    temperature: float
    after_history_mutated: Optional[Callable[[], None]]
    register_stream_canceller: Callable[[str, Any], None]
    clear_stream_canceller_if_same: Callable[[str, Any], None]
    safe_cancel: Callable[[Any], None]
    user_display_content: str = ""
    user_message_context: str = ""
    user_context_cards: List[Dict[str, Any]] = field(default_factory=list)
