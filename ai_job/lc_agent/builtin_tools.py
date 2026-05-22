"""
内置工具定义（与业务 Agent 解耦的「保底」工具集）。

说明：
- ``create_tool_calling_agent`` 要求 LLM 绑定至少若干 tools；若调用方未传自定义 tools，
  工厂会使用本模块提供的列表，避免「无工具可绑」的边缘情况；
- 这里的工具应尽量轻量、无副作用，便于本地/CI 连通性自检。

扩展方式：在本模块追加更多 ``@tool`` 函数，并在 ``build_default_tools`` 的列表中注册。
"""

from typing import Dict, List

from langchain_core.tools import BaseTool, tool

from app.portal.schemas import JobInfoQueryRequest
from app.skills.job_info import run_job_info_query_for_agent
from app.skills.job_info_query import recommend_jobs_and_companies_markdown


@tool
def ping() -> str:
    """当用户请求检查连通性、服务是否可用、或执行健康检查时，调用本工具。"""
    return "ok"


@tool
def query_job_info(query: str, student_context: str = "") -> str:
    """
    当岗位规划师仅需**快速查阅**知识库中的岗位/市场样本（无结构化推荐列表）时调用。
    走 GrepRAG 检索，返回检索素材 Markdown；适合对话中补充事实，不适合作为学生主页的最终岗位推荐。
    参数 query：岗位方向、城市、技能、薪资等关键词；student_context：可选的学生档案摘要。
    """
    return recommend_jobs_and_companies_markdown(query, student_context=student_context)


@tool
def query_job_info_by_lightrag(query: str, student_context: str = "") -> str:
    """
    当用户明确提出**岗位推荐**需求，或需根据学生背景给出结构化推荐列表时调用。
    走 LightRAG 检索 + 业务模型分析，返回推荐岗位 Markdown（含匹配理由）；结果为市场参考，不代表录用承诺。
    参数 query：检索与推荐意图（必填）；student_context：学生基本信息、专业、技能、期望城市等（建议填写）。
    """
    raw = (query or "").strip()
    if not raw:
        return "（查询为空：请在 query 中提供岗位方向、城市、技能或薪资等关键词）"
    payload = JobInfoQueryRequest(
        query=raw,
        student_context=(student_context or "").strip(),
        use_rag=True,
        use_semantic_cache=True,
    )
    return run_job_info_query_for_agent(payload)


@tool
def run_adversarial_harness_tool(
    role_ref: str,
    adversary_desc: str,
    question: str,
    max_rounds: int = 3,
) -> str:
    """
    当用户希望进行 AI 对抗迭代（生产者 vs 对抗者）以改进回答时，调用本工具。
    role_ref 可传 usercode 或 username；max_rounds 建议 1-10。
    """
    # 延迟导入，避免与 pipeline_llm -> lc_agent -> builtin_tools 形成循环依赖
    from app.skills.adversarial_harness import run_harness_and_render_markdown

    return run_harness_and_render_markdown(
        role_ref=role_ref,
        adversary_desc=adversary_desc,
        question=question,
        max_rounds=max_rounds,
    )


BUILTIN_TOOLS_BY_NAME: Dict[str, BaseTool] = {
    "ping": ping,
    "query_job_info": query_job_info,
    "query_job_info_by_lightrag": query_job_info_by_lightrag,
    "run_adversarial_harness_tool": run_adversarial_harness_tool,
}


def build_default_tools() -> List[BaseTool]:
    return [ping]


def build_builtin_tools_by_names(names: List[str]) -> List[BaseTool]:
    """按工具名构造内置工具列表；未知名称将被忽略。"""
    selected: List[BaseTool] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        tool_obj = BUILTIN_TOOLS_BY_NAME.get(name)
        if tool_obj is not None:
            selected.append(tool_obj)
    return selected
