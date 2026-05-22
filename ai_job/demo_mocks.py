"""
演示/测试用替身：与业务逻辑分离，便于 ``demo.py`` 在无真实 API 时跑通全链路。

``unittest.mock.patch`` 目标：
- ``role_pipeline._run_pipeline_llm`` → 使用本模块的 ``mock_run_pipeline_llm``，避免访问网络与 modelCfg；
- ``lc_agent.agent_executor_compat.AgentExecutor.invoke``（或旧版 ``langchain.agents.AgentExecutor.invoke``）
  → ``mock_agent_executor_invoke``，跳过工具循环与真实 LLM。

请勿在生产路径 import 本模块；仅用于离线演示或本地冒烟测试。
"""

from __future__ import annotations

from typing import Any, Dict


def mock_run_pipeline_llm(profile: Any, user_payload: str, *, temperature: float = 0.0) -> Any:
    """
    模拟结构化 JSON 输出，键名与 ``schemas/*.json`` 及各角色的 ``structured_primary_field`` 对齐。

    通过 ``usercode`` 中的占位片段（``PIPE_Q`` / ``PIPE_C`` / ``PIPE_A`` / ``PIPE_P``）分支，
    与 ``role_profiles.json`` 中演示用 code 一致（如 ``ROLE_PIPE_Q01``）。
    """
    code = profile.get("usercode", "")
    head = user_payload.strip().split("\n", 1)[0][:72]
    if "PIPE_Q" in code:
        return {"clean_question": f"[demo 净化后] {head}", "noise_notes": "demo"}
    if "PIPE_C" in code:
        return {
            "summary": f"[demo 上下文摘要] 压缩自 {len(user_payload)} 字符的前文。",
            "keywords": ["demo"],
        }
    if "PIPE_A" in code:
        return {
            "risk_level": "medium",
            "issues": ["demo 要点 A", "demo 要点 B"],
            "suggestions": ["保持严谨"],
        }
    if "PIPE_P" in code:
        return {
            "merge_highlights": ["demo 画像要点"],
            "suggested_profile_patch": {"focus_topics": ["LangChain Agent"]},
            "discard_noise": [],
            "confidence_notes": "待验证",
        }
    return {"raw": f"[demo:{code}] ok"}


def mock_agent_executor_invoke(self: Any, inputs: Dict[str, Any], **kw: Any) -> Dict[str, Any]:
    """替换 ``AgentExecutor.invoke``：不执行 bind_tools，直接返回固定形态结果。"""
    q = inputs.get("input", "")
    return {
        "output": (
            "【演示主 Agent 模拟回答】已收到问题要点；"
            "真实环境下此处为工具调用 Agent 的最终输出。\n"
            f"input 预览: {str(q)[:120]}…"
        ),
        "input": inputs,
    }
