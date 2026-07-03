"""
岗位推荐语义缓存。

设计要点
--------
1. **scope（缓存分区）**：只有「同一套 KB 版本 + 检索引擎 + 推荐参数」的请求才互相比相似度，
   避免跨 LightRAG/GrepRAG、跨语料版本、跨模型档位误用旧结果。
2. **精确缓存**：对 normalize(rag_q) 做 SHA256，改写句完全一致时直接命中，无需算向量。
3. **语义缓存**：对指纹文本做**全维 embedding**，在 scope 桶内算**余弦相似度**，
   超过阈值则返回历史上保存的完整 API 响应（不截断向量维度）。
4. **存储**：Redis 单 key 存 JSON 数组（每 scope 最多 N 条，LRU 淘汰），与 student_redis 共用连接配置。

Redis 键约定
------------
- 精确：``job_info:sem:exact:v1:{scope_id}:{rag_q_hash}``
- 语义列表：``job_info:sem:v1:{scope_id}`` → JSON 数组，元素含 embedding / response / expires_at

环境变量
--------
JOB_INFO_SEM_CACHE_ENABLED          1/true 启用（默认关）
JOB_INFO_SEM_CACHE_EXACT_ENABLED    1/true 启用精确键（默认开）
JOB_INFO_SEM_CACHE_TTL_SEC          条目 TTL，默认 3600 秒
JOB_INFO_SEM_CACHE_MAX_ENTRIES      每 scope 最多条数，默认 300
JOB_INFO_SEM_CACHE_THRESHOLD        余弦相似度阈值，默认 0.94
JOB_INFO_SEM_CACHE_KB_VERSION       手动 KB 版本号，语料更新后请修改
JOB_INFO_SEM_CACHE_EMBED_LEVEL      embedding 档位，默认同 LIGHTRAG_EMBED_LEVEL
JOB_INFO_SEM_CACHE_INCLUDE_PROFILE  1 时 student_context 参与 scope 与指纹文本
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from model_cfg import load_model_list
from openai import OpenAI

from app.skills.job_info.context import RecommendRunCtx
from app.skills.job_info.llm_schema import resolve_analyze_response_format_mode
from app.skills.job_info.score_rubric import dimensions_scope_token, normalize_score_dimensions

log = logging.getLogger(__name__)

# Redis 键前缀（勿随意修改，否则旧缓存无法读取）
_REDIS: Any = None
_PREFIX = "job_info:sem"
_EXACT_PREFIX = f"{_PREFIX}:exact:v1"  # 精确缓存
_LIST_PREFIX = f"{_PREFIX}:v1"  # 语义缓存列表


def _env_bool(name: str, default: bool = False) -> bool:
    """读取环境变量是否为真（1/true/yes/on）。"""
    v = os.getenv(name, "1" if default else "0").strip().lower()
    return v in ("1", "true", "yes", "on")


def cache_enabled() -> bool:
    """是否启用语义/精确缓存（由 JOB_INFO_SEM_CACHE_ENABLED 控制）。"""
    return _env_bool("JOB_INFO_SEM_CACHE_ENABLED", default=False)


def _ttl_sec() -> int:
    """缓存条目与 Redis 键的过期时间（秒）。"""
    try:
        return max(60, int(os.getenv("JOB_INFO_SEM_CACHE_TTL_SEC", "3600")))
    except ValueError:
        return 3600


def _max_entries() -> int:
    """每个 scope 桶内最多保留的语义缓存条数，超出则按 created_at 淘汰最旧。"""
    try:
        return max(10, int(os.getenv("JOB_INFO_SEM_CACHE_MAX_ENTRIES", "300")))
    except ValueError:
        return 300


def _similarity_threshold() -> float:
    """语义命中所需的最小余弦相似度，越高越严格、误命中越少。"""
    try:
        return float(os.getenv("JOB_INFO_SEM_CACHE_THRESHOLD", "0.94"))
    except ValueError:
        return 0.94


def _include_profile_in_scope() -> bool:
    """学生画像是否参与 scope 与 embedding 指纹（画像会影响改写时应开启）。"""
    return _env_bool("JOB_INFO_SEM_CACHE_INCLUDE_PROFILE", default=True)


def _exact_enabled() -> bool:
    """是否启用 rag_q 精确键缓存。"""
    return _env_bool("JOB_INFO_SEM_CACHE_EXACT_ENABLED", default=True)


def _redis_client() -> Any:
    """懒加载 Redis 客户端（decode_responses=True，值为 str）。"""
    global _REDIS
    if _REDIS is not None:
        return _REDIS
    import redis

    _REDIS = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        db=int(os.getenv("REDIS_DATABASE", os.getenv("REDIS_DB", "0"))),
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=5,
    )
    return _REDIS


def kb_fingerprint(*, use_rag: bool) -> str:
    """
    知识库版本指纹，写入 scope，用于语料更新后隔离旧缓存。

    优先级：
    1. 环境变量 JOB_INFO_SEM_CACHE_KB_VERSION（推荐语料大更新时手动 bump）
    2. LightRAG：LIGHTRAG_WORKDIR
    3. GrepRAG：greprag_db.json 文件 mtime
    """
    manual = os.getenv("JOB_INFO_SEM_CACHE_KB_VERSION", "").strip()
    if manual:
        return manual
    if use_rag:
        return (os.getenv("LIGHTRAG_WORKDIR", "lightrag") or "lightrag").strip()
    db_path = os.getenv("GREPRAG_DB_PATH", "").strip()
    if not db_path:
        try:
            from pathlib import Path
            from app.common.runtime_config import load_runtime_config

            base = Path(__file__).resolve().parents[3]
            cfg = load_runtime_config()
            db_path = str(
                Path(
                    os.getenv(
                        "GREPRAG_DB_PATH",
                        cfg.get("greprag_db_path", str(base / "data" / "greprag" / "greprag_db.json")),
                    )
                ).expanduser()
            )
        except Exception:
            db_path = ""
    if db_path and os.path.isfile(db_path):
        try:
            return f"greprag_mtime_{int(os.path.getmtime(db_path))}"
        except OSError:
            pass
    return "greprag_default"


def build_scope(
    ctx: RecommendRunCtx,
    *,
    use_rag: bool,
    top_n_jobs: int,
    top_n_companies: int,
    student_context: str = "",
    use_student_profile: bool = True,
    score_baseline: int = 85,
    min_recommend_score: int = 85,
    score_dimensions: dict | None = None,
) -> str:
    """
    构造缓存分区字符串（逻辑桶名，非 Redis 键）。

    仅当 scope 相同才会在语义上互相比对；不同 scope 之间绝不命中。
    ctx 本身不写入 scope 字符串，但 rag_q 已通过 engine/kb/参数间接关联。
    """
    kb = kb_fingerprint(use_rag=use_rag)
    engine = "lightrag" if use_rag else "greprag"
    analyze_level = (os.getenv("JOB_RAG_ANALYZE_MODEL_LEVEL", "mid") or "mid").strip()
    analyze_fmt = resolve_analyze_response_format_mode()
    rewrite_off = _env_bool("JOB_RAG_QUERY_REWRITE_DISABLED", default=False)
    profile_part = "guest"
    if not use_student_profile:
        profile_part = "guest"
    elif _include_profile_in_scope():
        sc = (student_context or "").strip()
        if sc:
            profile_part = hashlib.sha256(sc.encode("utf-8")).hexdigest()[:16]
        else:
            profile_part = "none"
    baseline = max(0, min(100, int(score_baseline or 85)))
    min_score = max(0, min(100, int(min_recommend_score or 85)))
    dims = normalize_score_dimensions(score_dimensions)
    parts = [
        f"engine={engine}",
        f"kb={kb}",
        f"top_jobs={top_n_jobs}",
        f"top_co={top_n_companies}",
        f"analyze={analyze_level}",
        f"fmt={analyze_fmt}",
        f"rewrite_off={int(rewrite_off)}",
        f"profile={profile_part}",
        f"score_base={baseline}",
        f"min_score={min_score}",
        f"use_profile={int(bool(use_student_profile))}",
        f"dims={dimensions_scope_token(dims)}",
    ]
    return "|".join(parts)


def scope_id(scope: str) -> str:
    """将 scope 字符串哈希为固定长度 id，用作 Redis 键片段。"""
    return hashlib.sha256(scope.encode("utf-8")).hexdigest()[:24]


def canonical_cache_text(ctx: RecommendRunCtx, *, student_context: str = "") -> str:
    """
    用于计算 embedding 的指纹文本。

    - 以 **rag_q**（改写检索句）为主信号，与真实检索输入一致
    - **raw_query** 为辅，降低改写偏离原意时的误命中
    - 可选附带 **student_context** 全文（与 scope 中 profile hash 策略一致）
    """
    lines = [f"rag:{ctx.rag_q}", f"raw:{ctx.raw_query}"]
    if _include_profile_in_scope():
        sc = (student_context or "").strip()
        if sc:
            lines.append(f"profile:{sc}")
    return "\n".join(lines)


def _normalize_rag_q(rag_q: str) -> str:
    """精确缓存用：小写 + 合并空白，减少无意义差异。"""
    return " ".join((rag_q or "").strip().lower().split())


def _exact_key(scope: str, rag_q: str) -> str:
    """精确缓存 Redis 键。"""
    sid = scope_id(scope)
    qh = hashlib.sha256(_normalize_rag_q(rag_q).encode("utf-8")).hexdigest()[:32]
    return f"{_EXACT_PREFIX}:{sid}:{qh}"


def _list_key(scope: str) -> str:
    """语义缓存列表 Redis 键（值为 JSON 数组）。"""
    return f"{_LIST_PREFIX}:{scope_id(scope)}"


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    计算两向量的余弦相似度，范围约 [-1, 1]。

    使用全维向量，**不要**只取前 256/512 维，以免误命中/漏命中增多。
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def embed_text_sync(text: str) -> List[float]:
    """
    同步调用 OpenAI 兼容 Embeddings API，返回浮点向量。

    模型与密钥与 LightRAG 共用 modelCfg（LIGHTRAG_EMBED_* / JOB_INFO_SEM_CACHE_EMBED_LEVEL）。
    """
    from app.rag.lightrag.embedding_config import resolve_embedding_params
    from app.rag.lightrag.runtime import select_embedding_entry

    level = (
        os.getenv("JOB_INFO_SEM_CACHE_EMBED_LEVEL")
        or os.getenv("LIGHTRAG_EMBED_LEVEL", "mid")
        or "mid"
    ).strip()
    entries = load_model_list()
    emb_entry = select_embedding_entry(level)
    if emb_entry is None and not entries:
        raise RuntimeError("无可用模型配置，无法计算语义缓存向量")
    chat_entry = emb_entry or entries[0]
    cfg = resolve_embedding_params(chat_entry, emb_entry)
    client = OpenAI(api_key=str(cfg["key"]), base_url=str(cfg["api"]))
    model = str(cfg["model"])
    resp = client.embeddings.create(model=model, input=(text or "").strip())
    vec = resp.data[0].embedding
    if not isinstance(vec, list):
        raise ValueError("embedding 返回格式异常")
    return [float(x) for x in vec]


def _load_entries(r: Any, list_key: str) -> List[Dict[str, Any]]:
    """从 Redis 读取某 scope 下全部语义缓存条目。"""
    raw = r.get(list_key)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        log.warning("语义缓存列表 JSON 损坏，将重置 key=%s", list_key)
        return []


def _save_entries(r: Any, list_key: str, entries: List[Dict[str, Any]]) -> None:
    """写回语义缓存列表并刷新 TTL。"""
    r.setex(list_key, _ttl_sec(), json.dumps(entries, ensure_ascii=False))


def lookup(
    ctx: RecommendRunCtx,
    *,
    scope: str,
    student_context: str = "",
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    查询缓存。

    顺序：精确键（rag_q）→ 语义近邻（全维余弦）。

    Returns:
        命中：``(完整 API 响应 dict, cache 元信息 dict)``，响应内**不含** cache 字段；
        由 pipeline 合并 ``cache`` 到顶层。
        未命中：``None``。
    """
    if not cache_enabled():
        return None
    try:
        r = _redis_client()
    except Exception as e:
        log.warning("语义缓存 Redis 不可用: %s", e)
        return None

    # --- 1) 精确命中：改写检索句归一化后完全一致 ---
    if _exact_enabled():
        try:
            ex_key = _exact_key(scope, ctx.rag_q)
            raw = r.get(ex_key)
            if raw:
                resp = json.loads(raw)
                if isinstance(resp, dict):
                    log.info("岗位推荐缓存精确命中 scope=%s", scope_id(scope))
                    return dict(resp), {
                        "hit": True,
                        "type": "exact",
                        "similarity": 1.0,
                        "scope": scope_id(scope),
                    }
        except Exception as e:
            log.warning("语义缓存精确读失败: %s", e)

    # --- 2) 语义命中：当前请求向量 vs 桶内历史向量 ---
    try:
        query_vec = embed_text_sync(canonical_cache_text(ctx, student_context=student_context))
    except Exception as e:
        log.warning("语义缓存 embedding 失败，跳过: %s", e)
        return None

    list_key = _list_key(scope)
    entries = _load_entries(r, list_key)
    if not entries:
        return None

    threshold = _similarity_threshold()
    best_sim = -1.0
    best_entry: Optional[Dict[str, Any]] = None
    now = time.time()

    for ent in entries:
        if not isinstance(ent, dict):
            continue
        exp = float(ent.get("expires_at") or 0)
        if exp and exp < now:
            continue  # 跳过已过期条目
        vec = ent.get("embedding")
        if not isinstance(vec, list):
            continue
        sim = cosine_similarity(query_vec, vec)
        if sim > best_sim:
            best_sim = sim
            best_entry = ent

    if best_entry is None or best_sim < threshold:
        return None

    resp = best_entry.get("response")
    if not isinstance(resp, dict):
        return None

    log.info(
        "岗位推荐缓存语义命中 scope=%s similarity=%.4f threshold=%.4f",
        scope_id(scope),
        best_sim,
        threshold,
    )
    return dict(resp), {
        "hit": True,
        "type": "semantic",
        "similarity": round(best_sim, 4),
        "threshold": threshold,
        "scope": scope_id(scope),
        "cached_rag_q": best_entry.get("rag_q", ""),
    }


def store(
    ctx: RecommendRunCtx,
    *,
    scope: str,
    response: Dict[str, Any],
    student_context: str = "",
) -> None:
    """
    写入缓存（精确键 + 语义列表）。

    - 写入前会去掉 response 内已有的 ``cache`` 字段，避免嵌套污染
    - 语义列表超限时按 ``created_at`` 保留最新 ``MAX_ENTRIES`` 条

    未启用缓存或 Redis 不可用时静默跳过。
    """
    if not cache_enabled():
        return
    try:
        r = _redis_client()
    except Exception as e:
        log.warning("语义缓存 Redis 不可用，跳过写入: %s", e)
        return

    payload = dict(response)
    payload.pop("cache", None)

    if _exact_enabled():
        try:
            ex_key = _exact_key(scope, ctx.rag_q)
            r.setex(ex_key, _ttl_sec(), json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            log.warning("语义缓存精确写失败: %s", e)

    try:
        vec = embed_text_sync(canonical_cache_text(ctx, student_context=student_context))
    except Exception as e:
        log.warning("语义缓存写入 embedding 失败: %s", e)
        return

    list_key = _list_key(scope)
    entries = _load_entries(r, list_key)
    now = time.time()
    # 写前清理已过期条目
    entries = [e for e in entries if isinstance(e, dict) and float(e.get("expires_at") or 0) > now]

    entries.append(
        {
            "id": uuid.uuid4().hex,
            "embedding": vec,
            "response": payload,
            "rag_q": ctx.rag_q[:500],
            "raw_query": ctx.raw_query[:500],
            "created_at": now,
            "expires_at": now + _ttl_sec(),
        }
    )

    max_n = _max_entries()
    if len(entries) > max_n:
        entries.sort(key=lambda x: float(x.get("created_at") or 0))
        entries = entries[-max_n:]

    try:
        _save_entries(r, list_key, entries)
        log.debug("语义缓存已写入 scope=%s entries=%s", scope_id(scope), len(entries))
    except Exception as e:
        log.warning("语义缓存列表写失败: %s", e)


def clear_all_caches() -> Dict[str, Any]:
    """
    清空岗位推荐语义/精确缓存（Redis 键前缀 ``job_info:sem``）。

    与 ``JOB_INFO_SEM_CACHE_ENABLED`` 无关：即使当前未启用，也可清理历史残留键。
    """
    try:
        r = _redis_client()
    except Exception as e:
        log.warning("语义缓存 Redis 不可用，无法清空: %s", e)
        return {
            "cleared": False,
            "deleted_keys": 0,
            "message": f"Redis 不可用: {e}",
        }

    deleted = 0
    try:
        for key in r.scan_iter(match=f"{_PREFIX}*"):
            r.delete(key)
            deleted += 1
    except Exception as e:
        log.warning("语义缓存清空失败: %s", e)
        return {
            "cleared": False,
            "deleted_keys": deleted,
            "message": str(e),
        }

    log.info("岗位推荐语义缓存已清空 deleted_keys=%s", deleted)
    return {
        "cleared": True,
        "deleted_keys": deleted,
        "message": "已清除岗位推荐语义缓存",
    }
