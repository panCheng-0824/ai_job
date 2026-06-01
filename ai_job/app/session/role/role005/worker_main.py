"""
ROLE005 ai_job_b Worker 启动入口。

用法::

    ROLE=ai_job_b python -m app.session.role.role005.worker_main

消费 ``interview_ai_task``；未安装 SDK 或 Broker 不可达时降级为待机日志。
"""

from __future__ import annotations

import logging
import os
import time

from app.mq.client import start_push_consumer
from app.mq.settings import (
    CONSUMER_GROUP_AI_JOB_B,
    TOPIC_AI_TASK,
    mq_endpoints,
    rocketmq_enabled,
)
from app.session.role.role005.config import ai_job_role
from app.session.role.role005.mq.consumer import handle_task_json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger(__name__)


def main() -> None:
    role = ai_job_role()
    if role != "ai_job_b":
        log.warning("当前 ROLE=%s，建议设置 ROLE=ai_job_b", role)
    ep = mq_endpoints()
    log.info(
        "ROLE005 Worker 启动 group=%s topic=%s nameserver=%s proxy_grpc=%s enabled=%s",
        CONSUMER_GROUP_AI_JOB_B,
        TOPIC_AI_TASK,
        ep["nameserver"],
        ep["proxy_grpc"],
        rocketmq_enabled(),
    )
    consumer_ok = False
    if rocketmq_enabled():
        consumer_ok = start_push_consumer(
            topic=TOPIC_AI_TASK,
            group=CONSUMER_GROUP_AI_JOB_B,
            on_message=handle_task_json,
        )
    if consumer_ok:
        log.info("Worker 已进入 PushConsumer 阻塞模式")
        while True:
            time.sleep(3600)
        return

    log.warning(
        "PushConsumer 未启动（未安装 rocketmq-client 或连接失败），进入待机轮询"
    )
    interval = int(os.getenv("ROLE005_WORKER_POLL_SEC", "30"))
    while True:
        log.debug("Worker 待机中…")
        time.sleep(max(5, interval))


if __name__ == "__main__":
    main()
