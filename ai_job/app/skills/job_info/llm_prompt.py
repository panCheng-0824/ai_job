"""大模型分析阶段的提示词构造。"""

from __future__ import annotations

import re

from app.skills.job_info.constants import LLM_MATERIAL_MAX

ANALYSIS_SYSTEM = (
    "你是高校就业岗位推荐结构化助手。严格根据用户提供的知识库素材输出 JSON，"
    "不要输出素材以外的岗位信息。"
)


def build_analysis_prompt(
    user_query: str, student_context: str, retrieval_context: str
) -> str:
    """用户消息：原问题 + 画像 + 知识库素材 + JSON 字段说明。"""
    ctx = (student_context or "").strip()
    ctx_block = f"\n\n【学生画像补充】\n{ctx}" if ctx else ""
    material = (retrieval_context or "").strip()


    return (
        "你是高校就业指导助手。请**仅依据**下方【知识库素材】分析，不得编造素材中不存在的岗位或数据。\n"
        "知识库文档 id 常为 job-<岗位ID>，<岗位ID> 与业务 job_id 一致。\n\n"
        f"【用户原问题】\n{user_query.strip()}"
        f"{ctx_block}\n\n"
        f"【知识库素材】\n{material}\n\n"
        "【输出要求】\n"
        "1) 只输出一个合法 JSON 对象，不要 markdown 围栏、不要注释、不要其它说明。\n"
        "2) 字段：isrecommend 取 yes 或 on 表示推荐；reason 为总体原因；"
        "recomList 为数组，元素必含 jobId、jonName、score、reason；"
        "若素材中有则尽量填写 city、companyName、salaryRange（勿编造）。按匹配度从高到低排列。\n"
        "3) jobId 必须来自素材中出现的岗位 ID，不要编造。\n"
        "示例："
        '{"isrecommend":"yes","reason":"已推荐","recomList":['
        '{"jobId":"<id>","score":88,"jonName":"<名>","reason":"<岗位推荐的理由，一定要详细有序，有根据>",'
        '"city":"<城市>","companyName":"<公司>","salaryRange":"<薪资>"}]}'
    )


def analysis_system_message(*, use_structured_format: bool) -> str:
    """系统消息；json_object 模式需在提示中出现 JSON 字样。"""
    if use_structured_format:
        return ANALYSIS_SYSTEM + " 请只输出一个 JSON 对象，字段遵循用户消息中的 schema 说明。"
    return ANALYSIS_SYSTEM
