"""
================================================================================
Day 7 —— LangGraph 架构入门：构建可控的 AI 工作流（学习型注释版）
================================================================================

写给初学者：本文件在讲什么？
----------------------------
LangGraph 是 LangChain 团队推出的「**有向无环图（DAG）**」式 AI 工作流框架。
你可以把它想象成「**流水线装配图**」：

1. **节点（Node）**：每个步骤，如「分析用户问题」「调用搜索工具」「生成答案」
2. **边（Edge）**：节点之间的连线，决定「走完 A 之后下一步去 B 还是 C」
3. **状态（State）**：沿着边传递的「流水」，包含问题、上下文、中间结果等

为什么需要 LangGraph？
----------------------
- **可观测**：每一步都有日志，方便调试
- **可循环**：支持「while True」这类条件循环（如 Agent 自动调用工具直到满意）
- **可持久化**：自带 checkpoint，程序中断后可从断点恢复（生产级特性）
- **可解释**：整个流程是「图」，不是「黑盒代码」

对比之前学的 Agent（Day1~4）
---------------------------
- **Agent**：模型自己决定「下一步调什么工具」
- **LangGraph**：开发者用代码明确定义「A 之后走 B，除非 C 条件满足才走 D」

换句话说：
- Agent = 让模型「自动驾驶」
- LangGraph = 让开发者「手动驾驶」+ 必要时让模型辅助决策

前置条件
--------
- Ollama 运行中（``ollama serve``），模型与 ``study01/llm.py`` 默认一致（如 qwen3:8b）
- 已安装 langgraph：``pip install langgraph``

运行示例
--------
    python -m study01.day7 simple          # 最简单的单向流水线
    python -m study01.day7 with-tools      # 带工具调用的工作流
    python -m study01.day7 conditional     # 带条件分支的工作流
    python -m study01.day7 loop            # 带循环的工作流（类似 Agent）

建议阅读顺序（学习路径）
-----------------------
1. 先看「核心概念」：理解 State、Node、Edge 是什么
2. 看 ``simple_graph``：最基础的「线性」流水线
3. 看 ``tool_graph``：加入「工具调用」节点
4. 看 ``conditional_graph``：加入「if-else」分支
5. 看 ``loop_graph``：实现「反复调用工具直到成功」的 Agent 行为
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Sequence

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from study01.llm import create_llm


# =============================================================================
# 一、LangGraph 核心概念：State（状态）
# =============================================================================
#
# State 是沿着图的边「流动」的数据结构。
# 它是一个字典（或 dataclass），每个节点可以读取、添加、修改其中的字段。
#
# 为什么用 TypedDict / dataclass？
# - 让 IDE 知道有哪些字段、类型是什么，代码提示更准确
# - LangGraph 会根据类型做「状态合并」验证
# =============================================================================


# 定义一个简单的「对话状态」
# - messages: 对话历史（LangChain 标准格式）
# - question: 用户原始问题
# - answer: 最终答案（生成后添加）
@dataclass
class SimpleState:
    """
    最简单的状态结构：只包含对话历史。

    学习要点：
    - field(default_factory=list)：让 messages 默认为空列表（而不是 None）
    - 这种结构适合「纯 LLM 调用」的简单流水线
    """
    messages: list = field(default_factory=list)


# 带工具调用结果的状态
@dataclass
class ToolState:
    """
    带工具调用信息的状态。

    fields:
        question: 用户的问题
        context: 从工具获取的上下文信息
        answer: 最终生成的答案
        tool_calls: 记录调用了哪些工具（用于调试/日志）
    """
    question: str = ""
    context: str = ""
    answer: str = ""
    tool_calls: list = field(default_factory=list)


# =============================================================================
# 二、LangGraph 核心概念：Node（节点）与 State 更新
# =============================================================================
#
# Node = Python 函数，输入 current_state，返回 updated_state（或部分更新）
#
# LangGraph 的「状态合并」机制：
# - 每个节点返回「部分状态」
# - 图引擎会把返回值 **合并** 到原状态上（类似 dict.update）
# - 例如：原状态 {a:1, b:2}，节点返回 {b:3, c:4} → 合并后 {a:1, b:3, c:4}
# =============================================================================


def greet_node(state: SimpleState) -> dict:
    """
    第一个节点：生成问候语。

    学习要点：
    - 输入：当前状态（包含 messages）
    - 输出：更新后的状态（添加新的 messages）
    - 这里直接返回新消息，下一个节点会看到完整的 messages
    
    注意：LangGraph 推荐返回 dict 而不是 dataclass，这样可以正确合并到状态中
    """
    llm = create_llm()
    system_msg = SystemMessage(content="你是一个友好的AI助手。请用一句话问候用户。")
    response = llm.invoke([system_msg])
    print(f"  [greet_node] 生成了回复: {response.content[:50]}...")
    return {"messages": [response]}


def chat_node(state: SimpleState) -> dict:
    """
    第二个节点：根据对话历史生成回复。

    学习要点：
    - 输入的 state.messages 包含之前所有消息
    - 直接把完整的 messages 传给 LLM
    - 返回新的 messages（会合并到状态中）
    """
    llm = create_llm()
    print(f"  [chat_node] 收到的 messages 数量: {len(state.messages)}")
    response = llm.invoke(state.messages)
    return {"messages": [response]}


# =============================================================================
# 三、LangGraph 核心概念：Edge（边）与图的构建
# =============================================================================
#
# Edge = 节点之间的连线，决定「谁之后走谁」
#
# 边的类型：
# 1. START → Node：入口边
# 2. Node → END：结束边
# 3. Node → Node：普通连线
# 4. Node → (Node1, Node2)：条件分支（函数返回值决定走哪条）
#
# 构建方式：
# - compiler.add_node(...)：添加节点
# - compiler.add_edge(...)：添加普通边
# - compiler.add_conditional_edges(...)：添加条件边
# =============================================================================


# -----------------------------
# 3.1 最简单的线性图（Simple Linear Graph）
# -----------------------------
#
# 流程：greet_node → chat_node → END
# 特点：无分支、无循环，纯线性
#


def build_simple_graph():
    """
    构建最简单的单向流水线。

    学习要点：
    - StateGraph：LangGraph 的核心类
    - .add_node(名字, 函数)：注册一个节点
    - .add_edge(起点, 终点)：添加单向连线
    - .set_entry_point(入口)：设置起点
    - .set_finish_point(终点)：设置终点（可省略，任意无出边的节点都会结束）
    - .compile()：编译成可执行的图
    """
    from langgraph.graph import END, StateGraph

    # 创建图，指定状态类型
    graph = StateGraph(SimpleState)

    # 注册节点
    graph.add_node("greet", greet_node)
    graph.add_node("chat", chat_node)

    # 设置入口：START → greet
    graph.set_entry_point("greet")

    # 设置流向：greet → chat → END
    graph.add_edge("greet", "chat")
    graph.add_edge("chat", END)

    # 编译成可运行对象
    return graph.compile()


# -----------------------------
# 3.2 带工具调用的图（Tool Calling Graph）
# -----------------------------
#
# 流程：问题 → 判断是否需要工具 → (是)调用工具 → 生成答案 → END
#                         └→ (否)直接生成答案 → END
#


@tool
def search_knowledge(query: str) -> str:
    """
    一个模拟的「知识库搜索」工具。

    学习要点：
    - @tool 装饰器：LangChain 的工具定义方式
    - 工具函数要有类型标注和文档字符串（LangChain 会自动解析）
    - 返回值必须是字符串（LangGraph 会把字符串转成 ToolMessage）
    """
    # 模拟知识库返回（实际项目这里会调用 Milvus/ES/数据库等）
    knowledge_db = {
        "python": "Python 是一种高级编程语言，创始人是 Guido van Rossum。",
        "langgraph": "LangGraph 是 LangChain 推出的有向无环图工作流框架。",
        "AI": "AI = Artificial Intelligence，人工智能。",
    }
    for key, value in knowledge_db.items():
        if key in query.lower():
            return value
    return "未找到相关信息。"


def question_node(state: ToolState) -> dict:
    """
    节点1：记录用户问题。

    返回字典（部分状态更新），LangGraph 会自动合并到 state 上。
    """
    return {"question": state.question}


def should_use_tool(state: ToolState) -> Literal["use_tool", "direct_answer"]:
    """
    条件节点：判断是否需要调用工具。

    学习要点：
    - 这是一个「路由器」函数
    - 返回值必须是字符串，对应图中另一个节点的名字
    - 这里用 LLM 判断，也可以用规则/正则

    返回值含义：
    - "use_tool"：去调用工具
    - "direct_answer"：直接生成答案
    """
    llm = create_llm()
    prompt = f"""用户问题是：「{state.question}」
    
这个问题是否需要查询外部知识库才能回答？请只回答 "需要" 或 "不需要"。"""

    response = llm.invoke([HumanMessage(content=prompt)])
    content = (response.content or "").strip().lower()

    if "需要" in content or "yes" in content:
        return "use_tool"
    return "direct_answer"


def use_tool_node(state: ToolState) -> dict:
    """
    节点2：调用工具获取上下文。

    学习要点：
    - 这里**直接调用工具函数**拿到结果（最直观，便于理解）。
    - 你在 Day1~Day4 见到的「LLM 自动选择工具并调用」属于 Function Calling / Agent 执行器的能力；
      而本节点的目标是演示“工作流里某一步明确要查知识库”，因此直接调用即可。
    - 等你理解清楚后，可以再升级成：
        1) 先让 LLM 产生工具调用（tool_calls）
        2) 再由图中的 ToolNode/执行器去执行工具
      那是更贴近真实 Agent 的做法，但对初学者更绕。
    """
    # 直接拿到工具结果文本（这里的工具是“模拟知识库检索”）
    context = search_knowledge.invoke({"query": state.question})

    return {
        "context": str(context),
        "tool_calls": [search_knowledge.name],
    }


def direct_answer_node(state: ToolState) -> dict:
    """节点3：不需要工具时，直接生成答案。"""
    llm = create_llm()
    response = llm.invoke([HumanMessage(content=state.question)])
    return {"answer": response.content or ""}


def generate_answer_node(state: ToolState) -> dict:
    """
    节点4：根据上下文生成最终答案。

    学习要点：
    - 无论之前走哪条分支，最后都会汇聚到这里
    - state.context 可能来自工具调用，也可能来自之前的消息
    """
    llm = create_llm()

    # 构建提示词
    if state.context:
        prompt = f"""根据以下上下文，回答用户问题。

上下文：{state.context}

问题：{state.question}

请给出回答。"""
    else:
        prompt = state.question

    response = llm.invoke([HumanMessage(content=prompt)])
    return {"answer": response.content or ""}


def build_tool_graph():
    """
    构建带条件分支的工具调用图。

    学习要点：
    - add_conditional_edges：条件边
      - 第一个参数：源节点名
      - 第二个参数：路由器函数
      - 第三个参数：可能的分支映射（返回值 → 目标节点）
    - add_edge 可以用 tuple 指定多个终点（但条件边更灵活）
    """
    from langgraph.graph import END, StateGraph

    graph = StateGraph(ToolState)

    # 注册节点
    graph.add_node("question", question_node)
    graph.add_node("use_tool", use_tool_node)
    graph.add_node("direct_answer", direct_answer_node)
    graph.add_node("generate_answer", generate_answer_node)

    # 设置入口
    graph.set_entry_point("question")

    # 条件分支：question 之后走 should_use_tool 判断
    graph.add_conditional_edges(
        "question",
        should_use_tool,
        {
            "use_tool": "use_tool",
            "direct_answer": "direct_answer",
        }
    )

    # 两条分支最终都汇入 generate_answer
    graph.add_edge("use_tool", "generate_answer")
    graph.add_edge("direct_answer", "generate_answer")

    # 结束
    graph.add_edge("generate_answer", END)

    return graph.compile()


# -----------------------------
# 3.3 带循环的图（Loop Graph）- 实现简易 Agent
# -----------------------------
#
# 流程：
#   START → evaluate → (需要更多步) → act → evaluate → ...
#                        (已完成) → END
#
# 这是 LangGraph 最强大的特性：让模型自己决定「再调用一次工具」
#


@dataclass
class AgentState:
    """
    Agent 循环状态。

    fields:
        question: 用户问题
        steps: 记录执行了多少步（防止无限循环）
        max_steps: 最大步数限制
        tool_results: 工具调用结果列表
        final_answer: 最终答案
    """
    question: str = ""
    steps: int = 0
    max_steps: int = 3
    tool_results: list = field(default_factory=list)
    final_answer: str = ""
    # evaluate_node 会写入该字段，conditional edge 再根据它决定是否继续
    should_continue: bool = True


def evaluate_node(state: AgentState) -> dict:
    """
    评估节点：判断问题是否已解决。

    学习要点：
    - 这是 Agent 的「判断中枢」
    - 每次循环都会先判断「是否还需要继续」
    """
    llm = create_llm()
    prompt = f"""用户问题：「{state.question}」

已执行步骤：{state.steps}
工具返回结果：{state.tool_results}

请判断问题是否已经得到充分回答。请只回答 "已完成" 或 "继续"。"""

    response = llm.invoke([HumanMessage(content=prompt)])
    decision = (response.content or "").strip()

    if "已完成" in decision or "完成" in decision:
        return {"should_continue": False}
    return {"should_continue": True}


def act_node(state: AgentState) -> dict:
    """
    执行节点：调用工具获取更多信息。

    学习要点：
    - 每次 act 都会让 steps +1
    - 这里简化：每次都调用搜索工具（实际 Agent 会根据上下文选择不同工具）
    """
    llm = create_llm()
    llm_with_tools = llm.bind_tools([search_knowledge])

    # 构造上下文
    context = "\n".join(state.tool_results) if state.tool_results else "无"
    prompt = f"""用户问题：「{state.question}」

已有信息：{context}

请基于问题调用合适的工具获取更多信息。"""

    response = llm_with_tools.invoke([HumanMessage(content=prompt)])

    new_result = response.content or ""
    new_steps = state.steps + 1

    return {
        "steps": new_steps,
        "tool_results": state.tool_results + [new_result]
    }


def final_answer_node(state: AgentState) -> dict:
    """生成最终答案。"""
    llm = create_llm()

    context = "\n".join(state.tool_results) if state.tool_results else "无"
    prompt = f"""基于以下信息，给出最终答案：

{context}

用户问题：{state.question}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return {"final_answer": response.content or ""}


def build_loop_graph():
    """
    构建带循环的 Agent 图。

    学习要点：
    - add_conditional_edges 的第二个返回值为布尔/字符串
    - 这里用 {"continue": "act", "end": "final_answer"} 映射
    - act → evaluate 形成循环
    - 当 should_continue=False 时，跳出循环走向 final_answer
    """
    from langgraph.graph import END, StateGraph

    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("act", act_node)
    graph.add_node("final_answer", final_answer_node)

    # 设置入口：先评估
    graph.set_entry_point("evaluate")

    # 条件边：evaluate → (继续) act 或 (结束) final_answer
    graph.add_conditional_edges(
        "evaluate",
        # 路由函数：把当前状态映射到下一跳节点名
        #
        # 学习要点：
        # - “是否继续”有两个维度：
        #   1) LLM 评估：state.should_continue
        #   2) 安全阈值：state.steps < state.max_steps（防止死循环）
        #
        # - 与本文件早些时候的 should_use_tool 类似：返回值要能映射到下面的分支表
        lambda state: "continue"
        if state.should_continue and state.steps < state.max_steps
        else "end",
        {
            "continue": "act",
            "end": "final_answer",
        }
    )

    # act 之后回到 evaluate（形成循环）
    graph.add_edge("act", "evaluate")

    # 最终答案后结束
    graph.add_edge("final_answer", END)

    return graph.compile()


# =============================================================================
# 四、运行入口：命令行界面
# =============================================================================


def run_simple():
    """运行最简单的线性图示例。"""
    print("\n" + "=" * 50)
    print("示例1：最简单的 LangGraph 流水线")
    print("=" * 50)

    graph = build_simple_graph()

    # initial_state：初始状态（空消息列表）
    # flow：执行流程（可迭代），每个元素是 (节点名, 该节点返回的状态)
    initial_state = SimpleState(messages=[])
    for step in graph.stream(initial_state):
        node_name = list(step.keys())[0]
        node_output = step[node_name]
        print(f"\n【{node_name}】输出：")
        # 支持 dataclass 和 dict 两种返回格式
        if hasattr(node_output, "messages"):
            for msg in node_output.messages:
                print(f"  - {msg.content}")
        elif isinstance(node_output, dict) and "messages" in node_output:
            for msg in node_output["messages"]:
                print(f"  - {msg.content}")


def run_with_tools():
    """运行带工具调用的条件分支图。"""
    print("\n" + "=" * 50)
    print("示例2：带工具调用的条件分支图")
    print("=" * 50)

    graph = build_tool_graph()

    # 测试问题1：需要查询知识库的
    print("\n--- 测试问题：什么是 LangGraph？ ---")
    result = graph.invoke({"question": "什么是 LangGraph？"})
    print(f"\n最终答案：{result.get('answer', '')}")
    print(f"工具调用：{result.get('tool_calls', [])}")
    print(f"上下文：{result.get('context', '')}")

    # 测试问题2：不需要工具的
    print("\n--- 测试问题：你好吗？ ---")
    result = graph.invoke({"question": "你好吗？"})
    print(f"\n最终答案：{result.get('answer', '')}")
    print(f"工具调用：{result.get('tool_calls', [])}")


def run_conditional():
    """运行条件分支示例（与 run_with_tools 共用逻辑）。"""
    run_with_tools()


def run_loop():
    """运行带循环的 Agent 示例。"""
    print("\n" + "=" * 50)
    print("示例3：带循环的 Agent 工作流")
    print("=" * 50)

    graph = build_loop_graph()

    result = graph.invoke({
        "question": "请介绍一下 Python 编程语言的特点",
        "max_steps": 2,
    })

    print(f"\n【最终答案】{result.get('final_answer', '')}")
    print(f"【执行步数】{result.get('steps', 0)}")
    print(f"【工具调用结果】")
    for i, r in enumerate(result.get("tool_results", []), 1):
        print(f"  步骤{i}: {r[:100]}...")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    命令行入口。

    学习要点：
    - subparsers：支持多个子命令（类似 git commit）
    - 每个子命令对应一个运行函数
    """
    parser = argparse.ArgumentParser(description="Day7：LangGraph 架构入门")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("simple", help="最简单的线性流水线")
    sub.add_parser("with-tools", help="带工具调用的条件分支图")
    sub.add_parser("conditional", help="条件分支示例（与 with-tools 相同）")
    sub.add_parser("loop", help="带循环的 Agent 工作流")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.cmd == "simple":
        run_simple()
    elif args.cmd == "with-tools":
        run_with_tools()
    elif args.cmd == "conditional":
        run_conditional()
    elif args.cmd == "loop":
        run_loop()
    else:
        print(f"未知命令: {args.cmd}", file=sys.stderr)
        return 1

    return 0


# `if __name__ == "__main__"`：只有直接运行本文件时才执行 main
if __name__ == "__main__":
    raise SystemExit(main())
