"""
岗位信息查询子包。

流程
----
1. ``run_job_info_query_async``（HTTP 主路径）：改写 ctx → 语义缓存 → 检索 → LLM → 写缓存
2. ``recommend_jobs_and_companies_async``：仅改写 + 检索，返回 rag 素材（jobs 为空）
3. ``deal_data_by_llm``：在已有检索结果上做 LLM 分析
4. ``recommend_jobs_and_companies_markdown``：Agent 轻量检索（GrepRAG）Markdown
5. ``run_job_info_query_for_agent``：Agent 完整推荐（LightRAG + LLM）Markdown

模块划分
--------
- ``constants``：字符上限、top_k 等常量
- ``context``：RecommendRunCtx、请求字段读取
- ``retrieval_payload`` / ``kb_retrieval`` / ``retrieval_service``：检索
- ``llm_*``：大模型提示、调用、解析、jobs 映射
- ``recommendation``：前端 recommendation 块
- ``pipeline``：deal_data_by_llm / run_job_info_query_async 编排
- ``semantic_cache``：scope 分桶 + Redis + 向量余弦语义缓存
"""

from app.skills.job_info.agent_tool import run_job_info_query_for_agent, run_job_info_query_sync
from app.skills.job_info.pipeline import deal_data_by_llm, run_job_info_query_async
from app.skills.job_info.recommendation import decorate_response as decorate_job_info_query_response
from app.skills.job_info.retrieval_service import (
    build_recommend_ctx,
    recommend_from_ctx,
    recommend_jobs_and_companies_async,
    recommend_jobs_and_companies_markdown,
)

__all__ = [
    "recommend_jobs_and_companies_async",
    "recommend_jobs_and_companies_markdown",
    "deal_data_by_llm",
    "run_job_info_query_async",
    "run_job_info_query_sync",
    "run_job_info_query_for_agent",
    "decorate_job_info_query_response",
    "build_recommend_ctx",
    "recommend_from_ctx",
]
