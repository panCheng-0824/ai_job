"""
岗位信息查询（对外兼容入口）。

实现位于 ``app.skills.job_info`` 子包，本文件仅 re-export，保证既有 import 路径不变：

- ``web_app`` → ``run_job_info_query_async``（检索 + LLM + 可选语义缓存）
- ``lc_agent`` → ``recommend_jobs_and_companies_markdown`` / ``run_job_info_query_for_agent``

子模块说明见 ``app/skills/job_info/__init__.py``。
"""

from app.skills.job_info import (
    deal_data_by_llm,
    decorate_job_info_query_response,
    recommend_jobs_and_companies_async,
    recommend_jobs_and_companies_markdown,
    run_job_info_query_async,
    run_job_info_query_for_agent,
    run_job_info_query_sync,
)

__all__ = [
    "recommend_jobs_and_companies_async",
    "recommend_jobs_and_companies_markdown",
    "deal_data_by_llm",
    "run_job_info_query_async",
    "run_job_info_query_sync",
    "run_job_info_query_for_agent",
    "decorate_job_info_query_response",
]
