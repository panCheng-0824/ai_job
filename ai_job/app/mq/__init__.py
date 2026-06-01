"""
ai_job 全局 RocketMQ 配置（面试异步任务与 ROLE005 Worker 共用）。
"""

from app.mq.settings import (
    CONSUMER_GROUP_AI_JOB_B,
    CONSUMER_GROUP_SERVER_RESULT,
    PRODUCER_GROUP_AI_JOB_A,
    PRODUCER_GROUP_AI_JOB_B,
    PRODUCER_GROUP_SERVER_JOB,
    TOPIC_AI_RESULT,
    TOPIC_AI_TASK,
    TOPIC_DLQ,
    TOPIC_TIMER_EVENT,
    mq_endpoints,
    rocketmq_enabled,
    rocketmq_nameserver_address,
    rocketmq_proxy_endpoint,
    rocketmq_proxy_grpc_endpoint,
)

__all__ = [
    "TOPIC_AI_TASK",
    "TOPIC_AI_RESULT",
    "TOPIC_TIMER_EVENT",
    "TOPIC_DLQ",
    "PRODUCER_GROUP_SERVER_JOB",
    "PRODUCER_GROUP_AI_JOB_A",
    "PRODUCER_GROUP_AI_JOB_B",
    "CONSUMER_GROUP_AI_JOB_B",
    "CONSUMER_GROUP_SERVER_RESULT",
    "mq_endpoints",
    "rocketmq_nameserver_address",
    "rocketmq_proxy_endpoint",
    "rocketmq_proxy_grpc_endpoint",
    "rocketmq_enabled",
]
