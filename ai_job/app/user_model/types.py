"""用户模型与管道角色模型的 TypedDict 定义。"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Tuple, TypedDict

from typing_extensions import NotRequired

# 需与 role_profiles.json 根对象中的角色键保持一致。
# ROLE001 的对话规划 / 结构化汇总编排见 app.session.role.role001（不从此文件加载）。
PipelineRoleKey = Literal[
    "question_denoiser",
    "context_compressor",
    "adversary",
    "profile_enricher",
]

PIPELINE_ROLE_KEYS: Tuple[str, ...] = (
    "question_denoiser",
    "context_compressor",
    "adversary",
    "profile_enricher",
)


class PipelineRoleProfile(TypedDict):
    """用于预处理/后处理管道的单个角色配置。"""

    username: str
    usercode: str
    sys_prompt: str
    model_level: str
    # 结构化输出所需模式文件的相对路径（可选）。
    output_schema_path: NotRequired[str]
    # 从结构化字典输出中提取主文本的字段名（可选）。
    structured_primary_field: NotRequired[str]


class RoleProfilesBundle(TypedDict):
    """按固定角色名组织的管道角色映射。"""

    question_denoiser: PipelineRoleProfile
    context_compressor: PipelineRoleProfile
    adversary: PipelineRoleProfile
    profile_enricher: PipelineRoleProfile


class MemoryTurn(TypedDict):
    """单条对话轮次记录。"""

    role: str
    content: str


class UserModel(TypedDict):
    """`usermodel.json` 中的一条用户配置。"""

    # 内部唯一角色名，用于路由与日志标识。
    username: str
    # 稳定业务编码，用于会话与系统集成。
    usercode: str
    # 结构化角色画像对象（姓名/领域/能力/语气等）。
    user_profile: Dict[str, Any]
    # 高层目标列表，用于约束对话方向。
    goals: List[str]
    # 可选历史对话，用作上下文注入。
    context_memory: NotRequired[List[MemoryTurn]]
    # 该角色需要绑定的内置工具方法名列表。
    tools: NotRequired[List[str]]
    # 最高优先级系统提示，定义角色行为边界。
    sys_prompt: str
    # 用户侧风格偏好模板，用于控制回复风格。
    user_prompt: str
    # 模型复杂度档位，通常为 low/mid/high。
    model_level: str
    # 建议首轮问候语，保证交互体验一致。
    greeting_example: NotRequired[str]
    # 建议结束语，用于自然收尾。
    conversation_exit: NotRequired[str]
    # 信息不足时的推荐追问句式。
    clarification_question: NotRequired[str]
    # 期望输出结构，例如 “A -> B -> C”。
    output_format: NotRequired[str]
    # 需规避的常见错误回复模式（字符串或字符串列表）。
    common_mistakes: NotRequired[str | List[str]]
    # 高风险场景下的标准风险提示文案。
    risk_reminder: NotRequired[str]
    # 明确禁止回答的主题列表。
    forbidden_topics: NotRequired[List[str]]
    # 当前输入问题，供单轮运行时使用。
    current_question: NotRequired[str]
    # 流式对话选用的实现类型（如 openai_direct）；缺省为 openai_direct（见 ``app.session.chat_stream_pipeline``）。
    stream_handler: NotRequired[str]
    # 流式侧参数：temperature；对抗轮次 adversarial_max_rounds（缺省 3）与 adversarial_max_rounds_cap（可选上限）。
    # ROLE001（岗位规划师）：use_structured_return 为真时走 structured_return（JSON+summary）；缺省 False 仅 Markdown 小结。
    # 是否开启深度思考仍以页面请求为准；此处仅配置开启时的最大轮次。
    stream_options: NotRequired[Dict[str, Any]]
