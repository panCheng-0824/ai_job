"""
RocketMQ 5 Proxy 与面试 Topic / 生产消费组配置。

环境变量与 server_job ``application.yml`` / ``.env.example`` 保持一致。
"""

from __future__ import annotations

import os

def rocketmq_proxy_grpc_endpoint() -> str:
    """
    RocketMQ 5.x Python/Java gRPC 客户端入口（官方示例为 ``host:8081``）。

    docker-compose 默认映射：宿主机 ``18081`` → 容器 Proxy gRPC ``8081``。
    勿与 HTTP/remoting 端口 18080 混用，否则路由可能落到 ``rocketmq-broker:8081``。
    """
    explicit = (os.getenv("ROCKETMQ_PROXY_GRPC_ENDPOINT") or "").strip()
    if explicit:
        return explicit
    legacy = (os.getenv("ROCKETMQ_PROXY_ENDPOINT") or "").strip()
    # 若仅配置了 18080（HTTP），自动改用 18081（gRPC）
    if legacy.endswith(":18080"):
        return legacy[:-5] + "18081"
    if legacy and not legacy.endswith(":8080"):
        return legacy
    port = (os.getenv("ROCKETMQ_PROXY_GRPC_PORT") or "18081").strip()
    host = (os.getenv("ROCKETMQ_PROXY_HOST") or "localhost").strip()
    return f"{host}:{port}"


def rocketmq_proxy_endpoint() -> str:
    """RocketMQ Proxy HTTP/remoting（Spring 等）；5.x gRPC 请用 ``rocketmq_proxy_grpc_endpoint``。"""
    return (os.getenv("ROCKETMQ_PROXY_ENDPOINT") or "localhost:18080").strip()


def rocketmq_nameserver_address() -> str:
    """
    Apache ``rocketmq-client-python`` 使用的 NameServer 地址。

    与 docker-compose 中 ``9876:9876`` 一致；勿与 Proxy 端口 18080 混用。
    """
    return (
        os.getenv("ROCKETMQ_NAMESERVER")
        or os.getenv("ROCKETMQ_NAMESERVER_ADDRESS")
        or "localhost:9876"
    ).strip()


def rocketmq_enabled() -> bool:
    return os.getenv("ROCKETMQ_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


# Topic（默认与 server_job interview.mq.topics 一致）
TOPIC_AI_TASK = os.getenv("INTERVIEW_MQ_TOPIC_AI_TASK", "interview_ai_task").strip()
TOPIC_AI_RESULT = os.getenv("INTERVIEW_MQ_TOPIC_AI_RESULT", "interview_ai_result").strip()
TOPIC_TIMER_EVENT = os.getenv("INTERVIEW_MQ_TOPIC_TIMER", "interview_timer_event").strip()
TOPIC_DLQ = os.getenv("INTERVIEW_MQ_TOPIC_DLQ", "interview_dlq").strip()

# 生产者组
PRODUCER_GROUP_SERVER_JOB = os.getenv(
    "ROCKETMQ_PRODUCER_GROUP_SERVER", "server_job_producer"
).strip()
PRODUCER_GROUP_AI_JOB_A = os.getenv(
    "ROCKETMQ_PRODUCER_GROUP", "ai_job_a_producer"
).strip()
PRODUCER_GROUP_AI_JOB_B = os.getenv(
    "ROCKETMQ_PRODUCER_GROUP_WORKER", "ai_job_b_producer"
).strip()

# 消费者组
CONSUMER_GROUP_AI_JOB_B = os.getenv(
    "ROCKETMQ_CONSUMER_GROUP", "ai_job_b_worker"
).strip()
CONSUMER_GROUP_SERVER_RESULT = os.getenv(
    "INTERVIEW_MQ_CONSUMER_AI_RESULT", "server_job_interview_result_consumer"
).strip()


def producer_group_for_role(role: str) -> str:
    """按进程角色返回生产者组名。"""
    r = (role or "").strip()
    if r == "ai_job_b":
        return PRODUCER_GROUP_AI_JOB_B
    if r == "server_job":
        return PRODUCER_GROUP_SERVER_JOB
    return PRODUCER_GROUP_AI_JOB_A


def mq_endpoints() -> dict[str, str]:
    """
    三种连接地址一览（联调日志 / 健康检查用）。

    - ``proxy_grpc``：Python 5.x 发送（``rocketmq-python-client``）
    - ``proxy_http``：Java Spring / remoting（``rocketmq-spring-boot-starter``）
    - ``nameserver``：legacy PushConsumer / 兜底 Producer
    """
    return {
        "proxy_grpc": rocketmq_proxy_grpc_endpoint(),
        "proxy_http": rocketmq_proxy_endpoint(),
        "nameserver": rocketmq_nameserver_address(),
    }
