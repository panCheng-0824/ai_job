"""
本地开发：为 rocketmq-python-client 注入「跳过证书校验」的 gRPC TLS。

Docker 内置 Proxy 默认自签名证书；不设此项时 tls_enable=True 会 CERTIFICATE_VERIFY_FAILED，
tls_enable=False 会在 startup() 永久阻塞。
"""

from __future__ import annotations

import os
import ssl

_patched = False


def patch_grpc_insecure_tls_if_needed() -> None:
    """按环境变量 ``ROCKETMQ_TLS_INSECURE=1`` 打补丁（仅进程内一次）。"""
    global _patched
    if _patched:
        return
    if os.getenv("ROCKETMQ_TLS_INSECURE", "1").strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return
    import grpc
    import grpc.aio as aio

    def _ssl_creds_dev():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return grpc.ssl_channel_credentials(ctx)

    def _secure_channel(target, credentials, options=None, compression=None):
        return aio.insecure_channel.__wrapped__(  # type: ignore[attr-defined]
            target, _ssl_creds_dev(), options, compression
        )

    # 保留原始实现引用，用自定义 credentials 替换
    if not hasattr(aio, "_rocketmq_orig_secure_channel"):
        aio._rocketmq_orig_secure_channel = aio.secure_channel  # type: ignore[attr-defined]

        def _patched_secure(target, credentials, options=None, compression=None):
            return aio._rocketmq_orig_secure_channel(  # type: ignore[attr-defined]
                target, _ssl_creds_dev(), options, compression
            )

        aio.secure_channel = _patched_secure  # type: ignore[assignment]
    _patched = True
