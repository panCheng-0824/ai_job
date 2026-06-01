"""
ROLE005 — 会话开场白（创建/进入空会话时写入 history）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

ROLE005_USERCODE = "ROLE005"

# 与 web 右侧「我的资料」能力对齐的固定开场文案（步骤与 ChatPlannerContextRail 一致）
ROLE005_SESSION_GREETING = """你好，我是你的模拟面试官。

我会结合你的简历与目标岗位，用结构化提问和追问，帮你练习真实面试场景。全程只提问与引导，不会直接给标准答案。

开始之前，请按下面步骤准备「我的资料」：

【打开资料栏】
1. 左侧先填写学号，并点击「创建 / 进入会话」；
2. 若页面右侧没有资料栏，请点击对话区右上角「展开我的资料」。

【添加简历】
3. 在右侧展开「简历」卡片；
4. 暂无简历可点「打开简历编辑」新建或完善；
5. 按住「简历」卡片拖到下方输入框，松手即可附加上下文。

【添加心仪岗位】
6. 在「岗位」页浏览并收藏目标岗位（左侧菜单可进入）；
7. 回到对话页，在右侧展开「收藏岗位」，将具体岗位卡片拖入输入框；
8. 也可展开「关注企业」，拖动企业卡片作为参考。

资料就绪后，回复「准备好了」或简单自我介绍，我们再进入正式问答。"""


def seed_role005_session_greeting(session: Dict[str, Any]) -> bool:
    """
    若为本角色且 history 为空，写入一条 assistant 开场消息。

    返回 True 表示已写入（调用方需持久化 sessions）。
    """
    if str(session.get("usercode") or "").strip() != ROLE005_USERCODE:
        return False
    history = session.get("history")
    if not isinstance(history, list):
        history = []
        session["history"] = history
    if history:
        return False
    session["history"] = [
        {
            "role": "assistant",
            "content": ROLE005_SESSION_GREETING.strip(),
            "ts": datetime.utcnow().isoformat() + "Z",
        }
    ]
    return True
