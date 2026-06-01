"""
宿主机跑 ai_job 时，修正 QueryRoute 返回的 Broker gRPC 地址。

rocketmq-python-client 会连两次：
  1) ROCKETMQ_PROXY_GRPC_ENDPOINT（如 127.0.0.1:18081）→ Proxy
  2) 路由里的 broker.endpoints（常为 host.docker.internal:8081）→ Broker gRPC

第 2 跳若带 Docker 主机名，gRPC 会拼成 ``ipv4:host.docker.internal:8081`` 并失败。
compose 需同时映射 ``8081:8081``（路由端口）与 ``18081:8081``（显式 Proxy 入口）。
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

_patched = False

_HOST_REWRITE = {
    "host.docker.internal": "127.0.0.1",
    "rocketmq-broker": "127.0.0.1",
}


def patch_v5_route_endpoints_for_host() -> None:
    """ROCKETMQ_ROUTE_REWRITE=1（默认）时，把路由 Broker 地址改成本机 IPv4。"""
    global _patched
    if _patched:
        return
    if os.getenv("ROCKETMQ_ROUTE_REWRITE", "1").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        return
    try:
        from rocketmq.grpc_protocol import AddressScheme
        from rocketmq.v5.client.connection import RpcEndpoints
        from rocketmq.v5.model import topic_route as topic_route_mod
    except ImportError:
        return

    orig_init = topic_route_mod.MessageQueue.__init__

    def patched_init(self, queue):
        orig_init(self, queue)
        endpoints_pb = self._MessageQueue__broker_endpoints.endpoints
        changed = False
        for addr in endpoints_pb.addresses:
            new_host = _HOST_REWRITE.get((addr.host or "").strip())
            if new_host:
                addr.host = new_host
                changed = True
        if not changed:
            return
        endpoints_pb.scheme = AddressScheme.IPv4
        self._MessageQueue__broker_endpoints = RpcEndpoints(endpoints_pb)
        log.debug(
            "RocketMQ 路由地址已重写为宿主机 IPv4: %s",
            self._MessageQueue__broker_endpoints.facade,
        )

    topic_route_mod.MessageQueue.__init__ = patched_init
    _patched = True
