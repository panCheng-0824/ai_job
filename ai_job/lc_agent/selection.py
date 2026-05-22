"""
模型条目选择（纯函数层）。

职责边界：
- 输入：已由其它模块加载好的 ``List[ModelEntry]``，本模块**不**读 JSON、**不**依赖 LangChain；
- 输出：单条 ``ModelEntry``，供 ``llm`` 模块构造 ``ChatOpenAI``。

这样「配置从哪来」与「如何从列表里挑一条」相互独立，便于单测时用内存里的假数据。
"""

from typing import List

from model_cfg import ModelEntry


def select_model_by_type_and_level(
    entries: List[ModelEntry], *, model_type: str, level: str
) -> ModelEntry:
    """
    按 model_type + model_level 选择模型，未命中时逐级回退：
    1) 同 type 同 level
    2) 同 type 任意 level（取第一条）
    3) 同 level 任意 type（取第一条）
    4) 全列表第一条
    """
    if not entries:
        raise ValueError("entries must not be empty")

    normalized_type = (model_type or "chat").strip().lower()
    normalized_level = (level or "").strip()

    for entry in entries:
        if str(entry.get("model_type", "chat")).strip().lower() == normalized_type and entry.get("model_level") == normalized_level:
            return entry

    for entry in entries:
        if str(entry.get("model_type", "chat")).strip().lower() == normalized_type:
            return entry

    for entry in entries:
        if entry.get("model_level") == normalized_level:
            return entry

    return entries[0]


def select_model_by_level(entries: List[ModelEntry], level: str) -> ModelEntry:
    """
    按 ``model_level`` 字符串选中第一条匹配的配置。

    :param entries: 非空列表（若为空，调用方应在外层保证；本函数会对空列表访问 ``[0]`` 抛错）。
    :param level: 目标档位，例如 ``\"low\"`` / ``\"mid\"`` / ``\"high\"``。
    :return: 命中的那条 ``ModelEntry``；若无一匹配，则退回 ``entries[0]``，避免运行时无模型可用。

    匹配策略刻意保持简单（线性扫描）：配置条数极少，无需建索引字典；若日后档位很多再优化即可。
    """
    # 兼容旧调用：默认按 chat 类型选档位。
    return select_model_by_type_and_level(entries, model_type="chat", level=level)
