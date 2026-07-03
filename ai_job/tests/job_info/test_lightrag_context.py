"""LightRAG 检索上下文净化 — 内部验证用例。"""

from __future__ import annotations

import json

import pytest

from app.skills.job_info.lightrag_context import (
    dedupe_job_chunks,
    extract_job_id,
    normalize_lightrag_retrieval_context,
    parse_lightrag_document_chunks,
    parse_reference_document_list,
)


# --- 用户真实场景：新版 JSONL + Reference List + KG 噪音 ---
USER_LIKE_RAW = """Knowledge Graph Data (Entity):

```json
{"entity": "Design Role", "type": "concept", "description": "noise that wastes tokens"}
{"entity": "Visual Design Skills", "type": "method", "description": "more noise"}
```

Knowledge Graph Data (Relationship):

```json
{"entity1": "A", "entity2": "B", "description": "relationship noise"}
```

Document Chunks (Each entry has a reference_id refer to the `Reference Document List`):

```json
{"reference_id": "1", "content": "【岗位三：视觉设计储备项目经理】\\n任职资格：视觉传达设计"}
{"reference_id": "4", "content": "【岗位三：视觉设计储备项目经理】\\n更多内容但仍是短片段"}
{"reference_id": "5", "content": "# 岗位信息：科大讯飞2026届春季校园招聘——设计类\\n\\n## 基本信息\\n- 岗位ID：d99d05fe282741c9b3d276b666a59290\\n- 职位名称：设计类\\n\\n## 岗位描述\\n设计类校招。"}
{"reference_id": "3", "content": "# 岗位信息：祖龙游戏\\n\\n## 基本信息\\n- 岗位ID：a85a0c0382d04970a0ea91ce0d78e7a9\\n- 职位名称：美术设计类\\n\\n## 岗位描述\\n游戏美术。"}
```

Reference Document List (Each entry starts with a [reference_id] that corresponds to entries in the Document Chunks):

```
[1] job-fbc79cd6f4be4b82a7afef9deecab323.md
[3] job-a85a0c0382d04970a0ea91ce0d78e7a9.md
[4] job-a57292b14b9743ba95f423424574a74b.md
[5] job-d99d05fe282741c9b3d276b666a59290.md
```
"""

# --- 旧版 LightRAG 格式 ---
LEGACY_RAW = """-----Entities(KG)-----

```json
[{"id": 1, "entity": "Noise", "type": "concept", "description": "x"}]
```

-----Relationships(KG)-----

```json
[]
```

-----Document Chunks(DC)-----

```json
[{"id": 1, "content": "# 岗位信息：测试岗\\n\\n## 基本信息\\n- 岗位ID：11111111-1111-1111-1111-111111111111\\n", "file_path": "job-11111111-1111-1111-1111-111111111111.md"}, {"id": 2, "content": "# 岗位信息：重复\\n\\n## 基本信息\\n- 岗位ID：11111111-1111-1111-1111-111111111111\\n", "file_path": "job-11111111-1111-1111-1111-111111111111.md"}]
```
"""


class TestExtractJobId:
    def test_from_content_uuid(self):
        assert extract_job_id(content="- 岗位ID：d99d05fe-2827-41c9-b3d2-76b666a59290") == "d99d05fe-2827-41c9-b3d2-76b666a59290"

    def test_from_content_hex32(self):
        assert extract_job_id(content="- 岗位ID：a85a0c0382d04970a0ea91ce0d78e7a9") == "a85a0c0382d04970a0ea91ce0d78e7a9"

    def test_from_file_path(self):
        assert extract_job_id(content="", file_path="job-d99d05fe282741c9b3d276b666a59290.md") == "d99d05fe282741c9b3d276b666a59290"


class TestParseReferenceList:
    def test_user_format(self):
        ref = parse_reference_document_list(USER_LIKE_RAW)
        assert ref["5"] == "d99d05fe282741c9b3d276b666a59290"
        assert ref["3"] == "a85a0c0382d04970a0ea91ce0d78e7a9"
        assert len(ref) == 4


class TestParseDocumentChunks:
    def test_user_jsonl_not_kg(self):
        chunks = parse_lightrag_document_chunks(USER_LIKE_RAW)
        assert len(chunks) == 4
        assert all("reference_id" in c for c in chunks)
        # 不应把 KG entity 块误解析为 document chunk
        assert not any("entity" in c for c in chunks)

    def test_legacy_json_array(self):
        chunks = parse_lightrag_document_chunks(LEGACY_RAW)
        assert len(chunks) == 2
        assert all(c.get("file_path", "").startswith("job-") for c in chunks)


class TestNormalizeUserScenario:
    def test_strips_kg_noise(self):
        material, jobs = normalize_lightrag_retrieval_context(USER_LIKE_RAW)
        assert "Knowledge Graph" not in material
        assert "Design Role" not in material
        assert "relationship noise" not in material

    def test_keeps_structured_jobs_with_ids(self):
        material, jobs = normalize_lightrag_retrieval_context(USER_LIKE_RAW)
        ids = {j["job_id"] for j in jobs}
        assert "d99d05fe282741c9b3d276b666a59290" in ids
        assert "a85a0c0382d04970a0ea91ce0d78e7a9" in ids

    def test_filters_short_fragments(self):
        _, jobs = normalize_lightrag_retrieval_context(USER_LIKE_RAW)
        ids = {j["job_id"] for j in jobs}
        # ref 1/4 为短片段，应被过滤
        assert "fbc79cd6f4be4b82a7afef9deecab323" not in ids
        assert "a57292b14b9743ba95f423424574a74b" not in ids

    def test_token_reduction(self):
        material, _ = normalize_lightrag_retrieval_context(USER_LIKE_RAW)
        assert len(material) < len(USER_LIKE_RAW) * 0.6

    def test_material_has_job_id_headers(self):
        material, _ = normalize_lightrag_retrieval_context(USER_LIKE_RAW)
        assert "### [1] job_id:" in material
        assert "岗位素材（已按 job_id 去重" in material


class TestLegacyFormat:
    def test_dedupe_same_job_id(self):
        material, jobs = normalize_lightrag_retrieval_context(LEGACY_RAW)
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "11111111-1111-1111-1111-111111111111"


class TestEdgeCases:
    def test_empty_input(self):
        material, jobs = normalize_lightrag_retrieval_context("")
        assert material == ""
        assert jobs == []

    def test_kg_only_returns_empty(self):
        kg_only = 'Knowledge Graph Data (Entity):\n```json\n{"entity": "X"}\n```\n'
        material, jobs = normalize_lightrag_retrieval_context(kg_only)
        assert material == ""
        assert jobs == []

    def test_same_job_id_keeps_longest(self):
        chunks = [
            {"content": "# 岗位信息：A\n- 岗位ID：aaa-bbbb-cccc-dddd-eeeeeeeeeeee\n短", "file_path": "job-aaa.md"},
            {"content": "# 岗位信息：A\n- 岗位ID：aaa-bbbb-cccc-dddd-eeeeeeeeeeee\n" + "长" * 200, "file_path": "job-aaa.md"},
        ]
        out = dedupe_job_chunks(chunks)
        assert len(out) == 1
        assert len(out[0]["content"]) > 100
