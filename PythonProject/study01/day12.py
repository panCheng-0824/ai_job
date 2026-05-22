"""
================================================================================
Day 12 —— LangGraph 工作流（Workflow）学习 Demo
================================================================================

本文件讲什么？
--------------
**工作流**在这里指：用一张 **有向图** 把业务拆成多个 **确定性顺序或分支节点**，
每一步读写共享状态；与 Day10「模型决定何时调工具」的 ReAct、与 Day11「先 Plan 再
循环 Executor」的范式不同，工作流强调 **人可读的控制流**（适合审批、风控、ETL、客服分级）。

本 Demo 场景（教学向）
--------------------
模拟「用户投稿 → 规范化 → 简易敏感词风控 → 安全则 LLM 起草并发布 / 不安全则拦截」：

::

    ┌───────────┐     ┌───────────┐     ┌────────────┐
    │ normalize │ ──► │ risk_scan │ ──► │ 条件路由    │
    └───────────┘     └───────────┘     └──────┬─────┘
                      │                      │
              未通过  │                      │ 通过
                      ▼                      ▼
               ┌────────────┐         ┌─────────┐     ┌─────────┐     END
               │  blocked   │         │  draft  │ ──► │ publish │
               └────────────┘         └─────────┘     └─────────┘

和 Day10 / Day11 的关系
-----------------------
- **Day10 ReAct**：循环由「是否还有 tool_calls」驱动，结构藏在预构建 Agent 里。
- **Day11 Plan-and-Execute**：Planner 产出步骤列表 + Executor 自环直到做完。
- **Day12 工作流**：分支边由 **你在代码里写的路由函数** 明确写出（本例结合简单规则）；
  需要时在某节点里再调用 LLM / 工具即可。

前置条件
--------
- ``langgraph``、``study01/llm.py`` 可用

运行方式
--------
在项目根目录：

    python -m study01.day12
    python -m study01.day12 "请介绍一下 Python 列表推导式"

``--quiet`` 只打印最终结果。
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Literal, Optional, Sequence

from langchain_core.messages import HumanMessage

from study01.llm import create_llm


# =============================================================================
# 一、状态：各节点通过返回 dict 做「部分更新」（与 Day11 一致）
# =============================================================================


@dataclass
class PublishWorkflowState:
    """简易「投稿发布」工作流状态。"""

    user_text: str = ""
    normalized_text: str = ""
    risk_passed: bool = True
    risk_reason: str = ""
    draft: str = ""
    final_output: str = ""


# 演示用敏感词表（非生产级）；命中则走 blocked 分支
_DEMO_BLOCKLIST: tuple[str, ...] = (
    "自杀教程",
    "制毒",
    "雇凶",
    "爆炸物制作",
)


def normalize_node(state: PublishWorkflowState) -> dict:
    """去掉多余空白，便于后续节点处理。"""
    text = (state.user_text or "").strip()
    collapsed = re.sub(r"\s+", " ", text)
    return {"normalized_text": collapsed}


def risk_scan_node(state: PublishWorkflowState) -> dict:
    """
    风控扫描（规则演示）：命中黑名单则 ``risk_passed=False``。

    学习要点：分支条件完全由代码定义，可替换为 API、模型分类器等。
    """
    body = state.normalized_text
    if not body:
        return {
            "risk_passed": False,
            "risk_reason": "空内容",
        }
    hit = next((w for w in _DEMO_BLOCKLIST if w in body), None)
    if hit:
        return {
            "risk_passed": False,
            "risk_reason": f"命中演示黑名单词：{hit}",
        }
    return {"risk_passed": True, "risk_reason": ""}


def route_after_risk(state: PublishWorkflowState) -> Literal["draft", "blocked"]:
    """条件边：是否允许进入起草。"""
    return "draft" if state.risk_passed else "blocked"


def draft_node(state: PublishWorkflowState) -> dict:
    """通过风控后，由模型生成一版面向读者的正文草稿（教学用）。"""
    llm = create_llm()
    prompt = f"""你是社区编辑助手。用户投稿如下，请整理成一段通顺、友好的正文（中文）。
不要编造事实；若内容过短可适当补充一句礼貌结语。控制在 200 字以内。

【投稿】
{state.normalized_text}
"""
    msg = llm.invoke([HumanMessage(content=prompt)])
    return {"draft": (msg.content or "").strip() or "（起草为空）"}


def publish_node(state: PublishWorkflowState) -> dict:
    """发布节点：本 Demo 直接把草稿对外输出（生产可做持久化、推送）。"""
    return {"final_output": state.draft}


def blocked_node(state: PublishWorkflowState) -> dict:
    """拦截分支：写入拒绝说明。"""
    reason = state.risk_reason or "未通过风控"
    return {"final_output": f"【未发布·演示】{reason}"}


def build_publish_workflow_graph():
    """编译工作流图。"""
    from langgraph.graph import END, StateGraph

    graph = StateGraph(PublishWorkflowState)
    graph.add_node("normalize", normalize_node)
    graph.add_node("risk_scan", risk_scan_node)
    graph.add_node("draft", draft_node)
    graph.add_node("publish", publish_node)
    graph.add_node("blocked", blocked_node)

    graph.set_entry_point("normalize")
    graph.add_edge("normalize", "risk_scan")
    graph.add_conditional_edges(
        "risk_scan",
        route_after_risk,
        {"draft": "draft", "blocked": "blocked"},
    )
    graph.add_edge("draft", "publish")
    graph.add_edge("publish", END)
    graph.add_edge("blocked", END)
    return graph.compile()


def _coerce_state(snapshot: object, fallback_text: str) -> PublishWorkflowState:
    if isinstance(snapshot, PublishWorkflowState):
        return snapshot
    if isinstance(snapshot, dict):
        return PublishWorkflowState(
            user_text=str(snapshot.get("user_text") or fallback_text),
            normalized_text=str(snapshot.get("normalized_text") or ""),
            risk_passed=bool(snapshot.get("risk_passed", True)),
            risk_reason=str(snapshot.get("risk_reason") or ""),
            draft=str(snapshot.get("draft") or ""),
            final_output=str(snapshot.get("final_output") or ""),
        )
    return PublishWorkflowState(user_text=fallback_text)


def run_workflow(user_text: str, *, verbose: bool = True) -> PublishWorkflowState:
    """执行工作流并返回最终状态。"""
    graph = build_publish_workflow_graph()
    config = {"recursion_limit": 24}
    initial = PublishWorkflowState(user_text=user_text)

    if verbose:
        print("\n" + "=" * 60)
        print("【工作流 stream_mode=\"values\"】每完成一个节点刷新一次状态快照")
        print("=" * 60)
        last: Optional[PublishWorkflowState] = None
        for step_i, snapshot in enumerate(
            graph.stream(initial, config=config, stream_mode="values"), start=1
        ):
            st = _coerce_state(snapshot, user_text)
            last = st
            print(f"\n--- 快照 #{step_i} ---")
            if st.normalized_text:
                nt = st.normalized_text[:200] + ("..." if len(st.normalized_text) > 200 else "")
                print(f"normalized_text: {nt}")
            print(f"risk_passed={st.risk_passed}  risk_reason={st.risk_reason or '（空）'}")
            if st.draft:
                d = st.draft[:300] + ("..." if len(st.draft) > 300 else "")
                print(f"draft: {d}")
            if st.final_output:
                fo = st.final_output[:300] + ("..." if len(st.final_output) > 300 else "")
                print(f"final_output: {fo}")
        if last is None:
            raise RuntimeError("stream 未产生状态")
        return last

    out = graph.invoke(initial, config=config)
    return _coerce_state(out, user_text)


DEFAULT_USER_TEXT = "大家好，我想分享一个小技巧：用列表推导式可以快速过滤列表中的偶数。"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Day12：LangGraph 工作流 Demo")
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        help="模拟用户投稿正文；省略时使用内置安全示例",
    )
    parser.add_argument("--quiet", action="store_true", help="不打印逐步快照")
    args = parser.parse_args(list(argv) if argv is not None else None)

    text = args.text if args.text is not None else DEFAULT_USER_TEXT
    print("\n【用户投稿】\n", text)
    final_state = run_workflow(text, verbose=not args.quiet)
    print("\n【工作流输出】\n", final_state.final_output or "（空）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
