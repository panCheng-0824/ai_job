package org.example.server_job.biz.support;

/**
 * 富文本 HTML 辅助：岗位描述（zwms）、单位简介（dwjj）等字段入库为 HTML，
 * RAG 拼装与日志场景需转为纯文本。
 */
public final class RichTextSupport {

    private RichTextSupport() {
    }

    /** 富文本 HTML → 纯文本 */
    public static String toPlainText(String html) {
        if (html == null || html.isBlank()) {
            return "";
        }
        String s = html;
        s = s.replaceAll("(?i)<br\\s*/?>", "\n");
        s = s.replaceAll("(?i)</p>", "\n");
        s = s.replaceAll("(?i)</div>", "\n");
        s = s.replaceAll("(?i)</li>", "\n");
        s = s.replaceAll("(?i)<li>", "- ");
        s = s.replaceAll("<[^>]+>", "");
        s = decodeBasicEntities(s);
        s = s.replaceAll("[ \\t\\x0B\\f\\r]+", " ");
        s = s.replaceAll("\\n{3,}", "\n\n");
        return s.trim();
    }

    private static String decodeBasicEntities(String s) {
        return s
                .replace("&nbsp;", " ")
                .replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&quot;", "\"")
                .replace("&#39;", "'");
    }
}
