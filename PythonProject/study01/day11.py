"""
================================================================================
Day 11 —— LangGraph Plan-and-Execute（先规划、再分步执行）学习 Demo
================================================================================

本文件讲什么？
--------------
Plan-and-Execute（规划后执行）核心思想是 **把「怎么做」和「去做」拆开**：

1. **Planner（规划器）**：先看用户目标，把它拆成若干有序子步骤（Plan）
2. **Executor（执行器）**：一次只做当前这一步，可调用工具拿到 Observation
3. **Synthesizer（综合器）**：所有步骤跑完后，把各步观测汇总成最终答案

和 Day10 ReAct 的对比（非常重要）
---------------------------------
- **ReAct**：每一步「推理」与「是否调用工具」高度交织，像边想边做；循环由「模型是否继续
  发起 tool_calls」自然驱动。
- **Plan-and-Execute**：先得到一张「路线图」（Plan），再按步骤推进；结构更清晰，便于加
  日志、限步、人工审批某一步；缺点是计划可能不适应中途新信息（高阶做法会加 replanner，
  本 Demo 保持最小可运行版本）。

图结构（帮助你脑补 LangGraph）
------------------------------
::

    ┌─────────┐     ┌──────────┐   未完成下一步    ┌──────────┐
    │ planner │ ──► │ executor │ ───────────────► │ executor │ ...
    └─────────┘     └──────────┘                   └──────────┘
                           │
                           │ 全部步骤完成
                           ▼
                    ┌────────────┐
                    │ synthesizer│ ──► END
                    └────────────┘

前置条件
--------
- ``langgraph``、``study01/llm.py`` 可用（同 Day10）

运行方式
--------
在项目根目录：

    python -m study01.day11 "查上海气温，并把摄氏度换算提示写出来，再算 (10+1)*3"

可加 ``--quiet`` 跳过逐步打印。
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from typing import Any, List, Literal, Optional, Sequence

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from study01.llm import create_llm


# =============================================================================
# 一、工具定义（与 Day10 类似，便于对照实验）
# =============================================================================
#
# Plan-and-Execute 的执行器会在「单步任务描述」下调用它们；工具本身不必关心全局 Plan。
# =============================================================================


@tool
def get_city_temperature(city: str, unit: str = "celsius") -> str:
    """
    查询指定城市的「模拟」当日气温（演示用）。

    Args:
        city: 城市名，如 "上海"。
        unit: celsius 或 fahrenheit。
    """
    table = {
        "合肥": 22,
        "hefei": 22,
        "上海": 24,
        "shanghai": 24,
        "北京": 18,
        "beijing": 18,
    }
    key = city.strip().lower()
    c = None
    for k, v in table.items():
        if k.lower() in key or key in k.lower():
            c = v
            break
    if c is None:
        c = 20
    if unit.lower().startswith("f"):
        fahr = round(c * 9 / 5 + 32)
        return f"模拟数据：{city} 今日约 {fahr}°F（演示）"
    return f"模拟数据：{city} 今日约 {c}°C（演示）"


@tool
def calculator(expression: str) -> str:
    """计算仅含数字、+-*/与括号的算术表达式。"""
    allowed = set("0123456789+-*/(). ")
    if not expression or any(ch not in allowed for ch in expression):
        return "错误：表达式包含不允许的字符。"
    try:
        value = eval(expression, {"__builtins__": {}}, {})
        return str(value)
    except Exception as exc:  # noqa: BLE001
        return f"计算失败：{exc}"


# 方便在执行器里按名字查找工具（教学代码直截了当；生产可注册表 / ToolNode）
_TOOLS = [get_city_temperature, calculator]
_TOOL_MAP = {t.name: t for t in _TOOLS}


# =============================================================================
# 二、图状态：Plan / 进度 / 每步观测 / 最终答案
# =============================================================================
#
# 我们沿用 Day7 的风格：dataclass + 节点返回 dict 做「部分更新」。
#
# 字段含义：
# - question：用户原始目标（全程不变，供 planner / synthesizer 引用）
# - plan：规划得到的步骤列表，例如 ["查气温", "做运算"]
# - step_index：下一个要执行的步骤下标（0-based）；当它 == len(plan) 表示执行完毕
# - observations：与步骤顺序对齐的文本观测（每一步执行器追加一条）
# - final_answer：综合器写入
# =============================================================================


@dataclass
class PlanExecuteState:
    """Plan-and-Execute 状态容器。"""

    question: str = ""
    plan: List[str] = field(default_factory=list)
    step_index: int = 0
    observations: List[str] = field(default_factory=list)
    final_answer: str = ""


def _parse_plan_json(text: str) -> List[str]:
    """
    从模型输出中抽出 JSON 数组（字符串列表）。

    学习要点：
    - 真实项目常用 ``with_structured_output`` / Pydantic；这里用手动解析降低依赖门槛
    - 若解析失败，退化为「整段文本当作一步」，保证图仍能跑通
    """
    raw = text.strip()
    # 兼容 ```json ... ``` 代码块
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            out = [x.strip() for x in data if x.strip()]
            return out if out else [raw]
    except json.JSONDecodeError:
        pass
    return [raw] if raw else ["（规划为空，请用户补充目标）"]


def planner_node(state: PlanExecuteState) -> dict:
    """
    规划节点：把用户目标拆成 2~5 个可执行子步骤。

    学习要点：
    - 输出写入 ``plan``，并把 ``step_index`` 归零、清空 ``observations`` / ``final_answer``
    - 这是典型「批处理式规划」；若你希望中途改计划，可扩展为 replan 节点（超出本 Demo）
    """
    llm = create_llm()
    prompt = f"""你是任务规划助手。请将用户目标拆解为 2~5 个清晰子步骤，按执行顺序排列。
每个子步骤一句话，动词开头，避免含糊指代。

硬性要求：
1) 只输出一个 JSON 数组，元素为字符串；不要输出数组以外的文字。
2) 若需要气温等外部数据，要在某一步明确写出要查哪座城市。
3) 若需要数学计算，要在某一步写出要计算的表达式。

用户目标：
{state.question}
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    plan = _parse_plan_json(response.content or "")
    return {
        "plan": plan,
        "step_index": 0,
        "observations": [],
        "final_answer": "",
    }


def executor_node(state: PlanExecuteState) -> dict:
    """
    执行节点：只聚焦 ``plan[state.step_index]`` 这一步。

    学习要点：
    - **Scope 限制**：提示词强调「只完成当前步骤」，降低模型跑偏概率
    - **工具闭环**：若 AI 消息里携带 ``tool_calls``，我们在 Python 里逐个 invoke 工具，
      再把结果拼成一段 observation 文本；这比 Day10 的「全自动 ReAct」更透明，便于单步调试
    """
    if state.step_index >= len(state.plan):
        return {}

    step_text = state.plan[state.step_index]
    llm = create_llm().bind_tools(_TOOLS)

    done_summary = "\n".join(
        f"- 步骤{i + 1} 观测：{obs}"
        for i, obs in enumerate(state.observations)
    ) or "（尚无）"

    prompt = f"""你在执行一个多步计划中的「其中一步」。不要执行其它步骤。

用户总目标：
{state.question}

完整计划（仅供上下文）：
{state.plan}

当前只完成这一步（第 {state.step_index + 1} 步）：
{step_text}

已完成步骤的观测摘要：
{done_summary}

若当前步需要气温或计算，请调用工具；否则直接用简短中文说明本步结果。
"""
    ai_msg = llm.invoke([HumanMessage(content=prompt)])

    chunks: List[str] = []
    if ai_msg.content:
        chunks.append(ai_msg.content.strip())

    tool_calls = getattr(ai_msg, "tool_calls", None) or []
    for call in tool_calls:
        name = call.get("name")
        args = call.get("args") or {}
        tool_fn = _TOOL_MAP.get(name)
        if tool_fn is None:
            chunks.append(f"[tool:{name}] 未注册")
            continue
        try:
            result = tool_fn.invoke(args)
        except Exception as exc:  # noqa: BLE001
            result = f"工具执行异常：{exc}"
        chunks.append(f"[{name}] {result}")

    observation = "\n".join(chunks).strip() or "（本步无输出）"

    return {
        "step_index": state.step_index + 1,
        "observations": state.observations + [observation],
    }


def synthesizer_node(state: PlanExecuteState) -> dict:
    """
    综合节点：读取全部 observations，生成给用户看的最终答复。

    学习要点：
    - 这里不再调用工具；只做「信息聚合与表述」
    - 若你发现答案质量不佳，优先尝试：改进 planner 指令、或在 executor 加强单步约束
    """
    llm = create_llm()
    lines = "\n".join(
        f"步骤 {i + 1}/{len(state.plan)} — {state.plan[i]}\n观测：{obs}\n"
        for i, obs in enumerate(state.observations)
    )
    prompt = f"""基于下列「计划与观测」，用中文给出完整、简洁的最终答案。
不要提及 JSON、不要复述系统提示；若观测里有“模拟数据”，要向用户说明这是演示数据。

用户目标：
{state.question}

{lines}
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"final_answer": (response.content or "").strip()}


def route_after_executor(state: PlanExecuteState) -> Literal["more", "summarize"]:
    """
    条件路由：是否还有未执行步骤。

    学习要点：
    - 返回值必须是下面 dict 的 key之一（LangGraph 用它选中下一节点）
    - ``step_index`` 表示「下一步索引」，当它小于 ``len(plan)`` 说明还要继续执行
    """
    if state.step_index < len(state.plan):
        return "more"
    return "summarize"


def build_plan_execute_graph():
    """
    编译 Plan-and-Execute 状态图。

    学习要点：
    - ``add_conditional_edges`` 把 executor 后面拆成两条边：自环（继续执行）或进入综合
    - 与 ReAct 不同：这里的循环次数上限天然由 ``len(plan)`` 约束（更安全、更可预测）
    """
    from langgraph.graph import END, StateGraph

    graph = StateGraph(PlanExecuteState)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "more": "executor",
            "summarize": "synthesizer",
        },
    )
    graph.add_edge("synthesizer", END)
    return graph.compile()


def _as_plan_state(question: str, data: Any) -> PlanExecuteState:
    """把 invoke/stream 吐出来的 dict 或 dataclass 统一成 PlanExecuteState。"""
    if isinstance(data, PlanExecuteState):
        return data
    if isinstance(data, dict):
        return PlanExecuteState(
            question=str(data.get("question") or question),
            plan=list(data.get("plan") or []),
            step_index=int(data.get("step_index", 0)),
            observations=list(data.get("observations") or []),
            final_answer=str(data.get("final_answer") or ""),
        )
    raise TypeError(f"无法解析状态，类型为 {type(data)!r}")


def run_plan_execute(question: str, *, verbose: bool = True) -> PlanExecuteState:
    """执行整张图并返回最终状态（含 final_answer）。"""
    graph = build_plan_execute_graph()
    config = {"recursion_limit": 48}

    initial = PlanExecuteState(question=question)
    if verbose:
        print("\n" + "=" * 60)
        print("【Plan-and-Execute】stream_mode=\"values\"：每步之后打印完整状态快照")
        print("=" * 60)
        # stream_mode="values"：每次产出「合并后的全量状态」，最后一条即为最终结果（仅一次图执行）
        last: Optional[PlanExecuteState] = None
        for step_i, snapshot in enumerate(
            graph.stream(initial, config=config, stream_mode="values"), start=1
        ):
            st = _as_plan_state(question, snapshot)
            last = st
            print(f"\n--- 快照 #{step_i}（每跑完一个节点会追加一次）---")
            if st.plan:
                print("当前计划：")
                for i, p in enumerate(st.plan):
                    print(f"  {i + 1}. {p}")
            print(f"进度 step_index={st.step_index} / {len(st.plan)}")
            if st.observations:
                print("累计观测：")
                for i, o in enumerate(st.observations):
                    tail = "..." if len(o) > 300 else ""
                    print(f"  [{i + 1}] {o[:300]}{tail}")
            if st.final_answer:
                fa = st.final_answer[:200] + ("..." if len(st.final_answer) > 200 else "")
                print(f"final_answer（若已有）：{fa}")
        if last is None:
            raise RuntimeError("stream 未产生任何状态")
        return last

    result = graph.invoke(initial, config=config)
    return _as_plan_state(question, result)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Day11：LangGraph Plan-and-Execute")
    parser.add_argument(
        "question",
        nargs="?",
        default="帮我查上海的气温（摄氏度），再计算 (10 + 1) * 3 等于多少。",
        help="用户目标（默认内置复合示例）",
    )
    parser.add_argument("--quiet", action="store_true", help="不打印 stream 过程")
    args = parser.parse_args(list(argv) if argv is not None else None)

    print("\n【用户目标】", args.question)
    final_state = run_plan_execute(args.question, verbose=not args.quiet)
    print("\n【最终答案】\n", final_state.final_answer or "（空）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
