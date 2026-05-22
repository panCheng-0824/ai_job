"""
================================================================================
Day 5 —— Milvus 向量数据库 CRUD 学习示例（配合本地 Docker）
================================================================================

前置条件
--------
1) 已用 Docker 启动 Milvus（默认会监听 **19530** 端口，gRPC）。
2) 安装 Python SDK::

       pip install pymilvus langchain-ollama

3) **自然语言转向量（语义检索）** 默认使用本机 **Ollama** 的嵌入模型（与 Day1 同一套服务）::

       ollama pull nomic-embed-text

   嵌入向量维度须与集合 ``embedding`` 字段的 ``dim`` 一致（本文件默认 **768**，对应 ``nomic-embed-text``）。
   若你曾用旧版 **dim=8** 建过同名集合，请先删除该 Collection 或使用环境变量 ``MILVUS_COLLECTION`` 换新表名。

   本示例按 **pymilvus 2.4+**（含 2.5）写法；若报错请检查版本与 Milvus 服务端主版本是否一致。

你会学到什么
------------
- **C**reate：建 Collection（定义 Schema）、建向量索引、`insert` / `upsert`
- **R**ead：`query`（按标量条件过滤）、`search`（按向量相似度检索）
- **U**pdate：Milvus 里常用 **`upsert`**（主键已存在则覆盖，不存在则插入）
- **D**elete：`delete(expr=...)` 按布尔表达式删除

重要概念（读一遍再往下看代码）
------------------------------
- **Collection**：类似「表」，但有 **Schema**（字段名、类型、哪一列是主键、哪一列是向量）。
- **Entity / 实体**：一行数据；向量列维度必须和 Schema 里声明的 **dim** 一致。
- **flush**：把内存缓冲区数据 **持久化** 到对象存储/段文件（学习阶段可理解为「尽量落盘」）。
- **index + load**：向量检索前通常要对向量列建 **索引**，并把 Collection **加载到内存**（`load`）后才能稳定 `search`。
- **expr**：删除、查询时使用的 **布尔表达式**（类似 SQL WHERE 子句的简化版）。

Docker 默认连接参数（可按你 docker-compose 修改）
------------------------------------------------
- 主机：localhost
- 端口：19530

若 Milvus 跑在别的机器或映射端口不同，请改下面 ``MilvusConfig`` 或设置环境变量
``MILVUS_HOST`` / ``MILVUS_PORT``。

图形界面（如 Attu）里看不到集合时，常见原因
------------------------------------------
1) **连错实例**：脚本默认 ``127.0.0.1:19530``；Docker 若映射成 ``宿主机:19531 -> 容器:19530``，
   应设置 ``MILVUS_PORT=19531``，Attu 里也要填同一地址端口。
2) **集合名**：本示例固定为 **study01_day5_notes**，不是 ``day5``。
3) **数据库**：Milvus 2.2+ 有多数据库；未指定时一般为 **default**。Attu 左上角请选 **default** 再刷新列表。
4) **脚本其实报错退出**：中间某步失败则不会留下集合；请看终端完整报错。
5) **release 不会删表**：脚本结束时的 ``release()`` 只是从内存卸载，**不会**删除 collection。

初学者如何阅读本文件（已在下文分节写细注释）
------------------------------------------
- **配置区**：``MilvusConfig`` / ``OllamaEmbedConfig`` —— 先搞清 host、port、集合名、向量维度。
- **连接**：``connect_milvus`` / ``disconnect_milvus`` —— 对应「连上 / 断开」数据库。
- **建表**：Schema、``create_collection_if_not_exists`` —— 理解主键、向量列、标量列。
- **写入与检索**：``insert``、``search``、``embed_documents_texts`` —— 与 Day6 同一套嵌入思路。
- **命令行**：文件末尾 ``argparse`` —— ``--legacy-random`` 无需 Ollama，纯学 Milvus API。

提示：本文件注释已很长；若你更熟悉 Agent 路线，可从 ``run_semantic_learning_demo`` 倒着往上读。
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Sequence

from langchain_ollama import OllamaEmbeddings

# -----------------------------------------------------------------------------
# PyMilvus：Milvus 官方 Python SDK（ORM 风格 API）
# -----------------------------------------------------------------------------
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)


# =============================================================================
# 一、连接配置（集中管理，方便你对照 Docker 文档改参数）
# =============================================================================


@dataclass(frozen=True)
class MilvusConfig:
    """
    Milvus 连接与示例 Collection 元信息。

    Attributes:
        host: Milvus 地址。Docker 本机一般填 localhost；Linux 上有时填 172.17.0.1 等网桥 IP。
        port: gRPC 端口，官方镜像默认 **19530**。
        alias: PyMilvus 连接别名，同一进程内多连接时才需要区分；入门阶段固定 "default" 即可。
        collection_name: 下面示例用的集合名，避免和你其它实验冲突可随意改字符串。
        vector_dim: 向量维度。**语义检索**须与嵌入模型输出维数一致（如 nomic-embed-text 为 768）；
            ``--legacy-random`` 模式使用 8 维随机向量。
        metric_type: 向量索引与检索度量。**COSINE** 适合同一嵌入模型生成的语义向量；旧版随机演示用 **L2**。
    """

    host: str = os.environ.get("MILVUS_HOST", "127.0.0.1")
    port: int = int(os.environ.get("MILVUS_PORT", "19530"))
    alias: str = "default"
    collection_name: str = os.environ.get("MILVUS_COLLECTION", "study01_day5_notes")
    vector_dim: int = int(os.environ.get("MILVUS_VECTOR_DIM", "768"))
    metric_type: str = os.environ.get("MILVUS_METRIC", "COSINE")


@dataclass(frozen=True)
class OllamaEmbedConfig:
    """
    Ollama 文本嵌入配置（自然语言 → 向量）。

    与 ``ChatOpenAI(base_url=ollama)`` 类似，这里用 LangChain 的 ``OllamaEmbeddings`` 调 Ollama 的 /api/embeddings。
    """

    model: str = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    base_url: str = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


# 示例里向量列、主键列、标题列的字段名（字符串常量，避免魔法字散落）
PK_FIELD = "note_id"
VECTOR_FIELD = "embedding"
TITLE_FIELD = "title"


# =============================================================================
# 二、连接 / 断开（资源管理）
# =============================================================================


def connect_milvus(cfg: MilvusConfig) -> None:
    """
    建立到 Milvus 的一条连接。

    说明：
    - ``connections.connect`` 是 **进程级** 连接池入口；重复 connect 同一 alias 可能抛错，
      因此下面用 ``has_connection`` 做了幂等保护。
    - 若连不上，优先检查：Docker 是否启动、端口是否映射、防火墙、以及 Milvus 版本。
    """
    if connections.has_connection(cfg.alias):
        return
    # timeout：秒；连不上时尽快失败，避免脚本长时间卡住（可按网络情况调大）
    connections.connect(alias=cfg.alias, host=cfg.host, port=cfg.port, timeout=30)


def disconnect_milvus(cfg: MilvusConfig) -> None:
    """断开别名对应的连接（脚本结束或单测清理时调用）。"""
    if connections.has_connection(cfg.alias):
        connections.disconnect(alias=cfg.alias)


# =============================================================================
# 三、Schema 与 Collection 创建（Create —— 建表）
# =============================================================================


def build_note_collection_schema(cfg: MilvusConfig) -> CollectionSchema:
    """
    定义本示例的「笔记」集合结构。

    字段解释：
    1) note_id（VARCHAR 主键，非自增）
       - 由 **业务侧** 指定，例如 "note-001"。
       - 选择 VARCHAR 主键便于和外部系统 ID 对齐；亦可用 INT64 主键，看业务需求。

    2) embedding（FLOAT_VECTOR）
       - 存放 **稠密向量**；维度必须等于 cfg.vector_dim。
       - **语义场景**：用嵌入模型把标题/正文等文本编成向量；**legacy 演示**：用随机向量。

    3) title（VARCHAR）
       - 普通标量字段，可用于 query 过滤或展示。

    enable_dynamic_field：
       - 打开后允许插入 **未在 Schema 声明** 的额外键（进阶）；入门示例保持 False 更直观。
    """
    fields = [
        FieldSchema(
            name=PK_FIELD,
            dtype=DataType.VARCHAR,
            is_primary=True,
            auto_id=False,
            max_length=64,
        ),
        FieldSchema(name=VECTOR_FIELD, dtype=DataType.FLOAT_VECTOR, dim=cfg.vector_dim),
        FieldSchema(name=TITLE_FIELD, dtype=DataType.VARCHAR, max_length=256),
    ]
    return CollectionSchema(fields=fields, description="Day5 学习用笔记向量表", enable_dynamic_field=False)


def create_collection_if_not_exists(cfg: MilvusConfig) -> Collection:
    """
    若集合不存在则创建，并返回 Collection 句柄。

    这是 **Create** 的第一步：在 Milvus 里注册集合元数据（尚不包含索引与数据）。
    """
    if utility.has_collection(cfg.collection_name, using=cfg.alias):
        return Collection(cfg.collection_name, using=cfg.alias)

    schema = build_note_collection_schema(cfg)
    coll = Collection(name=cfg.collection_name, schema=schema, using=cfg.alias)
    return coll


def drop_collection_if_exists(cfg: MilvusConfig) -> None:
    """
    删除整个集合（包括数据与索引）。

    学习时用于「清空重来」；生产环境 **慎用**。
    """
    if utility.has_collection(cfg.collection_name, using=cfg.alias):
        utility.drop_collection(cfg.collection_name, using=cfg.alias)


# =============================================================================
# 四、索引与 load（为向量检索做准备）
# =============================================================================


def ensure_vector_index_and_load(collection: Collection, cfg: MilvusConfig) -> None:
    """
    为向量列创建索引并将集合加载到内存。

    为什么需要？
    - ``search``（相似度检索）依赖向量索引结构；数据量很小可用 FLAT（暴力检索），易理解。
    - ``load`` 之后，查询/检索会在 **QueryNode** 侧就绪（细节可略过，先记流程）。

    metric_type：
    - **L2**：欧氏距离，越小越相似。
    - **IP**：内积，越大越相似（常用于已归一化向量）。

    数据量变大后应改用 IVF、HNSW 等索引；Day5 以学习流程为主。
    """
    collection.flush()
    if not collection.has_index():
        index_params = {"index_type": "FLAT", "metric_type": cfg.metric_type, "params": {}}
        collection.create_index(field_name=VECTOR_FIELD, index_params=index_params)
    collection.load()


# =============================================================================
# 五、插入数据（Create —— 增）
# =============================================================================


def insert_notes(
    collection: Collection,
    note_ids: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    titles: Sequence[str],
) -> Any:
    """
    批量插入实体（Create）。

    PyMilvus 的 ``insert`` 入参是 **按列组织** 的列表，顺序必须与 Schema 字段顺序一致：
    本示例 Schema 顺序为：note_id → embedding → title。

    返回值：
    - InsertResult，含主键列表、插入条数等；学习阶段可只关心是否抛异常。

    注意：
    - 若主键重复且使用普通 ``insert``，可能产生重复主键数据（视版本与配置而定）；
      需要「有则更新」请用 ``upsert_notes``。
    """
    if not (len(note_ids) == len(embeddings) == len(titles)):
        raise ValueError("note_ids、embeddings、titles 长度必须一致")
    entities = [list(note_ids), list(embeddings), list(titles)]
    return collection.insert(entities)


def upsert_notes(
    collection: Collection,
    note_ids: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    titles: Sequence[str],
) -> Any:
    """
    批量 **Upsert**（Update + Insert 合一）。

    语义（与关系库 UPSERT 类似）：
    - 主键不存在 → 插入新行
    - 主键已存在 → 用新数据 **覆盖** 旧实体（具体行为以你服务端版本为准，2.4+ 一般如此）

    适用：同步外部文档库、反复写入同一 note_id 的最新向量与标题。
    """
    if not (len(note_ids) == len(embeddings) == len(titles)):
        raise ValueError("note_ids、embeddings、titles 长度必须一致")
    entities = [list(note_ids), list(embeddings), list(titles)]
    return collection.upsert(entities)


# =============================================================================
# 六、查询（Read —— 标量条件）
# =============================================================================


def query_notes(
    collection: Collection,
    expr: str,
    output_fields: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    使用布尔表达式 **query**（Read，非向量相似度）。

    expr 示例：
    - ``note_id == "note-001"``
    - ``note_id in ["note-001", "note-002"]``
    - ``title like "Mil%"``（是否支持 like 取决于版本与字段类型，详见 Milvus 文档）

    output_fields：
    - 需要返回的列名列表；向量字段也可查，但结果体积大。

    limit：
    - 最多返回多少条；Milvus 新版 API 可能用 ``limit`` 参数名，此处与 pymilvus 对齐。
    """
    fields = output_fields or [PK_FIELD, TITLE_FIELD]
    kwargs: Dict[str, Any] = {"expr": expr, "output_fields": fields}
    if limit is not None:
        kwargs["limit"] = limit
    return list(collection.query(**kwargs))


# =============================================================================
# 七、向量检索（Read —— 相似度搜索）
# =============================================================================


def search_similar_notes(
    collection: Collection,
    query_vectors: List[List[float]],
    top_k: int = 3,
    expr: Optional[str] = None,
    metric_type: str = "COSINE",
) -> Any:
    """
    向量相似度检索（Read）。

    参数：
    - query_vectors：一组查询向量，每个向量长度须等于建表 dim；可一次搜多条（batch）。
    - top_k：每个查询向量返回前 K 个最相似结果。
    - expr：可选的 **标量过滤**（先过滤再检索），例如只搜某用户的数据。
    - metric_type：须与建索引时一致（如 **COSINE**、**L2**、**IP**）。

    返回：
    - SearchResult，可迭代；每条命中含 id、distance、entity 等字段。
    """
    search_params = {"metric_type": metric_type, "params": {}}
    return collection.search(
        data=query_vectors,
        anns_field=VECTOR_FIELD,
        param=search_params,
        limit=top_k,
        expr=expr,
        output_fields=[PK_FIELD, TITLE_FIELD],
    )


# =============================================================================
# 八、删除（Delete）
# =============================================================================


def delete_notes_by_expr(collection: Collection, expr: str) -> Any:
    """
    按表达式删除（Delete）。

    典型 expr：
    - ``note_id == "note-001"``
    - ``note_id in ["note-001","note-002"]``

    删除后若立刻查询，建议 ``flush`` 以便行为更符合直觉（是否必须取决于读写路径）。
    """
    return collection.delete(expr)


# =============================================================================
# 九、自然语言 → 向量（Embedding）与按语义搜索
# =============================================================================
#
# 流程：文本 --嵌入模型--> 浮点向量 --Milvus search--> 与库内向量最相近的实体。
# 注意：入库时的文本与查询必须使用 **同一模型**，维度、度量类型与建表一致。
# =============================================================================


def create_ollama_embedder(ecfg: Optional[OllamaEmbedConfig] = None) -> OllamaEmbeddings:
    """
    构造 Ollama 嵌入客户端（LangChain）。

    Ollama 需在本地运行（``ollama serve``），并已 ``ollama pull`` 对应 embed 模型。
    """
    ecfg = ecfg or OllamaEmbedConfig()
    return OllamaEmbeddings(model=ecfg.model, base_url=ecfg.base_url)


def embed_query_text(embedder: OllamaEmbeddings, text: str) -> List[float]:
    """
    将 **单条** 自然语言编码为向量（List[float]）。

    LangChain 统一入口 ``embed_query``：适合「用户问句」这类查询文本。
    """
    vec = embedder.embed_query(text)
    if not vec:
        raise RuntimeError("嵌入模型返回空向量，请检查 Ollama 模型是否已拉取。")
    return list(vec)


def embed_documents_texts(embedder: OllamaEmbeddings, texts: Sequence[str]) -> List[List[float]]:
    """
    将 **多条** 文本批量编码为向量列表。

    与 ``embed_query`` 相比，``embed_documents`` 在部分后端会做批处理；入库时优先用它。
    """
    if not texts:
        return []
    rows = embedder.embed_documents(list(texts))
    return [list(v) for v in rows]


def assert_vector_dim(vec: Sequence[float], expected: int, *, context: str) -> None:
    if len(vec) != expected:
        raise ValueError(
            f"{context}: 向量维度为 {len(vec)}，与 MilvusConfig.vector_dim={expected} 不一致。"
            "请改用匹配的嵌入模型，或调整 MILVUS_VECTOR_DIM / 重建集合。"
        )


def search_by_natural_language(
    collection: Collection,
    embedder: OllamaEmbeddings,
    query_text: str,
    cfg: MilvusConfig,
    top_k: int = 5,
    expr: Optional[str] = None,
) -> Any:
    """
    用 **自然语言** 在向量库中做相似度检索（先 embed_query，再 ``search``）。

    Args:
        collection: 已 load、且已建向量索引的 Collection。
        embedder: 与入库时相同的 OllamaEmbeddings。
        query_text: 用户问题或检索用语（中文、英文均可，取决于模型能力）。
        cfg: 其中的 ``vector_dim``、``metric_type`` 须与建表/建索引一致。
        top_k: 返回最相近的 K 条。
        expr: 可选标量过滤表达式。
    """
    qvec = embed_query_text(embedder, query_text)
    assert_vector_dim(qvec, cfg.vector_dim, context="查询向量")
    return search_similar_notes(
        collection,
        query_vectors=[qvec],
        top_k=top_k,
        expr=expr,
        metric_type=cfg.metric_type,
    )


def run_semantic_learning_demo(
    cfg: MilvusConfig,
    ecfg: Optional[OllamaEmbedConfig] = None,
    *,
    reset: bool = True,
    demo_query: str = "如何用向量数据库做语义检索？",
) -> None:
    """
    **语义版**演示：标题文本 → 嵌入 → 写入 Milvus；自然语言问句 → 嵌入 → search。

    默认 ``vector_dim=768``、``metric_type=COSINE``，与 ``nomic-embed-text`` 常见配置一致。
    若模型实际维度不同，会先探测并 ``dataclasses.replace`` 更新 cfg。
    """
    embedder = create_ollama_embedder(ecfg)
    probe = embed_query_text(embedder, "dimension_probe")
    cfg = replace(cfg, vector_dim=len(probe))
    if cfg.metric_type not in ("COSINE", "L2", "IP"):
        raise ValueError(f"不支持的 metric_type: {cfg.metric_type}")

    connect_milvus(cfg)
    try:
        if reset:
            drop_collection_if_exists(cfg)

        coll = create_collection_if_not_exists(cfg)

        # 示例笔记：标题即「可检索的语义文本」；向量由标题嵌入得到（真实业务可改为正文 chunk）
        ids = ["note-001", "note-002", "note-003", "note-004"]
        titles = [
            "Milvus 向量数据库入门与 Docker 部署",
            "自然语言处理中的文本嵌入 embedding 简介",
            "Python 使用 pymilvus 做 CRUD 和相似度搜索",
            "今天天气不错，适合出门跑步",
        ]
        vectors = embed_documents_texts(embedder, titles)
        if len(vectors) != len(ids):
            raise RuntimeError("嵌入结果条数与笔记条数不一致")
        for i, v in enumerate(vectors):
            assert_vector_dim(v, cfg.vector_dim, context=f"第 {i} 条笔记向量")

        insert_notes(coll, ids, vectors, titles)
        coll.flush()
        ensure_vector_index_and_load(coll, cfg)

        print("\n【语义检索】查询语句：", demo_query)
        res = search_by_natural_language(coll, embedder, demo_query, cfg, top_k=3)
        print_search_results(res)

        coll.release()
        names = utility.list_collections(using=cfg.alias)
        print("\n【确认】当前数据库中的集合列表：", names)
        print("【确认】集合名：", cfg.collection_name, "维度：", cfg.vector_dim, "度量：", cfg.metric_type)
    finally:
        disconnect_milvus(cfg)


def run_query_only(
    cfg: MilvusConfig,
    query_text: str,
    ecfg: Optional[OllamaEmbedConfig] = None,
    top_k: int = 5,
) -> None:
    """
    只对 **已存在** 的集合做一次自然语言检索（不写库、不删表）。

    使用前请保证集合的 dim / metric 与当前嵌入模型、cfg 一致。
    """
    embedder = create_ollama_embedder(ecfg)
    probe = embed_query_text(embedder, "dimension_probe")
    cfg = replace(cfg, vector_dim=len(probe))

    connect_milvus(cfg)
    try:
        if not utility.has_collection(cfg.collection_name, using=cfg.alias):
            print("集合不存在：", cfg.collection_name, file=sys.stderr)
            sys.exit(1)
        coll = Collection(cfg.collection_name, using=cfg.alias)
        coll.load()
        res = search_by_natural_language(coll, embedder, query_text, cfg, top_k=top_k)
        print_search_results(res)
        coll.release()
    finally:
        disconnect_milvus(cfg)


# =============================================================================
# 十、小工具：随机向量 & 打印 Search 结果
# =============================================================================


def random_vector(dim: int) -> List[float]:
    """生成 dim 维随机向量，仅用于本地学习，不代表真实语义。"""
    return [random.random() for _ in range(dim)]


def print_search_results(res: Any) -> None:
    """把 search 返回结果用可读形式打印出来。"""
    for i, hits in enumerate(res):
        print(f"\n--- 查询向量 #{i} 的 Top 结果 ---")
        for hit in hits:
            print(f"  id={hit.id}, distance={hit.distance}, entity={hit.entity}")


# =============================================================================
# 十一、串联演示：从连接到 CRUD 跑通一遍（Legacy 随机向量）
# =============================================================================


def run_learning_demo(cfg: MilvusConfig, *, reset: bool = True) -> None:
    """
    **Legacy**：随机向量 + CRUD 全流程（无需 Ollama）。用于理解 Milvus API；无语义。

    请使用 ``MilvusConfig(vector_dim=8, metric_type="L2")`` 与旧版教程一致。

    Args:
        cfg: 连接与表名配置。
        reset: True 时先 drop 再建，保证每次运行状态干净；改 False 可在表里累加数据。
    """
    connect_milvus(cfg)
    try:
        if reset:
            drop_collection_if_exists(cfg)

        coll = create_collection_if_not_exists(cfg)

        # ----- Create：插入 3 条笔记 -----
        dim = cfg.vector_dim
        ids = ["note-001", "note-002", "note-003"]
        vectors = [random_vector(dim), random_vector(dim), random_vector(dim)]
        titles = ["第一条笔记", "Milvus CRUD 学习", "第三条备用"]
        insert_notes(coll, ids, vectors, titles)
        coll.flush()

        # 为向量列建索引并 load（否则 search 可能不可用或报错）
        ensure_vector_index_and_load(coll, cfg)

        # ----- Read：query 按主键/标题过滤 -----
        rows = query_notes(coll, expr=f'{PK_FIELD} == "note-002"', output_fields=[PK_FIELD, TITLE_FIELD])
        print("\n【Query】note_id == note-002：", rows)

        # ----- Read：search 用第一条向量当 query，找最相近的 top2 -----
        res = search_similar_notes(
            coll, query_vectors=[vectors[0]], top_k=2, metric_type=cfg.metric_type
        )
        print_search_results(res)

        # ----- Update：upsert 覆盖 note-002 的标题与向量 -----
        new_vec = random_vector(dim)
        upsert_notes(coll, ["note-002"], [new_vec], ["标题已被 upsert 更新"])
        coll.flush()
        rows2 = query_notes(coll, expr=f'{PK_FIELD} == "note-002"', output_fields=[PK_FIELD, TITLE_FIELD, VECTOR_FIELD])
        print("\n【Query】upsert 后 note-002：", rows2)

        # ----- Delete：删除 note-003 -----
        delete_notes_by_expr(coll, f'{PK_FIELD} == "note-003"')
        coll.flush()
        # num_entities：集合中实体条数（学习阶段用来确认删除是否生效；与 query 全表不同，更直观）
        print("\n【统计】删除并 flush 后实体数量：", coll.num_entities)

        # 释放内存（可选）：release 后需再 load 才能 search（不会删除集合）
        coll.release()

        # 方便你在 Attu / 其它工具里对照：脚本连的是哪个库、集合是否真的存在
        names = utility.list_collections(using=cfg.alias)
        print("\n【确认】本脚本使用的连接别名：", cfg.alias)
        print("【确认】当前数据库中的集合列表：", names)
        print("【确认】Day5 示例集合名应为：", cfg.collection_name)
        if cfg.collection_name not in names:
            print(
                "⚠ 若上面列表里没有该名字，说明连到的不是你以为的那台 Milvus，"
                "或 db_name 与图形界面选中的「数据库」不一致（默认均为 default）。"
            )

    finally:
        disconnect_milvus(cfg)


if __name__ == "__main__":
    # argparse：把命令行参数解析成 Python 变量；子命令多时可用 subparsers，这里用可选 flag 即可。
    parser = argparse.ArgumentParser(description="Day5：Milvus CRUD + 自然语言语义检索（Ollama 嵌入）")
    parser.add_argument(
        "--legacy-random",
        action="store_true",
        help="使用 8 维随机向量跑旧版 CRUD 全流程（不需要 Ollama）",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        metavar="TEXT",
        help="仅对已有集合执行一次自然语言检索后退出（不写库）",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="语义演示时不先 drop 集合（在已有数据上追加 insert 可能主键冲突）",
    )
    parser.add_argument(
        "--demo-query",
        type=str,
        default="如何用向量数据库做语义检索？",
        help="语义演示结束时的示例问句",
    )
    args = parser.parse_args()

    # 分支优先级：显式 --query 优先；否则看是否 legacy；最后走默认语义演示。
    if args.query is not None:
        run_query_only(MilvusConfig(), args.query, top_k=5)
    elif args.legacy_random:
        # 8 维 + L2：与旧版随机向量教程一致，和 nomic 768 维无关。
        legacy_cfg = MilvusConfig(vector_dim=8, metric_type="L2")
        run_learning_demo(legacy_cfg, reset=not args.no_reset)
    else:
        # 默认：Ollama 嵌入 + 语义写入/检索（需 ollama pull nomic-embed-text）
        run_semantic_learning_demo(
            MilvusConfig(),
            reset=not args.no_reset,
            demo_query=args.demo_query,
        )
