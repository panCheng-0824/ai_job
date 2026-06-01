#!/usr/bin/env python3
"""
向 RocketMQ 投递一条面试测试信封（联调 ai_job_b / server_job）。

用法::

    cd ai_job
    export ROCKETMQ_PROXY_GRPC_ENDPOINT=localhost:18081
    python scripts/mq_send_test.py
    python scripts/mq_send_test.py --topic interview_ai_result --event interview.reflection.result
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 保证可 import app.*
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import os

from app.mq.client import diagnose_mq_sdk, send_json
from app.mq.settings import (
    TOPIC_AI_RESULT,
    TOPIC_AI_TASK,
    producer_group_for_role,
    rocketmq_proxy_grpc_endpoint,
)
from app.session.role.role005.mq.envelope import MqEnvelope


def main() -> int:
    parser = argparse.ArgumentParser(description="RocketMQ 面试模块测试发送")
    parser.add_argument(
        "--topic",
        default=TOPIC_AI_TASK,
        choices=[TOPIC_AI_TASK, TOPIC_AI_RESULT],
        help="目标 Topic",
    )
    parser.add_argument(
        "--event",
        default="interview.reflection.request",
        help="event_type 字段",
    )
    args = parser.parse_args()

    envelope = MqEnvelope(
        event_type=args.event,
        producer="cli_test",
        idempotency_key=f"cli:test:{args.topic}:1",
        payload={
            "interview_session_id": "isess_cli_test",
            "student_id": "stu_cli",
            "note": "mq_send_test.py",
        },
    )
    group = producer_group_for_role(os.getenv("ROLE", "ai_job_a"))
    print(diagnose_mq_sdk())
    print("---")
    ok = send_json(args.topic, envelope.model_dump(), group=group)
    print(f"proxy_grpc={rocketmq_proxy_grpc_endpoint()} topic={args.topic} sent={ok}")
    if not ok:
        print(
            "提示: pip install rocketmq-python-client\n"
            "      ROCKETMQ_PROXY_GRPC_ENDPOINT=localhost:18081（勿用 18080）\n"
            "      docker compose up -d rocketmq-broker && ./scripts/rocketmq-init-topics.sh\n"
            "      若仍见 rocketmq-broker:8081，重建 broker 使 rocketmq/broker.conf 生效"
        )
    print(envelope.model_dump_json(ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
