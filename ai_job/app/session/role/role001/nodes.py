"""
ROLE001 LangGraph 节点实现。

图拓扑::

    intent_router → job_recommend → END
                 └→ planner → executor → … → structured_return | plain_finalize → END

各节点通过 ``GraphBindings`` 读取 LLM、工具、角色约束；通过 ``JobPlanExecuteState`` 读写进度。
"""

from __future__ import annotations

import logging
from typing import List, Literal

from langchain_core.messages import HumanMessage

from app.portal.schemas import JobInfoQueryRequest
from app.session.role.role001.bindings import GraphBindings, is_cancelled
from app.session.role.role001.intent import Role001Intent, classify_role001_intent
from app.session.role.role001.parsing import parse_plan_json, parse_structured_blob
from app.session.role.role001.state import JobPlanExecuteState
from app.skills.job_info.agent_tool import (
    format_job_info_query_markdown,
    run_job_info_query_sync,
    to_job_recommend_client_payload,
)

log = logging.getLogger(__name__)


def make_intent_router_node(bindings: GraphBindings):
    """
    入口路由器：写入 ``state.intent``，供条件边选择快车道或慢车道。

    若流式入口已预分类（``state.intent`` 非空且非默认值冲突），则尊重已有值；
    否则根据用户原句 + 历史摘录 + ``intent_mode``，由 LLM（失败则规则）分类。
    """

    def intent_router_node(state: JobPlanExecuteState) -> dict:
        if is_cancelled(bindings):
            return {"intent": "career_consult", "plan": ["（用户已中止）"]}

        preset = (state.intent or "").strip()
        if preset in ("job_recommend", "career_consult"):
            return {"intent": preset}

        intent: Role001Intent = classify_role001_intent(
            state.user_query or state.question,
            history_block=bindings.history_block,
            intent_mode=bindings.intent_mode,
            llm=bindings.llm,
        )
        return {"intent": intent}

    return intent_router_node


def route_after_intent_router(state: JobPlanExecuteState) -> Literal["recommend", "consult"]:
    """意图路由条件边：``job_recommend`` → 快车道节点；否则 → planner（慢车道）。"""
    if (state.intent or "").strip() == "job_recommend":
        return "recommend"
    return "consult"


def make_job_recommend_node(bindings: GraphBindings):
    """
    岗位推荐快车道：直接调用 ``run_job_info_query_for_agent``（LightRAG + LLM），
    将 Markdown 写入 ``final_answer``，不经过 planner / executor 多步规划。
    """

    def job_recommend_node(state: JobPlanExecuteState) -> dict:
        if is_cancelled(bindings):
            return {
                "final_answer": "（已中止）",
                "plan": ["（岗位推荐已中止）"],
                "observations": [],
            }

        query = (state.user_query or "").strip()
        if not query:
            return {
                "final_answer": "请补充岗位方向、城市、技能或薪资等关键词，以便为你检索推荐岗位。",
                "plan": ["（查询为空）"],
                "observations": ["用户未提供可检索的推荐意图"],
            }

        student_context = (state.student_context or "").strip()
        client_payload: dict = {}
        try:
            payload = JobInfoQueryRequest(
                query=query,
                student_context=student_context,
                use_rag=True,
                use_semantic_cache=True,
            )
            raw = run_job_info_query_sync(payload)
            client_payload = to_job_recommend_client_payload(raw)
            markdown = format_job_info_query_markdown(raw)
            jobs = client_payload.get("jobs") if isinstance(client_payload.get("jobs"), list) else []
            if jobs:
                reason = str((client_payload.get("llm") or {}).get("reason") or "").strip()
                markdown = reason or "已根据你的诉求匹配以下岗位，请在推荐卡片中查看详情与理由。"
        except Exception as exc:
            log.warning("岗位推荐快车道执行失败: %s", exc, exc_info=True)
            markdown = f"岗位推荐服务暂时不可用：{exc}"
            client_payload = {}

        return {
            "intent": "job_recommend",
            "plan": ["根据学生背景与诉求检索知识库并生成结构化岗位推荐"],
            "step_index": 1,
            "observations": [markdown],
            "structured_payload": "",
            "final_answer": markdown,
            "job_recommend": client_payload,
        }

    return job_recommend_node


def make_planner_node(bindings: GraphBindings):
    """
    规划节点：将用户诉求拆成 3～6 个有序子步骤（JSON 字符串数组）。

    不负责代替规划师向用户寒暄或下结论，只产出「对话节奏」步骤列表。
    """

    def planner_node(state: JobPlanExecuteState) -> dict:
        if is_cancelled(bindings):
            return {
                "plan": ["（用户已中止）"],
                "step_index": 0,
                "observations": [],
                "structured_payload": "",
                "final_answer": "",
            }

        step4 = (
            "4) 后半段步骤必须包含：汇总观测 → 产出可供下一步封装为结构化 JSON 的小结素材（与「输出结构约束」语义对齐）。"
            if bindings.use_structured_return
            else "4) 后半段步骤必须包含：汇总观测 → 形成符合「输出结构约束」的对话式结论文稿要点（自然语言即可，无需按 JSON 字段排版）。"
        )
        prompt = f"""你是「对话规划助手」，只做**本轮对话内**的子步骤拆分，不代替岗位规划师直接对用户发言。
根据下列「角色配置约束」，把用户诉求拆成 3~6 个有序子步骤；动词开头、每条只承载一小块「对齐信息 / 比较选项 / 查证参考 / 归纳讨论点」。

──角色配置约束──
{bindings.role_block}

硬性要求：
1) 只输出一个 JSON 数组（字符串列表），不要数组以外的文字。
2) 步骤须体现配置中的「角色目标」与「核心能力」：例如对齐现状与目标、澄清约束、比较路径或赛道、结合工具了解市场岗位样本（仅作参考）、归纳待用户确认的信息等（以实际配置为准）；**不要**写成派发工单或强制投递执行清单。
3) 若配置中列出可调用工具：需快速查市场样本时用 query_job_info；仅为连通性时可安排 ping。
{step4}

用户完整上下文与目标：
{state.question}
"""
        response = bindings.llm.invoke([HumanMessage(content=prompt)])
        plan = parse_plan_json(response.content or "")
        return {
            "plan": plan,
            "step_index": 0,
            "observations": [],
            "structured_payload": "",
            "final_answer": "",
        }

    return planner_node


def make_executor_node(bindings: GraphBindings):
    """
    执行节点：逐步完成 ``plan[step_index]``。

  策略：
    - 有工具时对 LLM ``bind_tools``，由 Python 侧 ``invoke`` 每个 tool_call；
    - 无工具时退化为纯文本调用；
    - 单步工具异常不导致整图崩溃，错误写入观测。
    """

    def executor_node(state: JobPlanExecuteState) -> dict:
        if is_cancelled(bindings) or state.step_index >= len(state.plan):
            return {}

        step_text = state.plan[state.step_index]
        llm_step = bindings.llm.bind_tools(bindings.tools) if bindings.tools else bindings.llm

        done_summary = "\n".join(
            f"- 步骤{i + 1} 观测：{obs}"
            for i, obs in enumerate(state.observations)
        ) or "（尚无）"
        tool_names = sorted(bindings.tool_map.keys())
        tool_hint = "、".join(tool_names) if tool_names else "（未配置：仅用文本完成本步）"

        prompt = f"""你在推进多步**对话式规划**中的「当前这一步」：完成本子步骤内的推理或工具查证即可，不要越权替用户决定或一次性写完终稿。
需要外部事实时，必须调用已注册工具（当前运行时可绑定的工具：{tool_hint}）。

──角色配置约束（必须遵守，尤其禁止话题与须规避项）──
{bindings.role_block}

用户总目标与系统设定（含历史等）：
{state.question}

完整规划子步骤：
{state.plan}

当前仅处理第 {state.step_index + 1} 步：
{step_text}

已完成步骤观测摘要：
{done_summary}

若本步需要配置中的工具能力，请正确传参调用；若无工具可完成，则用简短中文给出本子步骤的结论与局限。语气保持规划师协作对话，不把用户写成待执行任务。不要评价用户为人；不主动推荐具体公司（若配置如此要求）。
"""
        ai_msg = llm_step.invoke([HumanMessage(content=prompt)])
        chunks: List[str] = []
        if ai_msg.content:
            chunks.append(str(ai_msg.content).strip())

        for call in getattr(ai_msg, "tool_calls", None) or []:
            name = call.get("name")
            args = call.get("args") or {}
            tool_fn = bindings.tool_map.get(str(name))
            if tool_fn is None:
                chunks.append(f"[tool:{name}] 未注册")
                continue
            try:
                result = tool_fn.invoke(args)
            except Exception as exc:  # noqa: BLE001 — 单步失败不中断整图
                result = f"工具执行异常：{exc}"
            chunks.append(f"[{name}] {result}")

        observation = "\n".join(chunks).strip() or "（本步无输出）"
        return {
            "step_index": state.step_index + 1,
            "observations": state.observations + [observation],
        }

    return executor_node


def make_structured_return_node(bindings: GraphBindings):
    """结构化收尾：将步骤与观测压缩为 JSON + 用户可读 summary。"""

    def structured_return_node(state: JobPlanExecuteState) -> dict:
        if is_cancelled(bindings):
            return {
                "structured_payload": "{}",
                "final_answer": "（已中止，未生成结构化结果）",
            }

        lines = "\n".join(
            f"子步骤 {i + 1}/{len(state.plan)} — {state.plan[i]}\n观测：{obs}\n"
            for i, obs in enumerate(state.observations)
        )
        ident = bindings.identity
        out_fmt = str(ident.get("output_format", "")).strip()
        out_fmt_line = (
            f"summary 的正文结构必须与配置中的「输出结构约束」一致，配置原文为：{out_fmt}"
            if out_fmt
            else "summary 须专业、分点清晰，便于用户直接阅读。"
        )
        usercode = str(ident.get("usercode", "")).strip()
        username = str(ident.get("username", "")).strip()

        prompt = f"""基于下列对话规划步骤与工具观测，输出「仅一个 JSON 对象」，不要 Markdown、不要代码围栏外文字。

──角色配置约束（summary 与 JSON 内容必须遵守）──
{bindings.role_block}

JSON 键必须有（键名固定；语义按岗位规划师理解，与「输出结构约束」对齐）：
- summary：字符串，给用户看的完整小结；{out_fmt_line}
- job_directions：字符串数组，规划中的岗位/赛道/路径选项或标签。
- match_reasons：字符串数组，支撑选项的**分析要点与依据**（勿写推销式「匹配话术」）。
- risk_notes：字符串数组，风险与不确定处；无则 []。
- action_items：字符串数组，建议的**下一步对话或轻量探索**；避免项目经理式硬任务清单，除非用户明确要求投递步骤。
- evidence_from_observations：字符串数组，每条概括一条关键观测或工具返回要点。
- optional_context：对象，可含 heat_hint、supply_hint、trend_hint 等字符串字段；若无相关信息则各为空字符串。
- meta：对象，必须包含：
  - username: "{username}"
  - usercode: "{usercode}"
  - output_format: 复制配置中的输出结构原文（若无则空字符串）
  - plan_steps: 字符串数组，与下列子步骤顺序一致
  - data_source_note: 简述依据来自哪些工具或观测，不得声称真实企业内幕；若工具返回含演示说明须如实反映

用户完整上下文与目标：
{state.question}

计划与观测：
{lines}
"""
        response = bindings.llm.invoke([HumanMessage(content=prompt)])
        pretty, summary = parse_structured_blob(response.content or "")
        user_face = summary or "（模型未给出 summary 字段，请查看结构化 JSON）"
        final = (
            f"{user_face}\n\n"
            f"---结构化数据（JSON）---\n"
            f"```json\n{pretty}\n```"
        )
        return {"structured_payload": pretty, "final_answer": final}

    return structured_return_node


def make_plain_finalize_node(bindings: GraphBindings):
    """Markdown 收尾：根据步骤与观测生成对话式结论，不产出 JSON 代码块。"""

    def plain_finalize_node(state: JobPlanExecuteState) -> dict:
        if is_cancelled(bindings):
            return {"structured_payload": "", "final_answer": "（已中止）"}

        lines = "\n".join(
            f"子步骤 {i + 1}/{len(state.plan)} — {state.plan[i]}\n观测：{obs}\n"
            for i, obs in enumerate(state.observations)
        )
        ident = bindings.identity
        out_fmt = str(ident.get("output_format", "")).strip()
        out_fmt_line = (
            f"正文分段顺序应尽量对齐配置中的「输出结构约束」：{out_fmt}"
            if out_fmt
            else "正文须专业、分点清晰，便于用户直接阅读。"
        )

        prompt = f"""你是岗位规划师的「对话小结助手」。根据下列规划子步骤与各步观测，写出给用户看的完整结论。
仅输出 Markdown 正文（可用标题与列表）；不要输出 JSON；不要用代码围栏包裹全文。
口吻像聊天里的规划师：协作、分步对齐，避免代办执行清单体。

──角色配置约束（必须遵守）──
{bindings.role_block}

写作要求：{out_fmt_line}
须基于观测如实归纳；不得捏造岗位或企业内幕；若工具返回标明演示/示例须如实说明。

用户完整上下文与目标：
{state.question}

规划子步骤与观测：
{lines}
"""
        response = bindings.llm.invoke([HumanMessage(content=prompt)])
        text = str(response.content or "").strip()
        return {"structured_payload": "", "final_answer": text or "（模型未生成正文）"}

    return plain_finalize_node


def make_executor_router(bindings: GraphBindings):
    """
    executor 之后的路由：仍有步骤则继续 executor；
    否则按配置进入 structured_return 或 plain_finalize。
    """

    def route(state: JobPlanExecuteState) -> Literal["more", "structure", "plain"]:
        if state.step_index < len(state.plan):
            return "more"
        return "structure" if bindings.use_structured_return else "plain"

    return route
