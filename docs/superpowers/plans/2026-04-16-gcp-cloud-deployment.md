# PillCare GCP Cloud Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy PillCare to GCP Cloud Run with Gemini LLM, GCS data loading, IAP auth, and GitHub Actions CI/CD.

**Architecture:** Replace Claude with Gemini 2.5 Flash via structured output (Pydantic JSON schema), load SQLite DB from GCS at startup with integrity verification, containerize with multi-stage uv Docker build, deploy to Cloud Run with IAP, automate with GitHub Actions + Workload Identity Federation.

**Tech Stack:** langchain-google-genai (ChatGoogleGenerativeAI), google-cloud-storage, Cloud Run, Artifact Registry, IAP, GitHub Actions, Docker

**Pre-requisite:** The `feat/medication-guidance-pipeline-v2` branch must be merged to `main` before starting. The plan assumes all 14 existing source files and 57 tests are on the working branch.

---

## File Structure

**New files:**
- `src/pillcare/gcs_loader.py` — GCS download with SHA256 + SQLite integrity check
- `src/pillcare/llm_factory.py` — LLM provider factory (Gemini/Claude, env-driven)
- `src/pillcare/logging_config.py` — JSON structured logging for Cloud Logging
- `tests/test_gcs_loader.py` — GCS loader tests (mocked)
- `tests/test_llm_factory.py` — LLM factory tests
- `Dockerfile` — Multi-stage uv build
- `.dockerignore` — Exclude data/, tests/, docs/, .git/
- `.github/workflows/ci-cd.yml` — Lint → test → build → deploy
- `.streamlit/config.toml` — Headless/WebSocket settings for Cloud Run

**Modified files:**
- `pyproject.toml` — Add langchain-google-genai, google-cloud-storage, ruff; move streamlit to prod deps
- `src/pillcare/schemas.py` — Add DrugSectionOutput, DrugGuidanceOutput for structured LLM output
- `src/pillcare/prompts.py` — Update system prompt for structured output (remove inline tag instructions)
- `src/pillcare/pipeline.py` — Replace regex parsing with structured output; remove _parse_drug_guidance, _detect_source_tier
- `src/pillcare/guardrails.py` — Simplify verify_source_tags for structured output
- `src/pillcare/app.py` — GCS DB loading, LLM factory, env config, UI disclaimer
- `tests/test_pipeline.py` — Update mocks for structured output
- `tests/test_guardrails.py` — Update for simplified source tag check

---

### Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml dependencies**

```toml
[project]
name = "pillcare"
version = "0.2.0"
description = "필케어 (PillCare) — 복약 정보 안내 파이프라인 POC"
readme = "README.md"
authors = [
    { name = "jawsbaek", email = "bshjaws1@gmail.com" }
]
requires-python = ">=3.11"
dependencies = [
    "anthropic==0.95.0",
    "google-cloud-storage>=2.18.0,<3.0.0",
    "langchain-anthropic==1.4.0",
    "langchain-core==1.2.30",
    "langchain-google-genai>=4.0.0,<5.0.0",
    "langgraph==1.1.6",
    "msoffcrypto-tool==6.0.0",
    "openpyxl==3.1.5",
    "pydantic==2.13.1",
    "python-dotenv==1.2.2",
    "rapidfuzz==3.14.5",
    "streamlit==1.45.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "pytest==9.0.3",
    "ruff>=0.9.0",
]
```

Key changes:
- Added `google-cloud-storage>=2.18.0,<3.0.0`
- Added `langchain-google-genai>=4.0.0,<5.0.0`
- Moved `streamlit` from dev to prod deps, pinned to `1.45.1` (WebSocket IAP compatibility)
- Added `ruff` to dev deps for linting in CI
- Bumped version to `0.2.0`

- [ ] **Step 2: Install and lock dependencies**

Run: `uv sync`
Expected: All dependencies install, `uv.lock` updated without conflicts.

- [ ] **Step 3: Verify existing tests still pass**

Run: `uv run pytest --tb=short`
Expected: All 57 tests pass (no regressions from dependency changes).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add langchain-google-genai, google-cloud-storage, ruff deps"
```

---

### Task 2: Structured Output Pydantic Models

**Files:**
- Modify: `src/pillcare/schemas.py`
- Test: `tests/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_schemas.py`:

```python
from pillcare.schemas import (
    DrugSectionOutput, DrugGuidanceOutput,
    DrugGuidance, GuidanceSection, SourceTier,
)


def test_drug_guidance_output_to_drug_guidance():
    """DrugGuidanceOutput converts to DrugGuidance with correct types."""
    output = DrugGuidanceOutput(
        drug_name="리도펜연질캡슐",
        sections=[
            DrugSectionOutput(
                section_name="명칭",
                content="리도펜연질캡슐 (이부프로펜 200mg)",
                source_tier="T1:허가정보",
            ),
            DrugSectionOutput(
                section_name="효능효과",
                content="감기 발열 통증에 사용합니다.",
                source_tier="T1:e약은요",
            ),
            DrugSectionOutput(
                section_name="투여의의",
                content="NSAIDs 계열 소염진통제입니다.",
                source_tier="T4:AI",
            ),
        ],
    )
    guidance = output.to_drug_guidance()
    assert isinstance(guidance, DrugGuidance)
    assert guidance.drug_name == "리도펜연질캡슐"
    assert "명칭" in guidance.sections
    assert "효능효과" in guidance.sections
    assert "투여의의" in guidance.sections
    assert guidance.sections["명칭"].source_tier == SourceTier.T1_PERMIT
    assert guidance.sections["효능효과"].source_tier == SourceTier.T1_EASY
    assert guidance.sections["투여의의"].source_tier == SourceTier.T4_AI


def test_drug_guidance_output_invalid_section_name():
    """DrugGuidanceOutput rejects invalid section names."""
    import pytest
    with pytest.raises(Exception):
        DrugSectionOutput(
            section_name="존재하지않는섹션",
            content="test",
            source_tier="T1:허가정보",
        )


def test_drug_guidance_output_invalid_source_tier():
    """DrugGuidanceOutput rejects invalid source tiers."""
    import pytest
    with pytest.raises(Exception):
        DrugSectionOutput(
            section_name="명칭",
            content="test",
            source_tier="T9:없는소스",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas.py::test_drug_guidance_output_to_drug_guidance -v`
Expected: FAIL with `ImportError: cannot import name 'DrugSectionOutput'`

- [ ] **Step 3: Add DrugSectionOutput and DrugGuidanceOutput to schemas.py**

Add after the `DrugGuidance` class (before `DurWarning`):

```python
from typing import Literal


SECTION_NAMES = Literal[
    "명칭", "성상", "효능효과", "투여의의", "용법용량",
    "저장방법", "주의사항", "상호작용", "투여종료후", "기타",
]

SOURCE_TIER_LABELS = Literal["T1:허가정보", "T1:e약은요", "T1:DUR", "T4:AI"]

_TIER_LABEL_MAP: dict[str, SourceTier] = {
    "T1:허가정보": SourceTier.T1_PERMIT,
    "T1:e약은요": SourceTier.T1_EASY,
    "T1:DUR": SourceTier.T1_DUR,
    "T4:AI": SourceTier.T4_AI,
}


class DrugSectionOutput(BaseModel):
    """LLM structured output schema for a single drug section."""
    section_name: SECTION_NAMES
    content: str
    source_tier: SOURCE_TIER_LABELS


class DrugGuidanceOutput(BaseModel):
    """LLM structured output schema for complete drug guidance."""
    drug_name: str
    sections: list[DrugSectionOutput]

    def to_drug_guidance(self) -> DrugGuidance:
        """Convert LLM structured output to internal DrugGuidance model."""
        sections_dict: dict[str, GuidanceSection] = {}
        for s in self.sections:
            tier = _TIER_LABEL_MAP[s.source_tier]
            sections_dict[s.section_name] = GuidanceSection(
                title=s.section_name,
                content=s.content,
                source_tier=tier,
            )
        return DrugGuidance(drug_name=self.drug_name, sections=sections_dict)
```

Note: `Literal` import needs to be added at the top of the file: `from typing import Literal`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: All schema tests pass including the 3 new ones.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/schemas.py tests/test_schemas.py
git commit -m "feat: add DrugSectionOutput and DrugGuidanceOutput for structured LLM output"
```

---

### Task 3: GCS Database Loader

**Files:**
- Create: `src/pillcare/gcs_loader.py`
- Create: `tests/test_gcs_loader.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_gcs_loader.py`:

```python
"""Tests for GCS database loader with mocked GCS client."""

import hashlib
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pillcare.gcs_loader import download_db, compute_sha256


@pytest.fixture
def valid_db(tmp_path: Path) -> Path:
    """Create a valid SQLite DB for testing."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO test VALUES (1)")
    conn.commit()
    conn.close()
    return db_path


def test_compute_sha256(valid_db: Path):
    """compute_sha256 returns correct hash for a file."""
    sha = compute_sha256(str(valid_db))
    assert len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)


@patch("pillcare.gcs_loader.storage")
def test_download_db_success(mock_storage, valid_db: Path, tmp_path: Path):
    """download_db downloads and verifies a valid DB."""
    local_path = str(tmp_path / "downloaded.db")
    expected_sha = compute_sha256(str(valid_db))

    mock_client = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    # Simulate download by copying the valid DB
    def fake_download(path):
        import shutil
        shutil.copy2(str(valid_db), path)

    mock_blob.download_to_filename.side_effect = fake_download

    result = download_db("test-bucket", "test.db", local_path, expected_sha256=expected_sha)
    assert result == local_path
    assert Path(local_path).exists()


@patch("pillcare.gcs_loader.storage")
def test_download_db_sha_mismatch(mock_storage, valid_db: Path, tmp_path: Path):
    """download_db raises on SHA256 mismatch."""
    local_path = str(tmp_path / "downloaded.db")

    mock_client = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    def fake_download(path):
        import shutil
        shutil.copy2(str(valid_db), path)

    mock_blob.download_to_filename.side_effect = fake_download

    with pytest.raises(RuntimeError, match="DB integrity.*SHA256"):
        download_db("test-bucket", "test.db", local_path, expected_sha256="wrong_hash")


@patch("pillcare.gcs_loader.storage")
def test_download_db_no_sha_check(mock_storage, valid_db: Path, tmp_path: Path):
    """download_db skips SHA check when expected_sha256 is None."""
    local_path = str(tmp_path / "downloaded.db")

    mock_client = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    def fake_download(path):
        import shutil
        shutil.copy2(str(valid_db), path)

    mock_blob.download_to_filename.side_effect = fake_download

    result = download_db("test-bucket", "test.db", local_path)
    assert result == local_path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_gcs_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pillcare.gcs_loader'`

- [ ] **Step 3: Implement gcs_loader.py**

Create `src/pillcare/gcs_loader.py`:

```python
"""Download SQLite DB from GCS with integrity verification."""

import hashlib
import sqlite3

from google.cloud import storage


def compute_sha256(file_path: str) -> str:
    """Compute SHA256 hex digest of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def download_db(
    bucket_name: str,
    blob_name: str,
    local_path: str,
    expected_sha256: str | None = None,
) -> str:
    """Download DB from GCS, verify integrity, return local path.

    Args:
        bucket_name: GCS bucket name.
        blob_name: GCS blob name (e.g. "pillcare.db").
        local_path: Local file path to save the DB.
        expected_sha256: Expected SHA256 hash. Skips check if None.

    Returns:
        The local_path string.

    Raises:
        RuntimeError: If SHA256 or SQLite integrity check fails.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)

    if expected_sha256:
        actual = compute_sha256(local_path)
        if actual != expected_sha256:
            raise RuntimeError(
                f"DB integrity failed: SHA256 expected {expected_sha256}, got {actual}"
            )

    conn = sqlite3.connect(local_path)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if result[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {result[0]}")
    finally:
        conn.close()

    return local_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_gcs_loader.py -v`
Expected: All 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/gcs_loader.py tests/test_gcs_loader.py
git commit -m "feat: add GCS database loader with SHA256 + SQLite integrity verification"
```

---

### Task 4: LLM Factory

**Files:**
- Create: `src/pillcare/llm_factory.py`
- Create: `tests/test_llm_factory.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm_factory.py`:

```python
"""Tests for LLM factory."""

import os
from unittest.mock import patch, MagicMock

import pytest

from pillcare.llm_factory import create_llm


@patch.dict(os.environ, {
    "LLM_PROVIDER": "gemini",
    "GCP_PROJECT_ID": "test-project",
    "GCP_REGION": "asia-northeast3",
})
@patch("pillcare.llm_factory.ChatGoogleGenerativeAI")
def test_create_gemini_llm(mock_chat_cls):
    """Factory creates Gemini LLM with correct params."""
    mock_chat_cls.return_value = MagicMock()
    llm = create_llm()
    mock_chat_cls.assert_called_once()
    call_kwargs = mock_chat_cls.call_args[1]
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert call_kwargs["vertexai"] is True
    assert call_kwargs["project"] == "test-project"
    assert call_kwargs["location"] == "asia-northeast3"
    assert call_kwargs["max_output_tokens"] == 5000


@patch.dict(os.environ, {"LLM_PROVIDER": "claude", "ANTHROPIC_API_KEY": "sk-test"})
@patch("pillcare.llm_factory.ChatAnthropic")
def test_create_claude_llm(mock_chat_cls):
    """Factory creates Claude LLM with correct params."""
    mock_chat_cls.return_value = MagicMock()
    llm = create_llm()
    mock_chat_cls.assert_called_once()
    call_kwargs = mock_chat_cls.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 4096


@patch.dict(os.environ, {}, clear=True)
@patch("pillcare.llm_factory.ChatGoogleGenerativeAI")
def test_defaults_to_gemini(mock_chat_cls):
    """Factory defaults to Gemini when LLM_PROVIDER is not set."""
    mock_chat_cls.return_value = MagicMock()
    create_llm()
    mock_chat_cls.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_llm_factory.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pillcare.llm_factory'`

- [ ] **Step 3: Implement llm_factory.py**

Create `src/pillcare/llm_factory.py`:

```python
"""LLM provider factory — creates Gemini or Claude based on environment."""

import os

from langchain_google_genai import ChatGoogleGenerativeAI


def create_llm():
    """Create LLM instance based on LLM_PROVIDER env var.

    Defaults to Gemini 2.5 Flash on Vertex AI.
    Set LLM_PROVIDER=claude to use Claude Sonnet (requires ANTHROPIC_API_KEY).
    """
    provider = os.environ.get("LLM_PROVIDER", "gemini")

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            max_tokens=4096,
        )

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        vertexai=True,
        project=os.environ.get("GCP_PROJECT_ID"),
        location=os.environ.get("GCP_REGION", "asia-northeast3"),
        max_output_tokens=5000,
        safety_settings={
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
            "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
        },
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_llm_factory.py -v`
Expected: All 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/llm_factory.py tests/test_llm_factory.py
git commit -m "feat: add LLM factory supporting Gemini (default) and Claude"
```

---

### Task 5: Update Prompts for Structured Output

**Files:**
- Modify: `src/pillcare/prompts.py`

- [ ] **Step 1: Update SYSTEM_PROMPT**

Replace the entire `SYSTEM_PROMPT` in `src/pillcare/prompts.py`:

```python
SYSTEM_PROMPT = """당신은 복약 정보 안내 AI입니다. 아래 도구로 제공된 의약품 정보를 바탕으로 복약 정보 안내문을 생성합니다.

## 역할 경계
- 절대 금지: 진단, 처방, 용량 변경 권고, 투약 중단 판단
- 모든 경고의 결론: "의사 또는 약사와 상담하십시오"
- 용어: "복약지도" 대신 "복약 정보 안내"를 사용

## 출처 분류 규칙 (source_tier)
각 섹션의 source_tier 필드에 정보 출처를 정확히 분류하십시오:
- "T1:허가정보": 허가사항(효능효과, 용법용량, 주의사항)에서 직접 인용한 내용
- "T1:e약은요": e약은요 환자용 텍스트에서 인용한 내용
- "T1:DUR": DUR 병용금기 데이터에서 인용한 내용
- "T4:AI": 위 출처에 없어 AI가 일반 지식으로 작성한 내용
  - T4 섹션은 반드시 다음 문구를 포함: "※ AI가 생성한 일반 정보입니다. 정확한 내용은 의사 또는 약사와 상담하십시오."

## 복약 정보 체크리스트 (10개 항목)
각 항목을 sections 배열에 포함하십시오:
1) 명칭 (source_tier: T1:허가정보) — 제품명, 성분명, 제조사, 제형, 함량
2) 성상 (source_tier: T1:허가정보) — 외형 설명
3) 효능효과 (source_tier: T1:허가정보 또는 T1:e약은요) — 허가사항 기반
4) 투여의의 (source_tier: T4:AI) — 약이 필요한 이유, 효능효과 + ATC 분류로 맥락 보충
5) 용법용량 (source_tier: T1:허가정보 또는 T1:e약은요) — 사용시간, 횟수, 용량
6) 저장방법 (source_tier: T1:허가정보) — 보관조건, 유효기간
7) 주의사항 (source_tier: T1:허가정보) — 흔한 이상반응 + 중대 이상반응. 반드시 "의사 또는 약사와 상담하십시오"로 마무리
8) 상호작용 (source_tier: T1:DUR 또는 T1:허가정보) — 병용금기 + 상호작용 섹션. 반드시 "의사 또는 약사와 상담하십시오"로 마무리
9) 투여종료후 (source_tier: T4:AI) — 해당 시. 반드시 "의사 또는 약사와 상담하십시오"로 마무리
10) 기타 (source_tier: T1:허가정보 또는 T4:AI) — 복용 누락, 일반 주의 등

## 금칙 어휘
절대 사용하지 말 것: 진단합니다, 처방합니다, 투약판단, 용량을 조절, 복용을 중단하세요, 복약지도

## DUR 병용금기
DUR 금기 정보가 있는 경우, 상호작용 섹션에 반드시 포함하십시오.
다기관 처방 교차 금기는 별도 강조하십시오."""
```

- [ ] **Step 2: Verify no tests are broken**

Run: `uv run pytest --tb=short`
Expected: All existing tests pass. (Prompt content is not directly tested by existing test assertions.)

- [ ] **Step 3: Commit**

```bash
git add src/pillcare/prompts.py
git commit -m "refactor: update system prompt for structured output format"
```

---

### Task 6: Pipeline Refactor — Structured Output

**Files:**
- Modify: `src/pillcare/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Update test mocks for structured output**

Replace test mocks and update imports in `tests/test_pipeline.py`. The key changes:
- Remove import of `_parse_drug_guidance` (it will be deleted)
- Mock LLM to return through `with_structured_output` chain
- Replace `test_parse_drug_guidance` with `test_structured_output_conversion`

Replace the full file `tests/test_pipeline.py`:

```python
"""Tests for LangGraph pipeline with mocked LLM."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pillcare.db_builder import build_db
from pillcare.schemas import DrugGuidanceOutput, DrugSectionOutput
from pillcare.xml_parser import parse_nb_doc
from pillcare.pipeline import build_pipeline, run_pipeline, GraphState
from pillcare.tools import make_match_node, make_dur_node, make_collect_node


@pytest.fixture
def full_db(tmp_path: Path, fixtures_dir: Path) -> Path:
    with open(fixtures_dir / "small_permit.json", encoding="utf-8") as f:
        permit = json.load(f)
    with open(fixtures_dir / "small_easy.json", encoding="utf-8") as f:
        easy = json.load(f)
    db_path = build_db(tmp_path / "test.db", permit_data=permit, easy_data=easy)
    conn = sqlite3.connect(db_path)
    for item in permit:
        nb = item.get("NB_DOC_DATA", "")
        sections = parse_nb_doc(nb)
        for s in sections:
            conn.execute(
                "INSERT OR REPLACE INTO drug_sections VALUES (?,?,?,?,?)",
                (item["ITEM_SEQ"], s.section_type, s.section_title, s.section_text, s.section_order),
            )
    # Add a DUR pair for ibuprofen x chlorpheniramine
    conn.execute(
        "INSERT INTO dur_pairs VALUES (?,?,?,?,?,?)",
        ("M040702", "이부프로펜", "M175201", "클로르페니라민말레산염", "중추신경 억제 증강", "20200101"),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_records():
    return [
        {"drug_name": "리도펜연질캡슐(이부프로펜)", "drug_code": "649301290", "department": "가정의학과"},
        {"drug_name": "코대원정", "drug_code": None, "department": "내과"},
    ]


@pytest.fixture
def mock_guidance_output():
    """Standard DrugGuidanceOutput for mocking structured LLM responses."""
    return DrugGuidanceOutput(
        drug_name="리도펜연질캡슐",
        sections=[
            DrugSectionOutput(section_name="명칭", content="리도펜연질캡슐 (이부프로펜 200mg)", source_tier="T1:허가정보"),
            DrugSectionOutput(section_name="효능효과", content="감기 발열 통증에 사용합니다.", source_tier="T1:e약은요"),
            DrugSectionOutput(section_name="주의사항", content="위장출혈 주의. 의사 또는 약사와 상담하십시오.", source_tier="T1:허가정보"),
            DrugSectionOutput(section_name="상호작용", content="이부프로펜과 클로르페니라민 병용 시 중추신경 억제 증강. 의사 또는 약사와 상담하십시오.", source_tier="T1:DUR"),
        ],
    )


def _make_mock_llm(guidance_output: DrugGuidanceOutput):
    """Create a mock LLM that supports with_structured_output."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = guidance_output
    return mock_llm


def test_deterministic_nodes(full_db, sample_records):
    """Test match -> DUR -> collect chain without LLM."""
    state = {"raw_records": sample_records, "errors": []}

    result = make_match_node(str(full_db))(state)
    assert len(result["matched_drugs"]) == 2
    state.update(result)

    result = make_dur_node(str(full_db))(state)
    assert len(result["dur_alerts"]) >= 1
    state.update(result)

    result = make_collect_node(str(full_db))(state)
    assert len(result["drug_infos"]) == 2


def test_dur_cross_clinic(full_db, sample_records):
    """DUR alerts between different departments are flagged as cross-clinic."""
    state = {"raw_records": sample_records, "errors": []}
    state.update(make_match_node(str(full_db))(state))
    result = make_dur_node(str(full_db))(state)
    cross = [a for a in result["dur_alerts"] if a["cross_clinic"]]
    assert len(cross) >= 1


def test_build_pipeline_compiles(full_db, mock_guidance_output):
    """Pipeline compiles without error."""
    mock_llm = _make_mock_llm(mock_guidance_output)
    graph = build_pipeline(db_path=str(full_db), llm=mock_llm)
    assert graph is not None


def test_structured_output_conversion(mock_guidance_output):
    """DrugGuidanceOutput converts to DrugGuidance with correct sections."""
    guidance = mock_guidance_output.to_drug_guidance()
    assert "명칭" in guidance.sections
    assert "효능효과" in guidance.sections
    assert "주의사항" in guidance.sections
    assert guidance.sections["효능효과"].source_tier.value == "T1:e약은요"


def test_generate_with_mock_llm(full_db, sample_records, mock_guidance_output):
    """Generate node produces guidance with mocked structured LLM response."""
    mock_llm = _make_mock_llm(mock_guidance_output)

    from pillcare.pipeline import _make_generate_node

    state = {"raw_records": sample_records, "errors": [], "_retry_count": 0}
    state.update(make_match_node(str(full_db))(state))
    state.update(make_dur_node(str(full_db))(state))
    state.update(make_collect_node(str(full_db))(state))

    gen_node = _make_generate_node(mock_llm)
    result = gen_node(state)

    assert result["guidance_result"] is not None
    assert mock_llm.with_structured_output.called


def test_full_pipeline_with_mock_llm(full_db, sample_records, mock_guidance_output):
    """Full pipeline runs end-to-end with mocked structured LLM."""
    mock_llm = _make_mock_llm(mock_guidance_output)

    result = run_pipeline(
        db_path=str(full_db),
        llm=mock_llm,
        records=sample_records,
        profile_id="test-user",
    )

    assert result["guidance_result"] is not None
    assert result["profile_id"] == "test-user"
    assert len(result["matched_drugs"]) == 2
    assert len(result["dur_alerts"]) >= 1


def test_should_retry_on_critical():
    """Retry is triggered by [CRITICAL] errors and capped at 2."""
    from pillcare.pipeline import _should_retry

    assert _should_retry({"_last_verify_errors": [], "_retry_count": 0}) == "done"
    assert _should_retry({"_last_verify_errors": ["[CRITICAL] T4 비율 초과"], "_retry_count": 0}) == "generate"
    assert _should_retry({"_last_verify_errors": ["[CRITICAL] T4 비율 초과"], "_retry_count": 1}) == "generate"
    assert _should_retry({"_last_verify_errors": ["[CRITICAL] T4 비율 초과"], "_retry_count": 2}) == "done"
    assert _should_retry({"_last_verify_errors": ["출처 태그 누락: A / 명칭"], "_retry_count": 0}) == "done"
```

- [ ] **Step 2: Run tests to see them fail**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL because `_parse_drug_guidance` is still imported from old test, and pipeline still uses regex.

- [ ] **Step 3: Refactor pipeline.py for structured output**

Replace the entire `src/pillcare/pipeline.py`:

```python
"""LangGraph StateGraph pipeline for medication guidance generation."""

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from pillcare.prompts import DRUG_GUIDANCE_TEMPLATE, SYSTEM_PROMPT
from pillcare.schemas import (
    DrugGuidance, DrugGuidanceOutput, DurWarning, GuidanceResult, GuidanceSection,
    SourceTier,
)
from pillcare.tools import make_collect_node, make_dur_node, make_match_node


# --- State schemas ---
class PublicState(TypedDict, total=False):
    profile_id: str
    raw_records: list[dict]
    matched_drugs: list[dict]
    dur_alerts: list[dict]
    drug_infos: list[dict]
    guidance_result: dict | None
    errors: Annotated[list[str], operator.add]


class GraphState(PublicState, total=False):
    _retry_count: int
    _last_verify_errors: list[str]


def _make_generate_node(llm: Any):
    """Factory: creates generate node with LLM bound via closure."""
    def generate_node(state: dict) -> dict:
        from pillcare.guardrails import filter_banned_words

        drug_infos = state.get("drug_infos", [])
        dur_alerts = state.get("dur_alerts", [])

        drug_guidances = []
        dur_warnings = []
        warning_labels = []
        generation_errors: list[str] = []

        structured_llm = llm.with_structured_output(DrugGuidanceOutput, method="json_schema")

        # Extract warning labels from data -- deterministic
        for info in drug_infos:
            sections = info.get("sections", {})
            if "경고" in sections:
                warning_labels.append(f"{info.get('item_name', '')}: {sections['경고'][:100]}")
            easy = info.get("easy") or {}
            if easy.get("atpn_warn_qesitm"):
                warning_labels.append(f"{info.get('item_name', '')}: {easy['atpn_warn_qesitm'][:100]}")

        # Build DUR warnings
        for alert in dur_alerts:
            dur_warnings.append(DurWarning(
                drug_1=alert["drug_name_1"], drug_2=alert["drug_name_2"],
                reason=alert["reason"], cross_clinic=alert["cross_clinic"],
            ))
            cross = " [다기관]" if alert["cross_clinic"] else ""
            warning_labels.append(
                f"[병용금기] {alert['drug_name_1']} x {alert['drug_name_2']}: {alert['reason']}{cross}"
            )

        # Format DUR text for prompts
        dur_text = ""
        if dur_alerts:
            lines = []
            for a in dur_alerts:
                cross = " [다기관 교차 처방]" if a["cross_clinic"] else ""
                lines.append(f"- {a['drug_name_1']} x {a['drug_name_2']}: {a['reason']}{cross}")
            dur_text = "\n".join(lines)

        # Generate per-drug guidance via structured output
        summary_points = []
        for info in drug_infos:
            sections_text = ""
            if info.get("sections"):
                for stype, stext in info["sections"].items():
                    sections_text += f"\n### {stype}\n{stext}\n"

            easy_text = ""
            if info.get("easy"):
                for key, val in info["easy"].items():
                    if val:
                        easy_text += f"{key}: {val}\n"

            prompt = DRUG_GUIDANCE_TEMPLATE.format(
                item_name=info.get("item_name", ""),
                main_item_ingr=info.get("main_item_ingr", ""),
                main_ingr_eng=info.get("main_ingr_eng", ""),
                entp_name=info.get("entp_name", ""),
                atc_code=info.get("atc_code", ""),
                etc_otc_code=info.get("etc_otc_code", ""),
                chart=info.get("chart", ""),
                total_content=info.get("total_content", ""),
                storage_method=info.get("storage_method", ""),
                valid_term=info.get("valid_term", ""),
                ee_text=info.get("ee_doc_data", "") or "(없음)",
                ud_text=info.get("ud_doc_data", "") or "(없음)",
                nb_sections=sections_text or "(없음)",
                easy_text=easy_text or "(없음)",
                dur_alerts=dur_text or "(없음)",
            )

            try:
                messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
                output: DrugGuidanceOutput = structured_llm.invoke(messages)
                guidance = output.to_drug_guidance()
            except Exception as e:
                # Fallback: create minimal guidance on LLM failure
                guidance = DrugGuidance(
                    drug_name=info.get("item_name", ""),
                    sections={
                        "명칭": GuidanceSection(
                            title="명칭",
                            content=info.get("item_name", ""),
                            source_tier=SourceTier.T1_PERMIT,
                        ),
                    },
                )
                generation_errors.append(f"[ERROR] LLM 호출 실패: {info.get('item_name', '')} — {e}")

            # Apply banned word filter
            for section in guidance.sections.values():
                section.content = filter_banned_words(section.content)

            drug_guidances.append(guidance)

            for a in dur_alerts:
                if a["drug_name_1"] == info.get("item_name") or a["drug_name_2"] == info.get("item_name"):
                    summary_points.append(
                        f"{a['drug_name_1']}과 {a['drug_name_2']}: {a['reason']}"
                    )

        result = GuidanceResult(
            drug_guidances=drug_guidances,
            dur_warnings=dur_warnings,
            summary=list(set(summary_points)),
            warning_labels=warning_labels,
        )
        return {"guidance_result": result.model_dump(), "errors": generation_errors}

    return generate_node


def _verify_node(state: dict) -> dict:
    """Post-verification node."""
    from pillcare.guardrails import post_verify

    result_data = state.get("guidance_result")
    retry_count = state.get("_retry_count", 0)

    if not result_data:
        return {"errors": ["생성 결과 없음"], "_retry_count": retry_count + 1}

    result = GuidanceResult(**result_data) if isinstance(result_data, dict) else result_data
    dur_alerts = state.get("dur_alerts", [])

    new_errors = post_verify(result, dur_alerts)
    return {
        "errors": new_errors,
        "_last_verify_errors": new_errors,
        "_retry_count": retry_count + 1,
    }


def _should_retry(state: dict) -> str:
    errors = state.get("_last_verify_errors", [])
    critical = [e for e in errors if e.startswith("[CRITICAL]")]
    retry_count = state.get("_retry_count", 0)
    if critical and retry_count < 2:
        return "generate"
    return "done"


def build_pipeline(db_path: str, llm: Any):
    """Build the LangGraph StateGraph."""
    builder = StateGraph(GraphState, input_schema=PublicState, output_schema=PublicState)

    builder.add_node("match_drugs", make_match_node(db_path))
    builder.add_node("check_dur", make_dur_node(db_path))
    builder.add_node("collect_info", make_collect_node(db_path))
    builder.add_node("generate", _make_generate_node(llm))
    builder.add_node("verify", _verify_node)

    builder.add_edge(START, "match_drugs")
    builder.add_edge("match_drugs", "check_dur")
    builder.add_edge("check_dur", "collect_info")
    builder.add_edge("collect_info", "generate")
    builder.add_edge("generate", "verify")
    builder.add_conditional_edges("verify", _should_retry, {"generate": "generate", "done": END})

    return builder.compile()


def run_pipeline(db_path: str, llm: Any, records: list[dict], profile_id: str = "default") -> dict:
    """Run the full pipeline."""
    graph = build_pipeline(db_path, llm)
    initial_state: PublicState = {
        "profile_id": profile_id,
        "raw_records": records,
        "matched_drugs": [],
        "dur_alerts": [],
        "drug_infos": [],
        "guidance_result": None,
        "errors": [],
    }
    return graph.invoke(initial_state)
```

- [ ] **Step 4: Run pipeline tests**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: All 8 tests pass.

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest --tb=short`
Expected: All tests pass (no regressions).

- [ ] **Step 6: Commit**

```bash
git add src/pillcare/pipeline.py tests/test_pipeline.py
git commit -m "refactor: replace regex parsing with structured output in pipeline"
```

---

### Task 7: Update Guardrails for Structured Output

**Files:**
- Modify: `src/pillcare/guardrails.py`
- Modify: `tests/test_guardrails.py`

- [ ] **Step 1: Update verify_source_tags test**

In `tests/test_guardrails.py`, update the two source tag tests:

```python
def test_verify_source_tags_detects_all_t4():
    """verify_source_tags flags when all sections are T4."""
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections={
            "명칭": GuidanceSection(title="명칭", content="리도펜연질캡슐입니다.", source_tier=SourceTier.T4_AI),
            "효능효과": GuidanceSection(title="효능효과", content="감기에 사용합니다.", source_tier=SourceTier.T4_AI),
        })],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_source_tags(result)
    assert len(errors) >= 1


def test_verify_source_tags_passes_with_t1():
    """verify_source_tags passes when at least one section has T1 source."""
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections={
            "명칭": GuidanceSection(title="명칭", content="리도펜연질캡슐", source_tier=SourceTier.T1_PERMIT),
            "투여의의": GuidanceSection(title="투여의의", content="소염진통제입니다.", source_tier=SourceTier.T4_AI),
        })],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    assert verify_source_tags(result) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_guardrails.py::test_verify_source_tags_detects_all_t4 -v`
Expected: FAIL (old verify_source_tags checks for regex in content, not source_tier field).

- [ ] **Step 3: Update guardrails.py**

Replace the entire `src/pillcare/guardrails.py`:

```python
"""Enhanced post-verification guardrails."""

from pillcare.prompts import BANNED_WORDS
from pillcare.schemas import GuidanceResult, SourceTier

_WARNING_SECTIONS = {"주의사항", "상호작용", "투여종료후"}
_CLOSING_PHRASE = "의사 또는 약사와 상담하십시오"


def verify_dur_coverage(result: GuidanceResult, dur_alerts: list[dict]) -> list[dict]:
    """Structured matching: check dur_warnings contains all alert pairs."""
    warned_pairs = set()
    for w in result.dur_warnings:
        warned_pairs.add((w.drug_1, w.drug_2))
        warned_pairs.add((w.drug_2, w.drug_1))
    missing = []
    for alert in dur_alerts:
        if (alert["drug_name_1"], alert["drug_name_2"]) not in warned_pairs:
            missing.append(alert)
    return missing


def filter_banned_words(text: str) -> str:
    """Remove banned words from text and clean up extra whitespace."""
    result = text
    for word in BANNED_WORDS:
        result = result.replace(word, "")
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip()


def verify_source_tags(result: GuidanceResult) -> list[str]:
    """Check that each drug has at least one T1-sourced section."""
    errors = []
    for dg in result.drug_guidances:
        has_t1 = any(
            s.source_tier in (SourceTier.T1_PERMIT, SourceTier.T1_EASY, SourceTier.T1_DUR)
            for s in dg.sections.values()
        )
        if not has_t1:
            errors.append(f"T1 출처 없음: {dg.drug_name} (모든 섹션이 AI 생성)")
    return errors


def verify_t4_ratio(result: GuidanceResult, max_ratio: float = 0.3) -> list[str]:
    """Verify that the ratio of T4 (AI-generated) sections is within limits."""
    ratio = result.t4_ratio()
    if ratio > max_ratio:
        return [f"[CRITICAL] T4 비율 초과: {ratio:.1%} (한도: {max_ratio:.0%})"]
    return []


def verify_closing_phrase(result: GuidanceResult) -> list[str]:
    """Ensure warning sections end with the mandatory closing phrase."""
    errors = []
    for dg in result.drug_guidances:
        for name, section in dg.sections.items():
            if name in _WARNING_SECTIONS and _CLOSING_PHRASE not in section.content:
                errors.append(f"필수 종결 문구 누락: {dg.drug_name} / {name}")
    return errors


def post_verify(result: GuidanceResult, dur_alerts: list[dict]) -> list[str]:
    """Run all post-verification guardrail checks and return collected errors."""
    errors = []
    missing = verify_dur_coverage(result, dur_alerts)
    for m in missing:
        errors.append(f"[ERROR] DUR 누락: {m['drug_name_1']} × {m['drug_name_2']} (deterministic 구성 — 재시도 불가, 코드 버그 확인 필요)")
    errors.extend(verify_source_tags(result))
    errors.extend(verify_t4_ratio(result))
    errors.extend(verify_closing_phrase(result))
    return errors
```

- [ ] **Step 4: Run guardrail tests**

Run: `uv run pytest tests/test_guardrails.py -v`
Expected: All tests pass.

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest --tb=short`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/pillcare/guardrails.py tests/test_guardrails.py
git commit -m "refactor: update guardrails for structured output (field-based source tier check)"
```

---

### Task 8: App Refactor — Gemini + GCS + Config + Disclaimer

**Files:**
- Modify: `src/pillcare/app.py`

- [ ] **Step 1: Replace app.py**

Replace the entire `src/pillcare/app.py`:

```python
"""Streamlit UI for PillCare medication guidance POC."""

import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pillcare.llm_factory import create_llm
from pillcare.pipeline import build_pipeline
from pillcare.schemas import GuidanceResult

_DISCLAIMER = (
    "이 서비스는 의료 행위가 아니며, 전문 의료인의 상담을 대체하지 않습니다. "
    "제공되는 정보는 공개된 식약처 데이터를 기반으로 하며, "
    "개인의 건강 상태에 따라 다를 수 있습니다."
)


def _get_db_path() -> str:
    """Resolve DB path: GCS download or local file."""
    gcs_bucket = os.environ.get("GCS_BUCKET")
    if gcs_bucket:
        from pillcare.gcs_loader import download_db

        local_path = "/tmp/pillcare.db"
        if not Path(local_path).exists():
            download_db(
                bucket_name=gcs_bucket,
                blob_name=os.environ.get("GCS_BLOB", "pillcare.db"),
                local_path=local_path,
                expected_sha256=os.environ.get("DB_SHA256"),
            )
        return local_path

    # Local development: use project-relative path
    project_root = Path(__file__).resolve().parent.parent.parent
    return str(project_root / "data" / "pillcare.db")


@st.cache_resource
def _get_pipeline(db_path: str):
    """Cache compiled graph across Streamlit reruns."""
    llm = create_llm()
    return build_pipeline(db_path=db_path, llm=llm)


def main():
    st.set_page_config(page_title="필케어 — 복약 정보 안내", layout="wide")
    st.title("필케어 (PillCare)")
    st.caption("개인 투약이력 기반 grounded 복약 정보 안내 POC")
    st.info(_DISCLAIMER)

    db_path = _get_db_path()
    if not Path(db_path).exists():
        st.error(f"DB not found at {db_path}. Run `uv run python -m pillcare.db_builder` or set GCS_BUCKET env var.")
        return

    uploaded_files = st.file_uploader(
        "심평원 '내가 먹는 약' 투약이력 파일 업로드 (.xls)",
        type=["xls"],
        accept_multiple_files=True,
    )

    password = st.text_input("파일 비밀번호", type="password")

    departments: dict[str, str] = {}
    if uploaded_files:
        for uf in uploaded_files:
            departments[uf.name] = st.text_input(
                f"{uf.name}의 진료과", value="미지정", key=f"dept_{uf.name}"
            )

    if not uploaded_files or not password:
        st.info("투약이력 파일을 업로드하고 비밀번호를 입력하세요.")
        return

    if st.button("분석 시작"):
        from pillcare.history_parser import parse_history_xls

        with st.spinner("투약이력 파싱 중..."):
            all_records = []
            for uf in uploaded_files:
                dept = departments.get(uf.name, "미지정")
                with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
                    tmp.write(uf.read())
                    tmp_path = Path(tmp.name)
                try:
                    records = parse_history_xls(tmp_path, password=password, department=dept)
                finally:
                    tmp_path.unlink(missing_ok=True)
                for rec in records:
                    all_records.append({
                        "drug_name": rec.drug_name,
                        "drug_code": rec.drug_code,
                        "department": rec.department,
                    })

        st.success(f"{len(all_records)}개 약물 파싱 완료")

        with st.spinner("LangGraph 파이프라인 실행 중..."):
            graph = _get_pipeline(db_path)
            initial_state = {
                "profile_id": "default",
                "raw_records": all_records,
                "matched_drugs": [],
                "dur_alerts": [],
                "drug_infos": [],
                "guidance_result": None,
                "errors": [],
            }
            final_state = graph.invoke(initial_state)

        result_data = final_state.get("guidance_result")
        if result_data:
            result = GuidanceResult(**result_data) if isinstance(result_data, dict) else result_data

            if result.dur_warnings:
                st.subheader("병용금기 경고")
                for w in result.dur_warnings:
                    cross = " (다기관 교차)" if w.cross_clinic else ""
                    st.error(f"**{w.drug_1}** x **{w.drug_2}**: {w.reason}{cross}")

            if result.drug_guidances:
                st.subheader("상세 복약 정보 (별첨1)")
                for dg in result.drug_guidances:
                    with st.expander(dg.drug_name):
                        for section_name, section in dg.sections.items():
                            st.markdown(f"**{section.title}** `{section.source_tier.value}`")
                            st.write(section.content)

            if result.summary:
                st.subheader("핵심 요약 (별첨2)")
                for point in result.summary:
                    st.write(f"- {point}")

            if result.warning_labels:
                st.subheader("경고 라벨 (별첨3)")
                for label in result.warning_labels:
                    st.warning(label)

        errors = final_state.get("errors", [])
        if errors:
            st.subheader("검증 결과")
            for e in errors:
                if e.startswith("[CRITICAL]"):
                    st.error(e)
                else:
                    st.warning(e)


if __name__ == "__main__":
    main()
```

Key changes:
- Replaced `ChatAnthropic` with `create_llm()` from `llm_factory`
- Added `_get_db_path()` for GCS or local DB
- Removed `api_key` parameter from `_get_pipeline`
- Added disclaimer (`_DISCLAIMER`) shown via `st.info()`
- Lazy import of `history_parser` (only when button clicked)

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest --tb=short`
Expected: All tests pass (app.py is not directly unit-tested — Streamlit integration).

- [ ] **Step 3: Commit**

```bash
git add src/pillcare/app.py
git commit -m "refactor: app uses LLM factory + GCS DB loading + disclaimer"
```

---

### Task 9: Logging Configuration

**Files:**
- Create: `src/pillcare/logging_config.py`

- [ ] **Step 1: Create logging_config.py**

Create `src/pillcare/logging_config.py`:

```python
"""JSON structured logging for Cloud Logging compatibility."""

import json
import logging
import os
import sys


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging() -> None:
    """Configure root logger with JSON formatter.

    Uses LOG_LEVEL env var (default: WARNING for PII protection in Cloud Run).
    """
    level = os.environ.get("LOG_LEVEL", "WARNING").upper()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
```

- [ ] **Step 2: Add setup_logging call to app.py**

Add at the top of `src/pillcare/app.py`, after `load_dotenv()`:

```python
from pillcare.logging_config import setup_logging
setup_logging()
```

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest --tb=short`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/pillcare/logging_config.py src/pillcare/app.py
git commit -m "feat: add JSON structured logging for Cloud Logging"
```

---

### Task 10: Streamlit Config for Cloud Run

**Files:**
- Create: `.streamlit/config.toml`

- [ ] **Step 1: Create .streamlit/config.toml**

```bash
mkdir -p .streamlit
```

Create `.streamlit/config.toml`:

```toml
[server]
headless = true
address = "0.0.0.0"
port = 8501
enableWebsocketCompression = false
enableXsrfProtection = true
maxUploadSize = 10
```

- [ ] **Step 2: Commit**

```bash
git add .streamlit/config.toml
git commit -m "config: add Streamlit config for Cloud Run (headless, no ws compression)"
```

---

### Task 11: Dockerfile and .dockerignore

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Create .dockerignore**

Create `.dockerignore`:

```
data/
tests/
docs/
research/
person_sample/
scripts/
.claude/
.venv/
.git/
.github/
__pycache__/
*.pyc
.env
.env.example
.DS_Store
*.md
uv.lock
```

Note: `uv.lock` is excluded from `.dockerignore` only in the ignore list — it IS needed for the build. Remove `uv.lock` from the above. Corrected:

```
data/
tests/
docs/
research/
person_sample/
scripts/
.claude/
.venv/
.git/
.github/
__pycache__/
*.pyc
.env
.env.example
.DS_Store
```

- [ ] **Step 2: Create Dockerfile**

Create `Dockerfile`:

```dockerfile
# === Stage 1: Builder ===
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first (cache-friendly layer ordering)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy app source and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# === Stage 2: Runtime ===
FROM python:3.11-slim-bookworm

RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

COPY --from=builder --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH"
USER nonroot
WORKDIR /app

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "src/pillcare/app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true"]
```

- [ ] **Step 3: Verify Docker build locally (optional)**

Run: `docker build -t pillcare:test .`
Expected: Build completes. (~300-500MB image)

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "build: add multi-stage Dockerfile with uv for Cloud Run"
```

---

### Task 12: GitHub Actions CI/CD Workflow

**Files:**
- Create: `.github/workflows/ci-cd.yml`

- [ ] **Step 1: Create workflow directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create ci-cd.yml**

Create `.github/workflows/ci-cd.yml`:

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGION: asia-northeast3
  SERVICE: pillcare
  IMAGE: asia-northeast3-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/pillcare/app

jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync --frozen

      - name: Lint
        run: uv run ruff check .

      - name: Format check
        run: uv run ruff format --check .

      - name: Test
        run: uv run pytest --tb=short

  build-deploy:
    needs: [lint-test]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.WIF_PROVIDER }}
          service_account: ${{ vars.DEPLOYER_SA }}

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev --quiet

      - uses: docker/setup-buildx-action@v3

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ env.IMAGE }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: ${{ env.SERVICE }}
          image: ${{ env.IMAGE }}:${{ github.sha }}
          region: ${{ env.REGION }}
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci-cd.yml
git commit -m "ci: add GitHub Actions workflow for lint, test, build, deploy"
```

---

### Task 13: .env.example Update and Final Verification

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Update .env.example**

Replace `.env.example`:

```bash
# LLM Provider: "gemini" (default) or "claude"
LLM_PROVIDER=gemini

# Gemini (Vertex AI) — used when LLM_PROVIDER=gemini
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=asia-northeast3

# Claude (Anthropic) — used when LLM_PROVIDER=claude
# ANTHROPIC_API_KEY=sk-ant-...

# GCS Database — set to enable GCS download (Cloud Run)
# GCS_BUCKET=pillcare-data
# GCS_BLOB=pillcare.db
# DB_SHA256=<sha256-of-pillcare.db>

# Logging
LOG_LEVEL=WARNING

# 식약처 Open API (for crawling, not runtime)
# MFDS_API_KEY=your-api-key
```

- [ ] **Step 2: Run full test suite one final time**

Run: `uv run pytest -v`
Expected: All tests pass (57 existing + ~10 new = ~67 tests).

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "docs: update .env.example with GCP deployment config"
```

---

## Self-Review

### Spec Coverage

| Spec Section | Task(s) | Status |
|---|---|---|
| §1 LLM 전환 (Gemini + structured output) | T2, T4, T5, T6 | Covered |
| §1 안전 필터 설정 | T4 (llm_factory) | Covered |
| §1 Structured Output 전환 | T2, T5, T6 | Covered |
| §1 프롬프트 호환성 대응 | T5 | Covered |
| §2 GCS → Cloud Run 데이터 | T3 | Covered |
| §2 DB 업데이트 프로세스 | T13 (.env.example docs) | Covered (manual process) |
| §3 Dockerfile | T11 | Covered |
| §3 .dockerignore | T11 | Covered |
| §3 Python 버전 통일 | T11 (python:3.11) | Covered |
| §4 Cloud Run 설정 | T12 (deploy action) | Covered (runtime config via gcloud) |
| §5 서비스 계정 | Infra setup, not code | N/A (GCP console/CLI) |
| §6 CI/CD GitHub Actions | T12 | Covered |
| §6 WIF 설정 | Infra setup, not code | N/A (GCP console/CLI) |
| §7 Cloud Logging | T9 | Covered |
| §7 비용 알림 | Infra setup, not code | N/A (GCP console/CLI) |
| §8 비용 예상 | Info only | N/A |
| §9 확장 경로 | Info only | N/A |
| §10 GCP 서비스 활성화 | Infra setup, not code | N/A |
| §11 UI 면책 문구 | T8 (app.py _DISCLAIMER) | Covered |

### Placeholder Scan

No TBD, TODO, or "implement later" found. All steps contain concrete code.

### Type Consistency

- `DrugSectionOutput` / `DrugGuidanceOutput` — defined in T2, used in T5 (pipeline), T6 (test fixtures)
- `to_drug_guidance()` — defined in T2, called in T5
- `create_llm()` — defined in T4, called in T8
- `download_db()` / `compute_sha256()` — defined in T3, called in T8
- `filter_banned_words()` — unchanged, called in T5 (pipeline refactor applies it to section.content)
- `verify_source_tags()` — signature unchanged, implementation updated in T7, tests updated in T7
