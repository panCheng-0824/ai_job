#!/usr/bin/env python3
"""
Agent 运用演示：通过命令行 ``--username`` / ``usercode`` 选择 ``usermodel.json`` 中的用户。

串联：

  ``model_cfg`` → 加载档位与 API  
  ``user_model`` → 校验用户画像、拼装 system prompt  
  ``lc_agent`` → 按该用户的 ``model_level`` 创建 ``AgentExecutor``  
  ``user_session.run_user_query`` → 管道（去噪 / 压缩历史 / 主 Agent / 对抗 / 画像建议）

运行（需 ``modelCfg.json`` 中端点与本机网络可用）：

  python demo.py --username tongqian --usercode USR003
  python demo.py --usercode USR001
  python demo.py --username liming

若 **两个参数都不传**，默认 ``usercode=USR003``（童倩）。  
选取规则同 ``load_user_model``：**同时提供时优先按 username 匹配**。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, TypedDict

ROOT = Path(__file__).resolve().parent


class _UserSelectKw(TypedDict, total=False):
    """用户选择参数：支持 username 与 usercode 二选一或同时传入。"""
    username: str
    usercode: str


def _banner(title: str) -> None:
    """打印统一风格的分段标题。"""
    line = "=" * 66
    print(f"\n{line}\n{title}\n{line}")


def _normalize_user_args(args: argparse.Namespace) -> _UserSelectKw:
    """
    从 argparse 得到传给 ``load_user_model`` / ``run_user_query`` 的选型参数。

    空串视为未提供；二者都缺省时默认 ``usercode=USR003``。
    """
    username = (args.username or "").strip() or None
    usercode = (args.usercode or "").strip() or None
    out: _UserSelectKw = {}
    if username is not None:
        out["username"] = username
    if usercode is not None:
        out["usercode"] = usercode
    return out


def step_print_model_catalog(highlight_level: str) -> None:
    """展示 ``modelCfg.json``，并在与当前用户 ``model_level`` 一致的档位旁标注箭头。"""
    _banner("① 模型配置 modelCfg.json（标注当前用户的档位）")
    from model_cfg import load_model_list

    entries = load_model_list()
    for e in entries:
        tag = "  ← 当前用户使用该档" if e["model_level"] == highlight_level else ""
        print(
            f"  · [{e['model_level']}] {e['model_provider']} / {e['model_name']!r}\n"
            f"      {e['model_api']}{tag}"
        )


def step_print_user_session(user: "UserModel") -> None:
    """打印选中用户的画像、目标、记忆、本轮提问与合成 system prompt。"""
    from user_model import UserModel, build_system_prompt_from_user

    _banner(f"② 用户会话：{user['username']}（{user['usercode']}）")

    prof = user["user_profile"]
    print(f"  登录名: {user['username']}    业务编号: {user['usercode']}")
    disp = prof.get("display_name", "")
    role = prof.get("role", "")
    extra = prof.get("major") or prof.get("experience_level", "")
    print(f"  姓名: {disp}    角色: {role}" + (f"    {extra}" if extra else ""))
    print(f"  model_level（主 Agent 档位）: {user['model_level']}")
    print("\n  【追求的目标】")
    for g in user["goals"]:
        print(f"    · {g}")

    print("\n  【上下文记忆 context_memory】（随后会被「压缩管道」摘要）")
    if not user["context_memory"]:
        print("    （空）")
    else:
        for turn in user["context_memory"]:
            who = "用户" if turn["role"] == "user" else "助手"
            line = turn["content"].strip().replace("\n", " ")
            print(f"    [{who}] {line[:120]}{'…' if len(line) > 120 else ''}")

    print("\n  【本轮 current_question】（会先经「去噪管道」）")
    cq = user["current_question"].strip()
    print(f"    {cq[:320]}{'…' if len(cq) > 320 else ''}")

    sp = build_system_prompt_from_user(user)
    preview = sp[:520] + ("…" if len(sp) > 520 else "")
    print("\n  【合成 system prompt 预览】（送入主 Agent 的第一条 system 消息）\n")
    print(preview)


def step_create_agent_for_user(select_kw: _UserSelectKw) -> None:
    """与业务入口一致：用 ``create_agent_from_user_model`` 绑定该用户的档位与人设。"""
    _banner("③ 创建 AgentExecutor（当前用户的档位 + system prompt）")
    from user_session import create_agent_from_user_model

    executor, user = create_agent_from_user_model(**select_kw, verbose=False)
    print(f"  已创建: {type(executor).__name__}")
    print(f"  绑定用户: {user['username']} ({user['usercode']})  model_level={user['model_level']}")
    print("  （下一步将执行 ``run_user_query``，触发完整管道与 invoke）")


def step_run_full_pipeline(
    select_kw: _UserSelectKw,
    *,
    verbose_agent: bool,
    use_role_pipeline: bool,
) -> None:
    """编排入口：``run_user_query`` = 管道 + 主 Agent + 对抗 + 画像建议（真实 Chat API）。"""
    _banner("④ 完整链路：run_user_query（管道 + 主 Agent）")

    from user_session import run_user_query

    kwargs: Dict[str, object] = {
        **select_kw,
        "verbose": verbose_agent,
        "use_role_pipeline": use_role_pipeline,
    }

    try:
        result = run_user_query(**kwargs)
    except Exception as exc:
        print(f"  调用失败（请检查 modelCfg、端点与本机网络）:\n  {exc!r}", file=sys.stderr)
        sys.exit(2)

    pipe = result.get("pipeline", {})
    print("  【pipeline 元数据】")
    for k in (
        "roles_loaded_from",
        "original_question",
        "denoised_question",
        "context_compression_summary",
        "used_compressed_history",
    ):
        if k in pipe:
            v = pipe[k]
            s = str(v)
            print(f"    · {k}: {s[:140]}{'…' if len(s) > 140 else ''}")

    print("\n  【主 Agent output】\n")
    print(result.get("output", ""))

    print("\n  【对抗审查 adversarial_review】\n")
    print(result.get("adversarial_review", ""))

    print("\n  【画像补充 profile_enrichment】\n")
    print(result.get("profile_enrichment", ""))


def main(
    username: str | None = None,
    usercode: str | None = None,
    use_role_pipeline: bool | None = None,
) -> None:
    """命令行演示入口：选择用户后串行执行模型、会话与管道调用演示。"""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    parser = argparse.ArgumentParser(
        description="按 username / usercode 选择用户，演示 Agent 与管道（真实 API）",
    )
    parser.add_argument(
        "--username",
        type=str,
        default=None,
        help="usermodel.json 中的 username；与 --usercode 可同时给（匹配规则同 load_user_model：优先 username）",
    )
    parser.add_argument(
        "--usercode",
        type=str,
        default=None,
        help="usermodel.json 中的 usercode；若 username 与本参数都未提供，则默认 USR003",
    )
    parser.add_argument(
        "--verbose-agent",
        action="store_true",
        help="打开 AgentExecutor 的 verbose 中间输出",
    )
    parser.add_argument(
        "--no-pipeline",
        action="store_true",
        help="关闭去噪/压缩/对抗/画像补充管道，只调用主 Agent",
    )
    args = parser.parse_args()
    # 允许通过参数方式调用，例如 main(username="alice", usercode="USR001")。
    if username is not None:
        args.username = username
    if usercode is not None:
        args.usercode = usercode
    if use_role_pipeline is not None:
        args.no_pipeline = not use_role_pipeline

    select_kw = _normalize_user_args(args)

    from user_model import UserModel, load_user_model

    user: UserModel = load_user_model(**select_kw)

    step_print_model_catalog(user["model_level"])
    step_print_user_session(user)
    step_create_agent_for_user(select_kw)
    step_run_full_pipeline(
        select_kw,
        verbose_agent=args.verbose_agent,
        use_role_pipeline=(not args.no_pipeline),
    )

    _banner("演示结束")


if __name__ == "__main__":
    username='tongqian'
    usercode='USR003'
    use_role_pipeline :bool= False
    main(username, usercode, use_role_pipeline)
