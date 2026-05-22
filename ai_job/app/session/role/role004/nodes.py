"""
ROLE004 LangGraph 节点 — 简历优化建议 / 结构化简历生成。
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from langchain_core.messages import HumanMessage

from app.session.role.role004.intent import Role004Intent, classify_role004_intent
from app.session.role.role004.materials import build_generate_context_block, truncate_text
from app.session.role.role004.parsing import parse_resume_content_blob
from app.session.role.role004.resume_templates import (
    build_llm_json_schema_block,
    build_llm_template_guide,
    get_template,
)
from app.session.role.role004.state import ResumeOptimizeState
from app.session.role.role_util.bindings import GraphBindings, is_cancelled

log = logging.getLogger(__name__)


def _format_llm_error(exc: Exception) -> str:
    name = type(exc).__name__
    msg = str(exc).strip()
    if "Timeout" in name or "timed out" in msg.lower():
        return (
            "简历生成请求超时（模型响应过慢或素材过多）。"
            "请减少 OCR/岗位素材数量后重试，或在服务端提高 ROLE004_LLM_TIMEOUT_S（默认 120 秒）。"
        )
    return f"简历生成失败：{msg or name}"


def make_intent_router_node(bindings: GraphBindings):
    """入口路由器：写入 ``state.intent``。"""

    def intent_router_node(state: ResumeOptimizeState) -> dict:
        if is_cancelled(bindings):
            return {"intent": "resume_advise", "final_answer": "（已中止）"}

        preset = (state.intent or "").strip()
        if preset in ("resume_advise", "resume_generate"):
            return {"intent": preset}

        intent: Role004Intent = classify_role004_intent(
            state.user_query or state.question,
            history_block=bindings.history_block,
            materials_block=state.materials_block,
            intent_mode=bindings.intent_mode,
            llm=bindings.llm,
        )
        return {"intent": intent}

    return intent_router_node


def route_after_intent_router(state: ResumeOptimizeState) -> Literal["advise", "generate"]:
    if (state.intent or "").strip() == "resume_generate":
        return "generate"
    return "advise"


def make_resume_advise_node(bindings: GraphBindings):
    """优化建议通道：综合档案、素材与用户诉求，输出可对照替换的建议。"""

    def resume_advise_node(state: ResumeOptimizeState) -> dict:
        if is_cancelled(bindings):
            return {"final_answer": "（已中止）"}

        out_fmt = str(bindings.identity.get("output_format", "")).strip()
        out_line = (
            f"正文结构须对齐：{out_fmt}"
            if out_fmt
            else "须包含：原文 → 问题点 → 修改版 → 修改理由（可对多段分别给出）。"
        )

        context_block = build_generate_context_block(
            user_query=state.user_query,
            student_context=state.student_context,
            materials_block=state.materials_block,
        )
        tpl = get_template(state.template_id)
        template_guide = build_llm_template_guide(tpl.id)
        baseline_hint = ""
        if "左侧当前简历草稿" in (state.materials_block or ""):
            baseline_hint = (
                "素材中含「左侧当前简历草稿」：必须以该草稿各分段为优化对象，"
                "参考素材仅用于对齐岗位与润色，勿脱离草稿重写。\n"
            )
        prompt = f"""你是简历优化师，根据下列角色约束与用户上下文，给出**可直接替换到简历**的优化建议。
语气专业、精准、简洁；不否定用户原表达；不说「完全重写」。

──角色配置约束──
{bindings.role_block}

──目标模版（分段名须与左侧表单一致）──
{template_guide}

──输出要求──
{out_line}
{baseline_hint}对每段待优化内容给出「原文」与「改后」对照；改后须可直接复制进简历对应分段（键名：{'、'.join(tpl.section_keys)}）。

──用户诉求与素材（已压缩）──
{context_block}
"""
        try:
            response = bindings.llm.invoke([HumanMessage(content=prompt)])
            text = str(response.content or "").strip()
        except Exception as exc:
            log.warning("ROLE004 优化建议节点失败: %s", exc, exc_info=True)
            text = f"简历优化建议生成失败：{exc}"

        return {
            "intent": "resume_advise",
            "final_answer": text or "（模型未生成建议，请补充简历段落或优化诉求）",
            "resume_content": {},
        }

    return resume_advise_node


def make_resume_generate_node(bindings: GraphBindings):
    """生成通道：综合素材输出结构化简历 JSON，供前端渲染简历页。"""

    def resume_generate_node(state: ResumeOptimizeState) -> dict:
        if is_cancelled(bindings):
            return {"final_answer": "（已中止）", "resume_content": {}}

        tpl = get_template(state.template_id)
        template_guide = build_llm_template_guide(tpl.id)
        json_schema = build_llm_json_schema_block(tpl.id)
        context_block = build_generate_context_block(
            user_query=state.user_query,
            student_context=state.student_context,
            materials_block=state.materials_block,
        )
        prompt = f"""你是简历优化师，根据下列角色约束与素材，生成**一整份**可填入简历编辑器的中文简历。
只输出一个 JSON 对象，不要 Markdown 围栏外的文字；尽量简洁，避免冗长复述。

──角色配置约束──
{truncate_text(bindings.role_block, 6000)}

──模版与分段规范（必须严格遵守）──
{template_guide}

──JSON 根结构示例（键名与模版绑定）──
{json_schema}

要求：
1) 根对象必须包含 templateId="{tpl.id}"，且 sections 的键名与上文模版完全一致，不得使用其它模版的分段名。
2) 若素材中含「左侧当前简历草稿」，必须以该草稿为基准更新各分段，保留已有事实与结构，仅用参考素材润色、补全、对齐岗位关键词。
3) 基于素材与学生档案如实撰写，不捏造未出现的经历；可归纳整合 OCR 与岗位关键词。
4) 经历描述尽量量化成果；与目标岗位相关的关键词可适当突出。
5) sections 下每个模版分段至少一条记录；body 内用换行分条（- 开头）。

──素材与用户诉求（已去重压缩）──
{context_block}
"""
        try:
            response = bindings.llm.invoke([HumanMessage(content=prompt)])
            raw = str(response.content or "")
            resume_content, parse_err = parse_resume_content_blob(raw, template_id=tpl.id)
        except Exception as exc:
            log.warning("ROLE004 简历生成节点失败: %s", exc, exc_info=True)
            resume_content, parse_err = {}, _format_llm_error(exc)

        if parse_err:
            summary = (
                f"已根据素材生成简历结构，但解析需留意：{parse_err}\n\n"
                "下方为结构化数据，可在简历页导入或微调各段内容。"
            )
        else:
            summary = (
                "已根据你提供的素材生成结构化简历，内容已同步到简历渲染数据。"
                "请在左侧简历页查看各分段，可按需继续微调。"
            )

        pretty = json.dumps(resume_content, ensure_ascii=False, indent=2)
        final = f"{summary}\n\n---简历结构化数据（JSON）---\n```json\n{pretty}\n```"

        return {
            "intent": "resume_generate",
            "final_answer": final,
            "resume_content": resume_content,
        }

    return resume_generate_node
