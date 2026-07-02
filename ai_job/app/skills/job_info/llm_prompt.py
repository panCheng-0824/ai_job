"""大模型分析阶段的提示词构造。"""

from __future__ import annotations

from typing import Optional

from app.skills.job_info.constants import DEFAULT_SCORE_BASELINE
from app.skills.job_info.llm_schema import format_recom_schema_for_prompt
from app.skills.job_info.score_rubric import (
    DEFAULT_SCORE_DIMENSIONS,
    dimensions_total,
    format_dimensions_for_prompt,
    normalize_score_dimensions,
)

ANALYSIS_SYSTEM = (
    "你是高校就业岗位推荐结构化助手。严格根据用户提供的知识库素材输出 JSON，"
    "不要输出素材以外的岗位信息。推荐理由必须具体、可核查，并解释评分依据。"
)


def build_analysis_prompt(
    user_query: str,
    student_context: str,
    retrieval_context: str,
    *,
    score_baseline: int = DEFAULT_SCORE_BASELINE,
    use_student_profile: bool = True,
    score_dimensions: Optional[dict] = None,
    include_json_schema: bool = False,
) -> str:
    """用户消息：原问题 + 画像 + 知识库素材 + JSON 字段说明。

    ``include_json_schema=True`` 时追加 ``RECOM_JSON_SCHEMA``（用于 ``json_object`` 模式）。
    """
    ctx = (student_context or "").strip()
    if use_student_profile and ctx:
        ctx_block = f"\n\n【学生画像补充】\n{ctx}"
    elif not use_student_profile:
        ctx_block = (
            "\n\n【访问模式】游客模式：未关联学生档案，仅依据【用户原问题】与【知识库素材】匹配，"
            "勿假设具体专业、学历或院校。"
        )
    else:
        ctx_block = ""
    material = (retrieval_context or "").strip()
    baseline = max(0, min(100, int(score_baseline or DEFAULT_SCORE_BASELINE)))
    dims = normalize_score_dimensions(score_dimensions or DEFAULT_SCORE_DIMENSIONS)
    dim_total = dimensions_total(dims)
    dim_block = format_dimensions_for_prompt(dims)
    profile_hint = (
        "【用户原问题】与【学生画像补充】"
        if use_student_profile and ctx
        else "【用户原问题】"
    )

    base = (
        "你是高校就业指导助手。请**仅依据**下方【知识库素材】分析，不得编造素材中不存在的岗位或数据。\n"
        "知识库文档 id 常为 job-<岗位ID>，<岗位ID> 与业务 job_id 一致。\n\n"
        f"【用户原问题】\n{user_query.strip()}"
        f"{ctx_block}\n\n"
        f"【知识库素材】\n{material}\n\n"
        "【分析要求】\n"
        f"在生成 JSON 前，先对照{profile_hint}，逐条阅读素材中的岗位信息。"
        "每条 recomList 的 reason 必须让人「看得懂为何推荐、为何是这个分数」，"
        "像就业顾问写给学生的匹配说明，而非空泛套话（禁止仅写「专业对口」「高度匹配」「已推荐」等）。\n\n"
        f"【评分体系】本次满分 {dim_total} 分，{baseline} 分表示「良好匹配」参考线："
        f"综合达到该线可视为值得推荐；明显短板应低于 {baseline} 分，"
        f"高度契合且素材充分时可高于 {baseline} 分。\n\n"
        f"【评分维度】（score 满分 {dim_total}；素材缺项则该维度降分并说明「素材未提及」）\n"
        f"{dim_block}\n"
        f"score 须与上述分析自洽：明显不匹配（如专业完全无关）不应给 {baseline} 分以上；"
        "有明确短板须在 reason 中扣分并说明。\n\n"
        "【输出要求】\n"
        "1) 只输出一个合法 JSON 对象，不要 markdown 围栏、不要注释、不要其它说明。\n"
        "2) 字段：isrecommend 取 yes 或 on 表示推荐；"
        "reason 为总体说明（120–250 字，概括筛选逻辑、与学生画像的整体契合度及主要取舍，勿写「已推荐」敷衍）；"
        "recomList 为数组，元素必含 jobId、jonName、score、reason；"
        "若素材中有则尽量填写 city、companyName、salaryRange（勿编造）。按 score 从高到低排列。\n"
        "3) jobId 必须来自素材中出现的岗位 ID，不要编造。\n"
        "4) recomList[].reason **不少于 300 个汉字**（不含空格），必须按以下四段标题撰写，"
        "**标题原样保留**（供页面分段展示，四段缺一不可，每段充分展开）：\n"
        "   【匹配结论】说明为何将该岗纳入推荐（结合学生画像与诉求，≥60 字）；\n"
        "   【评分依据】按五维逐条写出「维度名 X/Y 分 + 依据」（须覆盖全部维度及分值构成，≥80 字）；\n"
        "   【素材依据】至少引用 3 条素材具体事实（职责、技能、学历、薪资、地点、企业等，逐条说明与学生的关联，≥100 字）；\n"
        "   【差异提示】写明差距、风险或需补强之处；若高度匹配也需说明依据（≥60 字）。\n"
        "5) 禁止编造素材中不存在的薪资、城市、企业名、职责；无信息则写「素材未提供」。\n"
        "6) 字数不足 300 字视为不合格，须补充素材引用与维度分析后再输出。\n"
        "示例（reason 字段须达到 300 字以上，此处为结构示意）："
        '{"isrecommend":"yes","reason":"总体说明示例","recomList":[{"jobId":"<id>","score":88,"jonName":"<名>",'
        '"reason":"【匹配结论】示例正文…【评分依据】示例正文…【素材依据】示例正文…【差异提示】示例正文…",'
        '"city":"<城市>","companyName":"<公司>","salaryRange":"<薪资>"}]}'
    )
    if include_json_schema:
        base += "\n\n" + format_recom_schema_for_prompt()
    return base


def analysis_system_message(*, use_structured_format: bool) -> str:
    """系统消息；json_object 模式需在提示中出现 JSON 字样。"""
    if use_structured_format:
        return ANALYSIS_SYSTEM + " 请只输出一个 JSON 对象，字段遵循用户消息中的 schema 说明。"
    return ANALYSIS_SYSTEM
