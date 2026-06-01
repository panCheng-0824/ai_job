"""
ROLE005 — 规划图（``compile_planner_graph``）各节点实现。

图状态类型：``PlannerGraphState``（素材文本、指纹、目标岗位、plan、cache_meta、error）。

执行顺序
--------
extract_materials → plan_cache → planner_llm → plan_summary → publish_plan_mq

设计要点
--------
- 缓存命中时 ``plan_cache`` 已写入 ``plan``，``planner_llm`` 检测到 ``state.plan`` 非空则跳过 LLM；
- 用户中止 SSE 时 ``bindings.cancel_event`` 置位，各节点通过 ``is_cancelled`` 提前返回 error 或空增量。
"""

from __future__ import annotations

from app.session.role.role005.agents.plan_cache import search_plan_cache
from app.session.role.role005.agents.planner import run_planner_agent
from app.session.role.role005.domain.state import PlannerGraphState
from app.session.role.role_util.bindings import GraphBindings, is_cancelled


def make_extract_materials_node(bindings: GraphBindings):
    """
    工厂：创建「素材入口」节点。

    业务含义
    --------
    规划图的**第一个节点**，不承担素材拼接（已在 ``stream_handlers/plan_preview`` 或
    API 层完成 ``build_interview_materials_block``），仅做：

    - 检查是否已取消流式请求；
    - 确认进入后续缓存/LLM 节点前流程未被中断。

    状态依赖
    --------
    调用 ``invoke`` 时初始 state 应已包含：

    - ``materials_text``：完整素材块；
    - ``material_hash``：``compute_material_hash`` 结果；
    - ``target_role``：``extract_target_role`` 结果；
    - ``student_context``：可选档案摘要。

    返回
    ----
    LangGraph 节点函数 ``(state) -> dict``，正常时返回空 dict（不修改 state）。
    """

    def node(state: PlannerGraphState) -> dict:
        if is_cancelled(bindings):
            # 前端停止生成：后续节点会因 state.error 或空 plan 失败
            return {"error": "已中止"}
        # 不在此节点重复解析 context_cards；避免与入口层职责重叠
        _ = state
        return {}

    return node


def make_plan_cache_node(bindings: GraphBindings):
    """
    工厂：创建「大纲语义缓存」节点。

    业务含义
    --------
    在调用昂贵 Planner LLM 之前，用 ``material_hash``（+ ``target_role``）检索是否已有
    相同/相似素材生成过的大纲（Milvus 向量库，P0 占位实现恒为未命中）。

    命中时
    ------
    向 state 合并 ``plan`` 与 ``cache_meta``（含 hit=True 等），``planner_llm`` 将跳过生成。

    未命中时
    --------
    仅更新 ``cache_meta``（如 hit=False、提示将生成新大纲），``plan`` 保持 None。
    """

    def node(state: PlannerGraphState) -> dict:
        if is_cancelled(bindings) or state.error:
            # 上游已报错或用户取消，不再访问缓存
            return {}
        cached, meta = search_plan_cache(state.material_hash, state.target_role)
        if cached is not None:
            # 缓存命中：直接复用 InterviewPlan，节省 token 与延迟
            return {"plan": cached, "cache_meta": meta}
        # 未命中：meta 供前端展示「将生成新大纲」等说明
        return {"cache_meta": meta}

    return node


def make_planner_llm_node(bindings: GraphBindings):
    """
    工厂：创建「Planner LLM 生成大纲」节点。

    业务含义
    --------
    规划图的**核心节点**：调用 ``run_planner_agent``，根据简历/岗位素材为目标岗位
    编排 8～10 道结构化面试题，产出 ``InterviewPlan``（每题含考查方向、深挖轴线、
    记录表入口说明等 eval_criteria；参考答案仅内部使用，不注入面试官 Prompt）。

    跳过条件
    --------
    - ``state.plan`` 已存在（``plan_cache`` 命中）；
    - 用户已取消请求。

    失败处理
    --------
    Agent 解析 JSON 失败或 Schema 校验不通过时，向 state 写入 ``error`` 文案，
    ``run_plan_preview_sync`` 最终抛出 ``RuntimeError``。
    """

    def node(state: PlannerGraphState) -> dict:
        if is_cancelled(bindings):
            return {"error": "已中止"}
        if state.plan is not None:
            # plan_cache 已写入大纲，本节点为 no-op（LangGraph 仍执行但无 LLM 开销）
            return {}
        plan, err = run_planner_agent(
            bindings,
            materials_block=state.materials_text,
            target_role=state.target_role,
            student_context=state.student_context,
            material_hash=state.material_hash,
            planner_model=str(bindings.identity.get("model_level") or ""),
        )
        if err or plan is None:
            return {"error": err or "规划失败"}
        # generated=True 标记本次为新算大纲，便于日志与 cache_meta 区分命中/新生成
        return {"plan": plan, "cache_meta": {**(state.cache_meta or {}), "generated": True}}

    return node
