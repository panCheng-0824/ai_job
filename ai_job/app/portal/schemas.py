"""门户 HTTP API 请求体模型（与路由层共用）。"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.skills.job_info.constants import (
    DEFAULT_MIN_RECOMMEND_SCORE,
    DEFAULT_SCORE_BASELINE,
    DEFAULT_TOP_N_JOBS,
    MAX_TOP_N_JOBS,
)


class ScoreDimensionWeights(BaseModel):
    """五维评分权重（各项上限之和通常为 100）。"""

    major: int = Field(default=25, ge=0, le=100, description="专业/方向对口")
    skill: int = Field(default=25, ge=0, le=100, description="技能与职责匹配")
    threshold: int = Field(default=20, ge=0, le=100, description="门槛匹配")
    intent: int = Field(default=15, ge=0, le=100, description="诉求匹配")
    quality: int = Field(default=15, ge=0, le=100, description="岗位质量")


class SessionInitRequest(BaseModel):
    """会话初始化请求体。"""

    session_id: str
    student_id: str
    usercode: str


class ChatMessageRequest(BaseModel):
    """会话消息请求体。"""

    message: str
    use_role_pipeline: bool = True
    use_adversarial_harness: bool = False
    adversarial_desc: str = ""


class ChatStreamMessageRequest(BaseModel):
    """流式会话消息（POST body，避免 GET URL 过长丢失 context_cards）。"""

    message: str = ""
    message_context: str = ""
    context_cards: List[Dict[str, Any]] = Field(default_factory=list)
    use_role_pipeline: bool = True
    use_adversarial_harness: bool = False
    adversarial_desc: str = ""


class InternalChatPayload(BaseModel):
    """无状态聊天请求：由 server_job 传入完整 history，不在此持久化会话。"""

    session_id: str
    student_id: str = ""
    usercode: str
    message: str
    message_context: str = ""
    context_cards: List[Dict[str, Any]] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    use_role_pipeline: bool = True
    use_adversarial_harness: bool = False
    adversarial_desc: str = ""


class JobInfoQueryRequest(BaseModel):
    """岗位信息查询请求体。"""

    query: str
    top_n_jobs: int = Field(default=DEFAULT_TOP_N_JOBS, ge=1, le=MAX_TOP_N_JOBS)
    top_n_companies: int = 3
    # 是否走 LightRAG（True）或 GrepRAG（False）；均仅返回检索上下文，岗位结构化由业务侧模型完成
    use_rag: bool = True
    student_context: str = ""
    # 是否将 student_context 带入改写与 LLM 分析；False 时为游客模式
    use_student_profile: bool = True
    # 良好匹配评分基准线（0–100），写入 LLM 提示词
    score_baseline: int = Field(default=DEFAULT_SCORE_BASELINE, ge=0, le=100)
    # 返回岗位最低 score 阈值（0–100），低于此分的条目会被过滤
    min_recommend_score: int = Field(default=DEFAULT_MIN_RECOMMEND_SCORE, ge=0, le=100)
    # 五维评分权重（写入 LLM 提示词；缺省 25/25/20/15/15）
    score_dimensions: Optional[ScoreDimensionWeights] = None
    # 是否使用语义相似缓存（需服务端 JOB_INFO_SEM_CACHE_ENABLED=1）；默认 True
    use_semantic_cache: bool = True
    # 已废弃：LightRAG 固定 only_need_context，保留字段仅为 API 兼容
    only_need_context: bool = False
    # 兼容旧字段：为 True 时强制跳过缓存
    skip_cache: bool = False


class OCRRecognizeRequest(BaseModel):
    """OCR 识别请求体。"""

    image_path: str
    lang: str = "ch"
    use_angle_cls: bool = True


class OCRRecognizeUrlRequest(BaseModel):
    """OCR 图片链接识别请求体。"""

    image_url: str
    lang: str = "ch"
    use_angle_cls: bool = True


class VoiceSpeechRequest(BaseModel):
    """TTS：朗读指定文本。"""

    text: str
    model_level: str = "mid"
    voice: str = "serena"


class VoiceSpokenSummaryRequest(BaseModel):
    """对话完成后：chat 模型生成口语摘要，再 TTS 播报。"""

    answer_text: str
    chat_model_level: str = "mid"
    tts_model_level: str = "mid"
    voice: str = "serena"


class VoiceSpokenSummaryTextRequest(BaseModel):
    """仅解析将要朗读的文案。"""

    answer_text: str
    chat_model_level: str = "mid"


class AiSearchCrawlRequest(BaseModel):
    """智能网页采集（ai_search）请求体。"""

    url: str
    prompt: str = ""
    mode: str = "scrapy"
    max_pages: int = Field(default=5, ge=1, le=20)
    follow_links: bool = False
    link_selector: str = ""
    require_login: bool = False
