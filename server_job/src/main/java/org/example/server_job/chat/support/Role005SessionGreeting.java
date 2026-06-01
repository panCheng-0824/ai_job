package org.example.server_job.chat.support;

import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * ROLE005 模拟面试官 — 创建/进入空会话时的固定开场白。
 *
 * <p>与 ai_job {@code role005.greeting} 文案保持一致；会话落库在 server_job MySQL。</p>
 */
public final class Role005SessionGreeting {

    public static final String USERCODE = "ROLE005";

    private static final String GREETING_TEXT = """
            你好，我是你的模拟面试官。

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

            资料就绪后，回复「准备好了」我们再进入正式问答。""".trim();

    private Role005SessionGreeting() {
    }

    public static boolean isRole005(String usercode) {
        return USERCODE.equals(usercode == null ? "" : usercode.trim());
    }

    /** 是否应在当前 history 为空时写入开场白。 */
    public static boolean shouldSeed(String usercode, List<Map<String, Object>> history) {
        return isRole005(usercode) && (history == null || history.isEmpty());
    }

    /** 构造一条 assistant 轮次（与 ai_job history 字段对齐）。 */
    public static Map<String, Object> buildTurn(Instant now) {
        Map<String, Object> turn = new LinkedHashMap<>();
        turn.put("role", "assistant");
        turn.put("content", GREETING_TEXT);
        turn.put("ts", DateTimeFormatter.ISO_INSTANT.format(now == null ? Instant.now() : now));
        return turn;
    }

    public static String greetingContent() {
        return GREETING_TEXT;
    }
}
