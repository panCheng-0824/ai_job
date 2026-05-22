#!/usr/bin/env python3
"""
对 ``modelCfg.json`` 中每条模型配置做 OpenAI 兼容 Chat **场景化连通性测试**：

使用固定人设 + 固定任务（写诗），更接近主流程中的 system / user 交互，便于观察延迟与生成质量。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lc_agent.llm import chat_model_from_entry
from model_cfg import ModelEntry, load_model_list

# 默认测试场景（可通过命令行覆盖）
DEFAULT_SYSTEM_PROMPT = (
    "你的名字叫做小潼，是一个可爱的人工智能。"
)
DEFAULT_USER_PROMPT = "请你以春天写一首诗"


def _probe_one(
    entry: ModelEntry,
    *,
    timeout_s: float,
    max_tokens: int,
    temperature: float,
    system_prompt: str,
    user_prompt: str,
    preview_chars: int,
) -> Tuple[bool, str, float]:
    """返回 (是否成功, 摘要文本或错误信息, 耗时秒)。"""
    llm = chat_model_from_entry(
        entry,
        timeout=timeout_s,
        max_tokens=max_tokens,
        temperature=temperature,
        max_retries=0,
    )
    messages = [
        SystemMessage(content=system_prompt.strip()),
        HumanMessage(content=user_prompt.strip()),
    ]
    t0 = time.monotonic()
    try:
        out = llm.invoke(messages)
        elapsed = time.monotonic() - t0
        text = getattr(out, "content", None) or ""
        if isinstance(text, str):
            cleaned = text.strip()
            single_line = cleaned.replace("\n", "\\n ")
            preview = single_line[:preview_chars] + (
                "…" if len(single_line) > preview_chars else ""
            )
        else:
            preview = str(text)[:preview_chars]
        return True, preview or "(空内容)", elapsed
    except Exception as exc:
        elapsed = time.monotonic() - t0
        return False, f"{type(exc).__name__}: {exc}", elapsed


def main() -> None:
    """批量探测各模型配置的连通性并输出摘要结果。"""
    parser = argparse.ArgumentParser(
        description="场景化测试 modelCfg.json 各端点（小潼人设 + 春天写诗）"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="modelCfg.json 路径（默认：项目根下 modelCfg.json）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="单次 Chat 请求超时（秒），写诗略长，默认 120",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="生成上限 token，默认 512",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="采样温度，默认 0.7（略利于诗句多样性）",
    )
    parser.add_argument(
        "--system",
        type=str,
        default=DEFAULT_SYSTEM_PROMPT,
        help="System 角色文案（默认：小潼人设）",
    )
    parser.add_argument(
        "--user",
        type=str,
        default=DEFAULT_USER_PROMPT,
        help="用户任务文案（默认：以春天写诗）",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=280,
        help="控制台展示的回复预览最大字符数，默认 280",
    )
    args = parser.parse_args()

    entries: List[ModelEntry] = load_model_list(args.config)

    print(f"共 {len(entries)} 条模型配置 | 超时 {args.timeout}s | max_tokens={args.max_tokens} | T={args.temperature}")
    print(f"System: {args.system[:80]}{'…' if len(args.system) > 80 else ''}")
    print(f"User:   {args.user[:80]}{'…' if len(args.user) > 80 else ''}\n")

    ok_n = 0
    fail_n = 0

    for entry in entries:
        level = entry["model_level"]
        name = entry["model_name"]
        api = entry["model_api"]
        label = f"[{level}] {name}"
        print(f"→ {label}")
        print(f"   base_url: {api}")

        ok, detail, elapsed = _probe_one(
            entry,
            timeout_s=args.timeout,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            system_prompt=args.system,
            user_prompt=args.user,
            preview_chars=args.preview_chars,
        )

        if ok:
            ok_n += 1
            print(f"   ✓ 连通  {elapsed:.2f}s")
            print(f"   回复预览: {detail}")
        else:
            fail_n += 1
            print(f"   ✗ 失败  {elapsed:.2f}s  {detail}")

        print()

    print("-" * 60)
    print(f"结果：成功 {ok_n} / 失败 {fail_n} / 合计 {len(entries)}")
    if fail_n:
        sys.exit(1)


if __name__ == "__main__":
    main()
