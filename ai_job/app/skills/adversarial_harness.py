"""生产者-对抗者 Harness：用于多轮对抗迭代优化回答。"""

from __future__ import annotations

from typing import Any, Dict, List

from pipeline_llm import run_pipeline_llm
from user_model import build_system_prompt_from_user, load_user_model


def _pick_user(role_ref: str) -> Dict[str, Any]:
    """按 usercode 或 username 解析生产者角色。"""
    ref = (role_ref or "").strip()
    if not ref:
        raise ValueError("role_ref 不能为空，请传入 usercode 或 username")
    try:
        return load_user_model(usercode=ref)
    except Exception:
        return load_user_model(username=ref)


def _build_temp_profile(*, usercode: str, username: str, sys_prompt: str, model_level: str) -> Dict[str, str]:
    """构造 run_pipeline_llm 所需的最小角色配置。"""
    return {
        "usercode": usercode,
        "username": username,
        "sys_prompt": sys_prompt,
        "model_level": model_level,
    }


def _build_adversary_prompt(adversary_desc: str) -> str:
    """构造对抗者系统提示词，要求输出固定 verdict。"""
    desc = (adversary_desc or "").strip() or "你是严格的红队审查员。"
    return (
        f"{desc}\n\n"
        "你现在扮演回答审查对抗者。请围绕「问题-回答」做严格审查，重点检查：\n"
        "1) 是否答非所问；2) 事实与逻辑错误；3) 漏掉关键约束；4) 表达是否可执行。\n\n"
        "输出必须遵循：\n"
        "VERDICT: PASS 或 FAIL\n"
        "ISSUES:\n"
        "- 列出主要问题（PASS 时可写无）\n"
        "SUGGESTIONS:\n"
        "- 给出可执行改进建议\n"
    )


def _is_pass(review_text: str) -> bool:
    """根据固定前缀判断是否通过。"""
    first_line = (review_text or "").strip().splitlines()[:1]
    if not first_line:
        return False
    head = first_line[0].strip().upper()
    return "VERDICT:" in head and "PASS" in head


def run_adversarial_harness(
    *,
    role_ref: str,
    adversary_desc: str,
    question: str,
    max_rounds: int = 3,
) -> Dict[str, Any]:
    """
    运行生产者-对抗者多轮博弈。

    入参：
    - role_ref: 生产者角色标识（usercode 或 username）
    - adversary_desc: 对抗者描述
    - question: 用户问题
    - max_rounds: 最大对抗轮次（1-10）
    """
    q = (question or "").strip()
    if not q:
        raise ValueError("question 不能为空")

    rounds = max(1, min(int(max_rounds), 10))
    producer_user = _pick_user(role_ref)
    producer_sys = build_system_prompt_from_user(producer_user)

    producer_profile = _build_temp_profile(
        usercode=str(producer_user["usercode"]),
        username=str(producer_user["username"]),
        sys_prompt=producer_sys,
        model_level=str(producer_user.get("model_level", "mid")),
    )
    adversary_profile = _build_temp_profile(
        usercode="HARNESS_ADV",
        username="harness_adversary",
        sys_prompt=_build_adversary_prompt(adversary_desc),
        model_level=str(producer_user.get("model_level", "mid")),
    )

    history: List[Dict[str, str]] = []
    last_answer = ""
    for i in range(1, rounds + 1):
        if i == 1:
            producer_payload = f"请回答这个问题：\n{q}"
        else:
            producer_payload = (
                "请基于上一版回答和审查意见，给出改进后的最终回答。\n\n"
                f"问题：\n{q}\n\n"
                f"上一版回答：\n{last_answer}\n\n"
                f"审查意见：\n{history[-1]['review']}\n"
            )

        answer = str(run_pipeline_llm(producer_profile, producer_payload, temperature=0.2)).strip()
        review_payload = (
            f"问题：\n{q}\n\n"
            f"回答：\n{answer}\n\n"
            "请按约定格式输出审查结论。"
        )
        review = str(run_pipeline_llm(adversary_profile, review_payload, temperature=0.1)).strip()

        history.append({"round": str(i), "answer": answer, "review": review})
        last_answer = answer
        if _is_pass(review):
            break

    return {
        "role_ref": role_ref,
        "question": q,
        "rounds_used": len(history),
        "max_rounds": rounds,
        "final_answer": last_answer,
        "final_review": history[-1]["review"] if history else "",
        "history": history,
    }


def render_harness_markdown(result: Dict[str, Any]) -> str:
    """将 Harness 结果渲染为可读 Markdown。"""
    out: List[str] = []
    out.append("## Harness 对抗结果")
    out.append(f"- 生产者角色：{result.get('role_ref', '')}")
    out.append(f"- 轮次：{result.get('rounds_used', 0)} / {result.get('max_rounds', 0)}")
    out.append(f"- 问题：{result.get('question', '')}")
    out.append("")
    out.append("## 最终回答")
    out.append(str(result.get("final_answer", "")))
    out.append("")
    out.append("## 最终审查")
    out.append(str(result.get("final_review", "")))
    out.append("")
    out.append("## 逐轮记录")
    for item in result.get("history", []):
        out.append(f"### Round {item.get('round', '')}")
        out.append("**回答**")
        out.append(str(item.get("answer", "")))
        out.append("")
        out.append("**审查**")
        out.append(str(item.get("review", "")))
        out.append("")
    return "\n".join(out)


def run_harness_and_render_markdown(
    *,
    role_ref: str,
    adversary_desc: str,
    question: str,
    max_rounds: int = 3,
) -> str:
    """对外一站式入口：执行 harness 并返回 Markdown 文本。"""
    result = run_adversarial_harness(
        role_ref=role_ref,
        adversary_desc=adversary_desc,
        question=question,
        max_rounds=max_rounds,
    )
    return render_harness_markdown(result)
