"""
RocketMQ 客户端薄封装：未安装 SDK 或 Broker 不可达时降级为日志模式。

依赖
----
**macOS / 本地开发推荐**（连 Proxy gRPC ``18081``，纯 Python wheel）::

    pip install rocketmq-python-client

Linux 可选 Apache 客户端（连 NameServer 9876）::

    pip install rocketmq-client-python

须与 PyCharm / 运行 ai_job 的**同一解释器**安装（见 ``diagnose_mq_sdk()`` 打印的 Python 路径）。
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Callable, Dict, Optional, Tuple

from app.mq.grpc_tls_dev import patch_grpc_insecure_tls_if_needed
from app.mq.route_rewrite import patch_v5_route_endpoints_for_host
from app.mq.settings import (
    mq_endpoints,
    rocketmq_nameserver_address,
    rocketmq_proxy_endpoint,
    rocketmq_proxy_grpc_endpoint,
)

log = logging.getLogger(__name__)

# 缓存项: ("v5"|"legacy", producer, MessageClass)
_ProducerHolder: Dict[str, Tuple[str, Any, Any]] = {}
_PushConsumerHolder: Dict[str, Any] = {}
_sdk_hint_logged = False


def diagnose_mq_sdk() -> str:
    """返回 SDK 探测说明，供日志或 CLI 打印。"""
    lines = [f"Python: {sys.executable}"]
    try:
        from rocketmq import ClientConfiguration  # noqa: F401

        lines.append("可用: RocketMQ 5 SDK — pip install rocketmq-python-client")
    except ImportError as exc:
        lines.append(f"不可用: RocketMQ 5 SDK ({exc})")
        lines.append("  → 请用本行 Python 执行: python -m pip install rocketmq-python-client")
    try:
        from rocketmq.client import Producer  # noqa: F401

        lines.append(
            f"可用: Apache rocketmq-client-python (NameServer={rocketmq_nameserver_address()})"
        )
    except ImportError as exc:
        err = str(exc).lower()
        if "dynamic library" in err or "librocketmq" in err:
            lines.append(
                "不可用: rocketmq-client-python 的 pip 包在，但缺少 librocketmq.dylib（macOS 常见）"
            )
            lines.append("  → 请改装: python -m pip install rocketmq-python-client")
        else:
            lines.append(f"不可用: Apache rocketmq-client-python ({exc})")
    ep = mq_endpoints()
    lines.append(f"Proxy gRPC (5.x SDK): {ep['proxy_grpc']}")
    lines.append(f"Proxy HTTP (Spring): {ep['proxy_http']}")
    lines.append(f"NameServer (legacy): {ep['nameserver']}")
    return "\n".join(lines)


def _log_sdk_missing_once() -> None:
    global _sdk_hint_logged
    if _sdk_hint_logged:
        return
    _sdk_hint_logged = True
    log.warning(
        "RocketMQ SDK 不可用，消息仅记录不落库。排查:\n%s",
        diagnose_mq_sdk(),
    )


def _parse_host_port(endpoint: str) -> tuple[str, int]:
    ep = (endpoint or "").strip()
    if ":" not in ep:
        raise ValueError(f"RocketMQ 端点格式应为 host:port，当前={ep!r}")
    host, port_s = ep.rsplit(":", 1)
    return host.strip(), int(port_s.strip())


def _try_v5_producer(group: str, topic: str) -> Optional[Tuple[str, Any, Any]]:
    """RocketMQ 5 gRPC（rocketmq-python-client），经 Proxy 连接。"""
    try:
        from rocketmq import ClientConfiguration, Credentials, Message, Producer
    except ImportError:
        return None

    patch_grpc_insecure_tls_if_needed()
    patch_v5_route_endpoints_for_host()
    # 5.x SDK 必须连 gRPC（compose 映射 18081→8081），不能连 18080
    endpoint = rocketmq_proxy_grpc_endpoint()
    host, port = _parse_host_port(endpoint)
    endpoints = f"{host}:{port}"
    config = ClientConfiguration(endpoints, Credentials())
    # 5.x 构造函数的第二个参数是 topic 列表，不是 producer group
    topics = (topic,) if topic else (group,)
    producer = Producer(config, topics)
    producer.startup()
    log.info(
        "RocketMQ 5 Producer 已启动 group=%s topics=%s proxy=%s",
        group,
        topics,
        endpoints,
    )
    return "v5", producer, Message


def _try_legacy_producer(group: str) -> Optional[Tuple[str, Any, Any]]:
    """Apache rocketmq-client-python：连接 NameServer（默认 localhost:9876）。"""
    try:
        from rocketmq.client import Message, Producer
    except ImportError:
        return None

    ns = rocketmq_nameserver_address()
    producer = Producer(group)
    producer.set_name_server_address(ns)
    producer.start()
    log.info("RocketMQ legacy Producer 已启动 group=%s nameserver=%s", group, ns)
    return "legacy", producer, Message


def get_producer(group: str, *, topic: str = ""):
    cache_key = f"{group}:{topic}" if topic else group
    if cache_key in _ProducerHolder:
        return _ProducerHolder[cache_key]
    holder = _try_v5_producer(group, topic)
    if holder is None:
        holder = _try_legacy_producer(group)
    _ProducerHolder[cache_key] = holder
    if holder is None:
        _log_sdk_missing_once()
    return holder


def send_json(topic: str, body: dict, *, group: str) -> bool:
    """向指定 Topic 发送 JSON 消息。"""
    payload = json.dumps(body, ensure_ascii=False)
    holder = get_producer(group, topic=topic)
    if holder is None:
        return False
    kind, producer, MessageCls = holder
    try:
        if kind == "v5":
            msg = MessageCls()
            msg.topic = topic
            msg.body = payload.encode("utf-8")
            producer.send(msg)
        else:
            msg = MessageCls(topic)
            msg.set_body(payload)
            producer.send_sync(msg)
        return True
    except Exception as exc:
        log.warning("MQ 发送失败 topic=%s: %s", topic, exc)
        return False


def start_push_consumer(
    *,
    topic: str,
    group: str,
    on_message: Callable[[str], None],
) -> bool:
    """
    启动 Push 消费（legacy API）。

    v5 SimpleConsumer 需异步循环，Worker 入口另行扩展。
    """
    key = f"{group}:{topic}"
    if key in _PushConsumerHolder:
        return True
    try:
        from rocketmq.client import PushConsumer
    except ImportError:
        _log_sdk_missing_once()
        return False

    def _callback(msg):
        try:
            body = msg.body.decode("utf-8") if isinstance(msg.body, bytes) else str(msg.body)
            on_message(body)
        except Exception as exc:
            log.exception("MQ 消费回调异常: %s", exc)
        return True

    consumer = PushConsumer(group)
    consumer.set_name_server_address(rocketmq_nameserver_address())
    consumer.subscribe(topic, _callback)
    consumer.start()
    _PushConsumerHolder[key] = consumer
    log.info(
        "PushConsumer 已启动 topic=%s group=%s nameserver=%s",
        topic,
        group,
        rocketmq_nameserver_address(),
    )
    return True
