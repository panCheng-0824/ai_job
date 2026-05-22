"""
================================================================================
Day 10 —— LangGraph ReAct 模式学习 Demo（预构建 Agent + 中文注释）
================================================================================

本文件讲什么？
--------------
ReAct（Reasoning + Acting）是一种经典的 Agent 范式：

1. **Thought（推理）**：模型用自然语言交代「我现在怎么想、下一步要做什么」
2. **Action（行动）**：模型发起工具调用（Tool / Function Call）
3. **Observation（观察）**：工具返回结果，写回对话历史
4. **重复**：直到模型认为可以给出最终答案为止（不再调用工具）

LangGraph 如何把这件事变成「图」？
----------------------------------
你不用从零手写「agent ↔ tools」循环：`langgraph.prebuilt.create_react_agent`
已经帮你搭好了标准拓扑（大致是：调用模型 → 若有 tool_calls 则执行工具 → 再回到模型 …）。

这与 Day7 手写 loop 的关系
--------------------------
- Day7 的 ``loop_graph``：教学用的「迷你循环」，帮助你理解「条件边 + 回边」
- Day10：工业界更常用的 **官方预构建 ReAct**，对接 LangChain 消息协议与 ToolNode

前置条件
--------
- 已安装 ``langgraph``（见项目 ``requirements.txt``）
- ``study01/llm.py`` 中的模型服务可用（默认本机 Ollama OpenAI 兼容接口）

运行方式
--------
在项目根目录：

    python -m study01.day10 "合肥明天大概多少度？"

    # 学生心理咨询：ReAct（工具自检）→ Reflection（审查草稿）→ 必要时修订后再审查 → 定稿
    python -m study01.day10 --counseling
    python -m study01.day10 --counseling "我最近考试前总是睡不着，很怕让父母失望。"

一般模式不传问题时有内置天气+计算示例；``--counseling`` 不传问题时有内置学生倾诉示例。

**重要**：心理咨询演示仅用于学习 ReAct 流程，不能替代专业心理服务；危机情况请通过现实渠道求助。
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Any, List, Literal, Optional, Sequence

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from study01.llm import create_llm


# =============================================================================
# 一、定义少量「教学向」工具（越简单越容易看清 ReAct 在干什么）
# =============================================================================
#
# 学习要点：
# - ``@tool`` 会把普通 Python 函数包装成 LangChain 的 BaseTool
# - 函数 docstring 会进入工具的 description，影响模型「选哪个工具」
# =============================================================================


@tool
def get_city_temperature(city: str, unit: str = "celsius") -> str:
    """
    查询指定城市的「模拟」当日气温（演示用，非真实气象接口）。

    Args:
        city: 城市中文或英文名，例如 "合肥"、"Shanghai"。
        unit: 温度单位，celsius（摄氏度）或 fahrenheit（华氏度）。

    Returns:
        一句包含气温说明的短文本。
    """
    # 刻意做成「查表 + 少量规则」，避免 Demo 依赖外部 HTTP，把注意力留在 ReAct 流程上。
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
    """
    计算一个简单的算术表达式（仅支持数字与 + - * / 和括号）。

    Args:
        expression: 例如 "(12 + 8) * 2"。

    Returns:
        计算结果字符串；若表达式不安全则返回错误说明。
    """
    allowed = set("0123456789+-*/(). ")
    if not expression or any(ch not in allowed for ch in expression):
        return "错误：表达式包含不允许的字符。"
    try:
        # 教学 Demo：eval 仅在接受白名单字符后使用；生产环境请换 AST / parser。
        value = eval(expression, {"__builtins__": {}}, {})
        return str(value)
    except Exception as exc:  # noqa: BLE001 —— 教学脚本保留宽泛捕获，打印友好错误
        return f"计算失败：{exc}"


# =============================================================================
# 二、学生心理咨询场景（内层 ReAct + 外层 Reflection）
# =============================================================================
#
# 设计意图：
# - **内层** ``build_counseling_react_graph``：``counselor_internal_checklist`` 要求回复前先工具自检；
#   ``campus_support_snippet`` 可选查演示话术。
# - **外层** ``build_counseling_reflect_graph``：``counsel`` 得到草稿 → ``reflect`` 用 JSON 审视草稿 →
#   未通过则 ``revise`` 再跑一轮内层 ReAct → 再 ``reflect``；至多修订一次后 ``finalize`` 定稿。
# - 若只想跑内层 ReAct、不要反思环，可调用 ``run_counseling_react``。
#
# 免责声明：以下为教学 Demo，不提供诊断或治疗；真人危机干预请勿依赖脚本输出。
# =============================================================================


@tool
def counselor_internal_checklist(student_need_summary: str, emotion_keywords: str) -> str:
    """
    在写出对学生的每一段正式回复之前，必须先调用本工具完成「思考步骤」。
    请用一两句话概括学生的诉求或处境，并列出你捕捉到的情绪关键词（如：焦虑、羞愧、孤独）。

    Args:
        student_need_summary: 你对学生当下诉求、压力的简短概括。
        emotion_keywords: 你认为突出的情绪或主题词，逗号分隔亦可。

    Returns:
        一段「回复前自检要点」供你在下一轮组织语言时使用（演示数据，非临床指引）。
    """
    summary = (student_need_summary or "").strip()
    emotions = (emotion_keywords or "").strip()
    combined = summary + emotions
    lines = [
        "【内部备忘·演示】",
        f"诉求概括：{summary or '（未填写）'}",
        f"情绪线索：{emotions or '（未填写）'}",
        "---",
        "回复前自检：",
        "1）先承认对方的感受，避免一上来就给大道理或贴标签；",
        "2）用开放式问题帮助 TA 具体化（例如「最坏会怎样」「你希望谁在」），但不要逼问细节；",
        "3）一段回复里建议控制在少量要点，语气温暖、平等；",
        "4）不做心理疾病诊断；若涉及无法忍受的痛苦或自伤/伤人念头，应明确建议尽快联系可信成人、学校心理中心或当地紧急/危机心理援助渠道。",
    ]
    urgent_markers = ("自杀", "自残", "不想活", "结束一切", "死了算了", "活不下去")
    if any(m in combined for m in urgent_markers):
        lines.append(
            "【演示级关键词提示】内容可能涉及严重风险：请优先建议立即联系身边可信成人或拨打所在地心理危机热线，"
            "避免仅停留在安慰句式；本脚本不能代替真人评估。"
        )
    return "\n".join(lines)


@tool
def campus_support_snippet(topic: str) -> str:
    """
    按主题查阅一段「校园心理支持」演示文案，便于在回复中酌情引用（虚构示例，非本校真实规定）。

    Args:
        topic: 主题关键词，如：学业压力、睡眠、人际冲突、家庭期望。

    Returns:
        一小段可融入对话的支持性表述示例。
    """
    key = (topic or "").strip().lower()
    table = {
        "学业": (
            "学业压力：许多人会在考试季睡不好或心慌，这不代表你不够努力。"
            "可以试试把任务拆成小块，并和学校信任的辅导员或班主任聊聊是否能调整节奏（演示文案）。"
        ),
        "睡眠": (
            "睡眠：压力常常打乱作息。固定起床时间、睡前减少刷题和手机有时能帮助身体放松（演示文案）。"
        ),
        "人际": (
            "人际：被孤立或吵架会让人很难受。你不必独自扛，可尝试与一位你感到安全的人慢慢说说（演示文案）。"
        ),
        "家庭": (
            "家庭期望：怕让父母失望很辛苦。可以练习用「我在乎你们，但我也很累」这样的句子表达边界（演示文案）。"
        ),
    }
    for k, text in table.items():
        if k in key or k.lower() in key:
            return f"【{k}·演示摘录】{text}"
    return (
        "【通用·演示摘录】学校通常有心理老师或辅导资源，你可以按自己舒适的速度了解；"
        "你愿意说出来，已经是在照顾自己了（演示文案）。"
    )


def build_react_agent_graph():
    """
    构建 ReAct Agent 对应的 CompiledStateGraph。

    学习要点：
    - ``create_react_agent(model, tools, prompt=...)`` 返回的是「已编译图」
    - ``prompt`` 可以是 str：框架会自动转成 SystemMessage 插在 messages 最前
    - 图的内部状态默认包含 ``messages``（对话轨迹）等字段；我们用 invoke 传入首条 HumanMessage 即可
    """
    from langgraph.prebuilt import create_react_agent

    llm = create_llm()
    tools = [get_city_temperature, calculator]

    system_prompt = """你是一个乐于助人的助手，必须使用中文回答最终结论。
在思考复杂问题时，可以先简要说明推理，再决定是否调用工具。
若用户问题需要外部数据（气温等），请调用工具，不要编造精确数字。
若只需简单计算，请调用 calculator。"""

    # version="v2" 为当前默认：工具调用在 ToolNode 中以更细粒度执行（见 LangGraph 文档说明）。
    graph = create_react_agent(llm, tools, prompt=system_prompt, debug=False)
    return graph


def build_counseling_react_graph():
    """构建「学生心理咨询」场景的 ReAct 图：依赖工具链体现「先思考、再开口」。"""
    from langgraph.prebuilt import create_react_agent

    llm = create_llm()
    tools = [counselor_internal_checklist, campus_support_snippet]

    system_prompt = """你是学校场景下的「学生心理辅导」对话助手（教学 Demo），必须用中文与学生交流。
核心流程（ReAct）：
1）每当学生说完一段，你在写出面向学生的回复正文之前，必须先调用工具 counselor_internal_checklist：
   传入你对诉求的概括与情绪关键词，拿到返回的自检要点后再组织语言。
2）若需要引用常见的校园支持表述，可再调用 campus_support_snippet；不需要则不必勉强调用。
3）对学生输出时：温暖、具体、少评判；不做精神障碍诊断；不要编造本校真实电话或政策。
4）最终给学生看的消息里，不要重复粘贴整段工具返回的技术性条目，用你自己的话自然表达。

【声明】你不是持证治疗师；若涉及严重心理危机，应明确建议联系现实中可信成人与专业/紧急援助渠道。"""

    return create_react_agent(llm, tools, prompt=system_prompt, debug=False)


def _extract_last_ai_text(messages: List[Any]) -> str:
    """从消息列表中取「最后一条无 tool_calls 的 AIMessage」正文（与 ReAct 最终回复约定一致）。"""
    last_text = ""
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            if not (getattr(m, "tool_calls", None) or []):
                last_text = (m.content or "").strip()
                if last_text:
                    break
    return last_text


def _print_messages_trace(messages: List[Any], *, trace_title: str) -> None:
    print("\n" + "=" * 60)
    print(trace_title)
    print("=" * 60)
    for i, m in enumerate(messages):
        name = m.__class__.__name__
        if name == "HumanMessage":
            print(f"{i:02d} [User] {m.content}")
        elif name == "AIMessage":
            tc = getattr(m, "tool_calls", None) or []
            if tc:
                print(f"{i:02d} [AI / 请求工具] {tc}")
            else:
                print(f"{i:02d} [AI / 最终回复] {m.content}")
        elif name == "ToolMessage":
            body = m.content if len(m.content) <= 200 else m.content[:200] + "..."
            print(f"{i:02d} [Tool 返回] {m.name}: {body}")
        else:
            print(f"{i:02d} [{name}] {m}")


def _invoke_agent_graph(
    graph,
    question: str,
    *,
    verbose: bool = True,
    recursion_limit: int = 32,
    trace_title: str = "【轨迹速览】ReAct 会在 messages 里累积 AIMessage / ToolMessage",
) -> str:
    """对任意 ``create_react_agent`` 编译图执行一次问答，打印可选轨迹并抽取最终 AI 文本。"""
    config = {"recursion_limit": recursion_limit}
    initial = {"messages": [HumanMessage(content=question)]}
    final_state = graph.invoke(initial, config=config)

    messages = final_state.get("messages") or []
    if verbose:
        _print_messages_trace(messages, trace_title=trace_title)

    last_text = _extract_last_ai_text(messages)
    return last_text or "（未能解析到明确文本回复，请查看上方轨迹）"


# =============================================================================
# 三、心理咨询 + Reflection（草案 → 审查 → 至多一次修订）
# =============================================================================
#
# 外层图：counsel（内层 ReAct）→ reflect（模型审视草稿）→ 不通过则 revise（再跑 ReAct）→ 再 reflect → finalize。
# 教学目的：展示「行动 / 工具」与「对草稿的二次评判」分属不同阶段。
# =============================================================================


@dataclass
class CounselingReflectState:
    """心理咨询流水线状态（ReAct 草稿 + 反思 + 定稿）。"""

    student_message: str = ""
    draft_reply: str = ""
    reflection_critique: str = ""
    reflection_ok: bool = False
    revision_round: int = 0
    final_reply: str = ""


def _coerce_counseling_reflect_state(
    snapshot: object,
    fallback_question: str,
) -> CounselingReflectState:
    """把 ``invoke`` / ``stream_mode='values'`` 的快照统一成 ``CounselingReflectState``。"""
    if isinstance(snapshot, CounselingReflectState):
        return snapshot
    if isinstance(snapshot, dict):
        return CounselingReflectState(
            student_message=str(snapshot.get("student_message") or fallback_question),
            draft_reply=str(snapshot.get("draft_reply") or ""),
            reflection_critique=str(snapshot.get("reflection_critique") or ""),
            reflection_ok=bool(snapshot.get("reflection_ok")),
            revision_round=int(snapshot.get("revision_round", 0)),
            final_reply=str(snapshot.get("final_reply") or ""),
        )
    return CounselingReflectState(student_message=fallback_question)


def _parse_reflect_json(text: str) -> tuple[bool, str]:
    """解析反思节点输出的 ``{\"pass\": bool, \"critique\": str}``。"""
    raw = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            ok = bool(data.get("pass"))
            critique = str(data.get("critique") or "").strip()
            return ok, critique or "（无具体说明）"
    except json.JSONDecodeError:
        pass
    return False, "（反思输出无法解析为 JSON，视为不通过）"


def counsel_node(state: CounselingReflectState) -> dict:
    """第一次（或唯一一次）走内层心理咨询 ReAct，得到给学生看的草稿。"""
    sub = build_counseling_react_graph()
    config = {"recursion_limit": 32}
    out = sub.invoke({"messages": [HumanMessage(content=state.student_message)]}, config=config)
    draft = _extract_last_ai_text(out.get("messages") or [])
    return {"draft_reply": draft or "（草稿为空）"}


def reflect_node(state: CounselingReflectState) -> dict:
    """Reflection：审视草稿是否足够共情、安全、未越界诊断；输出 pass + critique。"""
    llm = create_llm()
    prompt = f"""你是「心理咨询回复」的教学用反思审查员（不是治疗师）。
请阅读学生倾诉与辅导员草稿，判断草稿是否可以就这样发给学生。

审查维度（演示）：是否先接纳情绪而非说教；是否避免下诊断或贴标签；严重风险时是否提到现实中求助渠道；语气是否平等。

学生倾诉：
{state.student_message}

辅导员草稿：
{state.draft_reply}

请只输出一个 JSON 对象，两个键：
- pass：布尔值，true 表示可以通过；false 表示需要修订
- critique：字符串，中文简要写出问题与改进方向（pass 为 true 时可写「无明显问题」）

不要输出 JSON 以外的文字。"""
    response = llm.invoke([HumanMessage(content=prompt)])
    ok, critique = _parse_reflect_json(response.content or "")
    return {"reflection_ok": ok, "reflection_critique": critique}


def revise_node(state: CounselingReflectState) -> dict:
    """根据反思意见，再跑一轮内层 ReAct，生成修订稿。"""
    sub = build_counseling_react_graph()
    config = {"recursion_limit": 32}
    body = f"""【修订任务·教学 Demo】
学生原话：
{state.student_message}

你上一版给学生看的回复草稿：
{state.draft_reply}

反思审查意见（请针对性改进）：
{state.reflection_critique}

请重新回复学生：仍须先调用 counselor_internal_checklist，再写正文；不要重复上一版的明显问题。"""
    out = sub.invoke({"messages": [HumanMessage(content=body)]}, config=config)
    draft = _extract_last_ai_text(out.get("messages") or [])
    return {
        "draft_reply": draft or state.draft_reply,
        "revision_round": state.revision_round + 1,
    }


def finalize_node(state: CounselingReflectState) -> dict:
    """定稿：本 Demo 直接使用最后一版草稿（已通过反思或已达修订次数上限）。"""
    return {"final_reply": (state.draft_reply or "").strip() or "（空）"}


def route_after_reflect(state: CounselingReflectState) -> Literal["finalize", "revise"]:
    """已通过反思，或尚未修订过则可进入修订；否则强制定稿。"""
    if state.reflection_ok:
        return "finalize"
    if state.revision_round == 0:
        return "revise"
    return "finalize"


def build_counseling_reflect_graph():
    """心理咨询 ReAct + Reflection 外层图。"""
    from langgraph.graph import END, StateGraph

    graph = StateGraph(CounselingReflectState)
    graph.add_node("counsel", counsel_node)
    graph.add_node("reflect", reflect_node)
    graph.add_node("revise", revise_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("counsel")
    graph.add_edge("counsel", "reflect")
    graph.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {"finalize": "finalize", "revise": "revise"},
    )
    graph.add_edge("revise", "reflect")
    graph.add_edge("finalize", END)
    return graph.compile()


def run_counseling_with_reflection(student_message: str, *, verbose: bool = True) -> CounselingReflectState:
    """跑通 counsel → reflect → [revise → reflect] → finalize，返回最终状态。"""
    graph = build_counseling_reflect_graph()
    config = {"recursion_limit": 48}
    initial = CounselingReflectState(student_message=student_message)

    if verbose:
        print("\n" + "=" * 60)
        print("【心理咨询流水线】counsel(ReAct) → reflect → 必要时 revise → finalize")
        print("=" * 60)
        last: Optional[CounselingReflectState] = None
        for step_i, snapshot in enumerate(
            graph.stream(initial, config=config, stream_mode="values"), start=1
        ):
            st = _coerce_counseling_reflect_state(snapshot, student_message)
            last = st
            print(f"\n--- 快照 #{step_i} ---")
            if st.draft_reply:
                d = st.draft_reply[:400] + ("..." if len(st.draft_reply) > 400 else "")
                print(f"draft_reply: {d}")
            print(f"reflection_ok={st.reflection_ok}  revision_round={st.revision_round}")
            if st.reflection_critique:
                c = st.reflection_critique[:400] + ("..." if len(st.reflection_critique) > 400 else "")
                print(f"reflection_critique: {c}")
            if st.final_reply:
                fa = st.final_reply[:400] + ("..." if len(st.final_reply) > 400 else "")
                print(f"final_reply: {fa}")
        if last is None:
            raise RuntimeError("stream 未产生状态")
        return last

    out = graph.invoke(initial, config=config)
    return _coerce_counseling_reflect_state(out, student_message)


def run_react(question: str, *, verbose: bool = True) -> str:
    """
    运行 ReAct：返回模型最终面向用户的文本（尽力从末条 AIMessage 抽取）。

    学习要点：
    - ``invoke`` 会跑完整条图，直到「模型不再请求工具」为止
    - ``recursion_limit`` 防止异常情况下无限循环；可按任务调大/调小
    """
    graph = build_react_agent_graph()
    return _invoke_agent_graph(graph, question, verbose=verbose)


def run_counseling_react(student_message: str, *, verbose: bool = True) -> str:
    """
    心理咨询场景 ReAct：模型通常会先 ``counselor_internal_checklist``（思考/自检），再生成对学生的回复。
    """
    graph = build_counseling_react_graph()
    title = "【轨迹速览·心理咨询】关注是否先出现 checklist / support 的 ToolMessage，再出现最终回复"
    return _invoke_agent_graph(graph, student_message, verbose=verbose, trace_title=title)


DEFAULT_GENERAL_QUESTION = "合肥今天大概多少度？再帮我算一下 (18 + 5) * 2 是多少。"
DEFAULT_COUNSELING_STUDENT_MESSAGE = (
    "我最近考试前总是睡不着，心跳很快，又不敢跟爸妈说，怕他们觉得我矫情、让他们失望。"
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Day10：LangGraph ReAct（create_react_agent）")
    parser.add_argument(
        "question",
        nargs="?",
        default=None,
        help="要向 Agent 说的内容；省略时使用内置示例（一般模式或心理咨询模式各有一套默认）",
    )
    parser.add_argument(
        "--counseling",
        action="store_true",
        help="学生心理咨询：内层 ReAct（工具自检）+ 外层 Reflection（审查草稿，未通过则修订一轮）",
    )
    parser.add_argument("--quiet", action="store_true", help="只打印最终答案，不打印消息轨迹")
    args = parser.parse_args(list(argv) if argv is not None else None)

    verbose = not args.quiet
    if args.counseling:
        text = args.question if args.question is not None else DEFAULT_COUNSELING_STUDENT_MESSAGE
        print("\n【学生倾诉（演示）】\n", text)
        final_state = run_counseling_with_reflection(text, verbose=verbose)
        print("\n【定稿回复（演示）】\n", final_state.final_reply)
    else:
        text = args.question if args.question is not None else DEFAULT_GENERAL_QUESTION
        print("\n【问题】", text)
        answer = run_react(text, verbose=verbose)
        print("\n【最终答案】\n", answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
