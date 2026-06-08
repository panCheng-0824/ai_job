"""大模型分析阶段的提示词构造。"""

from __future__ import annotations

import re

from app.skills.job_info.constants import (
    DEFAULT_MIN_RECOMMEND_SCORE,
    DEFAULT_SCORE_BASELINE,
    DEFAULT_TOP_N_JOBS,
    MAX_TOP_N_JOBS,
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
) -> str:
    """用户消息：原问题 + 画像 + 知识库素材 + JSON 字段说明。"""
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
    profile_hint = (
        "【用户原问题】与【学生画像补充】"
        if use_student_profile and ctx
        else "【用户原问题】"
    )

    return (
        "你是高校就业指导助手。请**仅依据**下方【知识库素材】分析，不得编造素材中不存在的岗位或数据。\n"
        "知识库文档 id 常为 job-<岗位ID>，<岗位ID> 与业务 job_id 一致。\n\n"
        f"【用户原问题】\n{user_query.strip()}"
        f"{ctx_block}\n\n"
        f"【知识库素材】\n{material}\n\n"
        "【分析要求】\n"
        f"在生成 JSON 前，先对照{profile_hint}，逐条阅读素材中的岗位信息。"
        "每条 recomList 的 reason 必须让人「看得懂为何推荐、为何是这个分数」，"
        "像就业顾问写给学生的匹配说明，而非空泛套话（禁止仅写「专业对口」「高度匹配」「已推荐」等）。\n\n"
        f"【评分基准】本次 {baseline} 分表示「良好匹配」参考线："
        f"综合达到该线可视为值得推荐；明显短板应低于 {baseline} 分，"
        f"高度契合且素材充分时可高于 {baseline} 分。\n\n"
        "【评分维度】（score 满分 100，须在 reason 中解释分数如何形成；素材缺项则该维度降分并说明「素材未提及」）\n"
        "1) 专业/方向对口（约 0–25）：岗位类别、职责与学生专业/诉求是否一致；\n"
        "2) 技能与职责匹配（约 0–25）：素材中的技能、软件、项目/职责要求与学生能力画像的吻合度；\n"
        "3) 门槛匹配（约 0–20）：学历、届别、经验、证书等硬性条件是否满足或可争取；\n"
        "4) 诉求匹配（约 0–15）：城市、薪资区间、行业、校招/社招等是否符合用户检索意图；\n"
        "5) 岗位质量（约 0–15）：企业规模、行业前景、岗位发展等（仅基于素材，勿臆测）。\n"
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
        "   【评分依据】逐维说明 score 加减分（专业/技能/门槛/诉求/岗位质量，写出分值构成，≥80 字）；\n"
        "   【素材依据】至少引用 3 条素材具体事实（职责、技能、学历、薪资、地点、企业等，逐条说明与学生的关联，≥100 字）；\n"
        "   【差异提示】写明差距、风险或需补强之处；若高度匹配也需说明依据（≥60 字）。\n"
        "5) 禁止编造素材中不存在的薪资、城市、企业名、职责；无信息则写「素材未提供」。\n"
        "6) 字数不足 300 字视为不合格，须补充素材引用与维度分析后再输出。\n"
        "示例（reason 字段须达到 300 字以上，此处为结构示意）："
        '{"isrecommend":"yes","reason":"总体说明示例","recomList":[{"jobId":"<id>","score":88,"jonName":"<名>",'
        '"reason":"【匹配结论】示例正文…【评分依据】示例正文…【素材依据】示例正文…【差异提示】示例正文…",'
        '"city":"<城市>","companyName":"<公司>","salaryRange":"<薪资>"}]}'
    )


def analysis_system_message(*, use_structured_format: bool) -> str:
    """系统消息；json_object 模式需在提示中出现 JSON 字样。"""
    if use_structured_format:
        return ANALYSIS_SYSTEM + " 请只输出一个 JSON 对象，字段遵循用户消息中的 schema 说明。"
    return ANALYSIS_SYSTEM
