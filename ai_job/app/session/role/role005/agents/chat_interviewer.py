"""
ROLE005 — 聊天模式下的面试官 Agent（无正式 turn / ContextBundle）。

结合最近三轮对话与当前输入，输出下一题、追问或澄清（JSON 契约与答题图一致）。
"""

from __future__ import annotations

from app.session.role.role005.agents._llm import invoke_llm_text
from app.session.role.role005.parsing import normalize_interviewer_output, parse_json_object
from app.session.role.role_util.bindings import GraphBindings


def build_chat_interviewer_prompt(
    bindings: GraphBindings,
    *,
    recent_rounds_block: str,
    materials_block: str,
    current_question: str,
) -> str:
    """
    构造 chat 模式 Prompt。

    参数
    ----
    recent_rounds_block:
        最近三轮 user/assistant 摘录。
    materials_block:
        右侧资料卡片与附加上下文拼成的素材块。
    current_question:
        学生本轮可见输入。
    """
    mats = (materials_block or "").strip() or "（无额外参考素材）"
    recent = (recent_rounds_block or "").strip() or "（无历史问答）"
    student = (current_question or "").strip() or "（无）"

    return f"""你是模拟面试官，当前处于**聊天辅导模式**（学生尚未通过 message_context 提交正式 turn JSON）。

请**综合【最近三轮对话】与【学生本轮输入】**，以及【参考素材】（若有），决定下一步：
- 提出新的面试题（action=ask_question）；
- 对上一轮回答追问（action=ask_followup）；
- 澄清题意（action=clarify）；
- 仅给思考方向（action=provide_hint）。

红线：
- **只提问/澄清/给思考提示**，禁止评价好坏、禁止透露参考答案、禁止打分。
- 输出**仅一个** JSON 对象，字段含 action, question_id, question_text, thinking_hint, followup_text 等。

{recent}

【参考素材】
{mats}

学生本轮输入：{student}

──角色约束──
{bindings.role_block}

输出 JSON 示例：
{{"action":"ask_question","question_id":"chat_q1","question_text":"请结合你刚才提到的项目，说明你在其中的技术决策","thinking_hint":"可从背景、你的职责、关键取舍三方面回答"}}
"""


def run_chat_interviewer_agent(
    bindings: GraphBindings,
    *,
    recent_rounds_block: str,
    materials_block: str,
    current_question: str,
) -> tuple[dict, str]:
    """调用 LLM 并解析面试官 JSON。返回 (data, error_message)。"""
    prompt = build_chat_interviewer_prompt(
        bindings,
        recent_rounds_block=recent_rounds_block,
        materials_block=materials_block,
        current_question=current_question,
    )
    raw = invoke_llm_text(bindings, prompt, scenario="模拟面试-对话提问")
    if not raw:
        return {}, "模型无输出或已取消"
    data, err = parse_json_object(raw)
    if err:
        return {}, err
    return normalize_interviewer_output(data), ""
