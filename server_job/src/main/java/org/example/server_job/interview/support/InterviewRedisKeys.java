package org.example.server_job.interview.support;

/**
 * 面试 Redis Key 规范（与《最终开发步骤》0.6 节一致）。
 *
 * <p>超时由 server_job 权威控制，ai_job 只响应 action=timeout 的 turn。
 */
public final class InterviewRedisKeys {

    private InterviewRedisKeys() {
    }

    /** 单题倒计时：TTL = 题目 timeout_seconds */
    public static String timer(String sessionId, int questionIndex) {
        return "interview:timer:" + sessionId + ":" + questionIndex;
    }

    /** 分布式锁，防止并发双提交 */
    public static String lock(String sessionId) {
        return "interview:lock:" + sessionId;
    }

    /** 幂等结果缓存（24h） */
    public static String idempotency(String studentId, String idempotencyKey) {
        return "interview:idempotency:" + studentId + ":" + idempotencyKey;
    }

    /** 连接心跳滑动续期 */
    public static String heartbeat(String sessionId) {
        return "interview:session:heartbeat:" + sessionId;
    }

    /** 整场面试进度上下文（TTL 约 24h，由 server_job 权威维护） */
    public static String ctx(String studentId, String recordId) {
        return "interview:ctx:" + studentId + ":" + recordId;
    }

    /**
     * 单题多轮 LLM 上下文（题完结后删除或短 TTL）。
     *
     * @param chatSessionId 门户聊天 session_id
     */
    public static String questionSession(
            String chatSessionId,
            String studentId,
            String recordId,
            String questionId
    ) {
        return "interview:qsess:"
                + chatSessionId + ":"
                + studentId + ":"
                + recordId + ":"
                + questionId;
    }

    /** 某条面试记录下全部单题 qsess（删除记录时扫尾） */
    public static String qsessPatternForRecord(String studentId, String recordId) {
        return "interview:qsess:*:" + studentId + ":" + recordId + ":*";
    }

    /** 某场面试会话下全部倒计时 key */
    public static String timerPattern(String interviewSessionId) {
        return "interview:timer:" + interviewSessionId + ":*";
    }
}
