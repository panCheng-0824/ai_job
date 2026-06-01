package org.example.server_job.interview.support;

import java.util.UUID;

/** 面试业务 ID 生成。 */
public final class InterviewIds {

    private InterviewIds() {
    }

    public static String newSessionId() {
        return "isess_" + UUID.randomUUID().toString().replace("-", "");
    }

    public static String newPlanId() {
        return "plan_" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    public static String newReportId() {
        return "ireport_" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    public static String planRowId(String planId, int version) {
        return planId + "#" + version;
    }

    /** 学生面试总结记录 ID */
    public static String newRecordId() {
        return "irec_" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    /** 逐题答题行 ID */
    public static String newAnswerRowId() {
        return "ians_" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    /** 大纲内题目物理主键 */
    public static String questionRowId(String planRowId, String questionId) {
        return planRowId + "#" + questionId;
    }
}
