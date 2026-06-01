package org.example.server_job.interview.mq;

/**
 * 面试模块 RocketMQ Topic 常量（默认值与 application.yml 一致）。
 */
public final class InterviewMqTopics {

    public static final String AI_TASK = "interview_ai_task";
    public static final String AI_RESULT = "interview_ai_result";
    public static final String TIMER_EVENT = "interview_timer_event";
    public static final String DLQ = "interview_dlq";

    private InterviewMqTopics() {
    }
}
