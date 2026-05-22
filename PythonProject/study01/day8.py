"""
================================================================================
Day 8 —— Harness engineering（评测/回归）：固定题集 + 运行器 + 指标 + 失败样本
================================================================================

这一关的目标
------------
你已经有：
- Agent（Day1~Day4）
- RAG 检索（Day6）
- 端到端 RAG（Day9）

但工程上最容易“越改越差”的问题是：
你改了 prompt / 工具 / 检索参数，感觉变好了，但没有证据。

Day8 解决的是“可回归”：
- 有一套固定题集（jsonl）
- 每次运行都输出通过率、失败列表
- 你可以把它接入 CI（以后再做）

本文件的评测是“学习版”，指标先做得简单可理解：
- **keyword_hit**：回答里是否包含 expected_keywords（粗粒度，入门够用）
- 输出失败样本：问题、回答、缺失关键词

运行方式
--------
    python -m study01.day8

默认读取同目录 `eval_questions_day8.jsonl`。
你也可以指定数据集：
    python -m study01.day8 --dataset ./study01/eval_questions_day8.jsonl
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from study01.day3 import create_basic_agent
from study01.day9 import rag_answer


@dataclass(frozen=True)
class EvalCase:
    """一条评测用例（从 jsonl 读入）。"""

    id: str
    mode: str  # "agent" or "rag"
    question: str
    expected_keywords: List[str]


@dataclass(frozen=True)
class EvalResult:
    """一条用例的评测结果（用于汇总与打印）。"""

    case_id: str
    mode: str
    passed: bool
    missing_keywords: List[str]
    answer_preview: str


def _load_jsonl_cases(path: Path) -> List[EvalCase]:
    """
    读取 jsonl 文件。

    jsonl = JSON Lines：每行一个 JSON 对象
    优点：追加/版本管理友好；比一个大 JSON 数组更容易 diff。
    """
    if not path.is_file():
        raise FileNotFoundError(f"数据集不存在: {path}")
    cases: List[EvalCase] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        cases.append(
            EvalCase(
                id=str(obj.get("id") or f"line-{i}"),
                mode=str(obj.get("mode") or "rag"),
                question=str(obj.get("question") or ""),
                expected_keywords=[str(x) for x in (obj.get("expected_keywords") or [])],
            )
        )
    return cases


def _keyword_judge(answer: str, expected_keywords: List[str]) -> Tuple[bool, List[str]]:
    """
    最简单的“自动评分”：
    - 全部关键词都出现 → 通过
    - 否则不通过，并返回缺失关键词

    注意：这不是严格评测，只是入门让你建立“可回归”的习惯。
    """
    a = (answer or "").lower()
    missing: List[str] = []
    for kw in expected_keywords:
        if kw and kw.lower() not in a:
            missing.append(kw)
    return (len(missing) == 0), missing


def _run_one(case: EvalCase, *, agent: Any) -> EvalResult:
    """
    跑一条用例：
    - mode=agent：走 AgentSkill（Function Calling 可能发生）
    - mode=rag：走 Day9 端到端 RAG
    """
    if case.mode == "agent":
        answer = str(agent.run(case.question))
    elif case.mode == "rag":
        answer = rag_answer(case.question).answer
    else:
        answer = f"（未知 mode={case.mode}，跳过执行）"

    passed, missing = _keyword_judge(answer, case.expected_keywords)
    preview = answer[:200] + ("…" if len(answer) > 200 else "")
    return EvalResult(
        case_id=case.id,
        mode=case.mode,
        passed=passed,
        missing_keywords=missing,
        answer_preview=preview,
    )


def run_eval(cases: List[EvalCase]) -> int:
    """
    执行整个评测集并打印汇总。

    返回退出码：
    - 0：全部通过
    - 1：存在失败（便于你以后接 CI / pre-push）
    """
    agent = create_basic_agent(verbose=False)

    results: List[EvalResult] = []
    for c in cases:
        results.append(_run_one(c, agent=agent))

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    print("\n" + "=" * 70)
    print("【Day8 Harness 评测汇总】")
    print("=" * 70)
    print(f"总数: {total}  通过: {passed}  失败: {failed}")

    if failed:
        print("\n【失败用例（用于回归定位）】")
        for r in results:
            if r.passed:
                continue
            print(f"\n- case_id={r.case_id} mode={r.mode}")
            print(f"  missing_keywords={r.missing_keywords}")
            print(f"  answer_preview={r.answer_preview}")

    return 0 if failed == 0 else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Day8：Harness engineering（评测/回归）")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(Path(__file__).with_name("eval_questions_day8.jsonl")),
        help="jsonl 数据集路径",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    cases = _load_jsonl_cases(Path(args.dataset))
    if not cases:
        print("数据集为空，退出。")
        return 2
    return run_eval(cases)


if __name__ == "__main__":
    raise SystemExit(main())

