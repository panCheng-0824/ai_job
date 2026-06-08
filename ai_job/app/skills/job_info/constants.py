"""
岗位推荐子模块：全局常量。

与 ``semantic_cache``、``retrieval_service``、``llm_prompt`` 等配合使用；
环境变量类配置见各模块文件头说明。
"""

# rag.answer_preview 截断长度；完整正文在 rag.retrieval_context
RETRIEVAL_PREVIEW_MAX = 16000

# 送入分析大模型的知识库素材最大字符数（超出则截断）
LLM_MATERIAL_MAX = 48000

# 检索 top_k = max(RETRIEVAL_TOP_K_MIN, top_n_jobs * RETRIEVAL_TOP_K_FACTOR)
RETRIEVAL_TOP_K_MIN = 40
RETRIEVAL_TOP_K_FACTOR = 4

# Agent 工具 recommend_jobs_and_companies_markdown 使用的 GrepRAG 条数
MARKDOWN_GREPRAG_TOP_K = 20

# 岗位推荐默认配置（与前端、JobInfoQueryRequest 一致）
DEFAULT_SCORE_BASELINE = 85
DEFAULT_MIN_RECOMMEND_SCORE = 85
DEFAULT_TOP_N_JOBS = 5
MAX_TOP_N_JOBS = 20
