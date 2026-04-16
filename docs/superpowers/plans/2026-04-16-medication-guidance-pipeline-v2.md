# 복약 정보 안내 파이프라인 v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data layer + LangGraph processing pipeline that takes personal medication history (심평원 "내가 먹는 약") and generates grounded medication guidance per 복약지도 10-item checklist, with deterministic DUR cross-check, source tier tag grounding, and multi-layer guardrails.

**Architecture:** 3-Phase pipeline orchestrated by LangGraph StateGraph.
- **Phase 1 (Deterministic):** SQLite DB (43K drugs, FTS5 trigram index) → history parser → EDI/FTS5/fuzzy drug matcher → multi-ingredient N×N DUR checker → drug info collector.
- **Phase 2 (LLM):** LangGraph invokes Claude Sonnet 4.6 via langchain-anthropic, generating guidance per-drug sequentially with source tier tags ([T1:허가정보], [T1:DUR], [T1:e약은요], [T4:AI]) enforced by system prompt. Structured Pydantic output. (Production path: Anthropic Citations API for char-level grounding — deferred from POC.)
- **Phase 3 (Deterministic):** Post-verification — DUR coverage check, source tag validation, T4 ratio limit, mandatory closing phrase, banned word filter. Retry loop (max 1) on critical failures.

**Tech Stack:** Python 3.11 · uv · langgraph · langchain-anthropic · langchain-core · anthropic SDK · sqlite3 (stdlib) · rapidfuzz · pydantic · pytest · streamlit · python-dotenv · msoffcrypto-tool (xls decrypt) · openpyxl

**Supersedes:** `2026-04-15-medication-guidance-pipeline.md` (v1). Changes: LangGraph orchestration, multi-ingredient DUR, EDI+FTS5 matching, Citations API, enhanced guardrails, prompt caching, structured output.

---

## File Structure

```
pill-care/
├── pyproject.toml                     # Task 1: project setup
├── .python-version                    # Python 3.11
├── .env.example                       # ANTHROPIC_API_KEY
├── .gitignore
├── data/
│   ├── drug_permit_detail.json        # 43,250 items (crawled, 2.2GB — gitignored)
│   ├── drug_permit_detail.csv         # 43,250 items (crawled, 48MB)
│   ├── easy_drug_info.json            # 4,711 items (crawled)
│   ├── bundle_drug_info.json          # 16,322 items (crawled)
│   ├── medicines.csv                  # 25,685 items (downloaded)
│   ├── 한국의약품안전관리원_병용금기약물_20240625.csv  # 542,996 rows (gitignored)
│   └── metadata.json
├── person_sample/
│   ├── 개인투약이력 가정의학과.xls     # Encrypted sample (pw: 19971207)
│   └── 개인투약이력 안과.xls
├── scripts/
│   ├── crawl_easy_drug.py             # (exists)
│   ├── crawl_drug_permit.py           # (exists)
│   └── crawl_bundle.py               # (exists)
├── src/pillcare/
│   ├── __init__.py
│   ├── db_builder.py                  # Task 2: SQLite DB builder + FTS5 index
│   ├── xml_parser.py                  # Task 3: NB_DOC_DATA XML → sections
│   ├── dur_normalizer.py              # Task 4: DUR CSV → normalized pairs
│   ├── history_parser.py              # Task 5: xls → medication_history records
│   ├── drug_matcher.py                # Task 6: 4-phase matching (EDI → exact → FTS5 → fuzzy)
│   ├── dur_checker.py                 # Task 7: multi-ingredient N×N DUR cross-check
│   ├── drug_info.py                   # Task 8: item_seq → structured drug info
│   ├── schemas.py                     # Task 9: Pydantic models for pipeline state + output
│   ├── prompts.py                     # Task 10: System prompts + prompt templates
│   ├── tools.py                       # Task 10: LangGraph tool node functions
│   ├── pipeline.py                    # Task 10: LangGraph StateGraph definition
│   ├── guardrails.py                  # Task 11: post-verification + safety filters
│   └── app.py                         # Task 12: Streamlit UI
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   ├── small_permit.json          # Task 2: 5-row permit fixture
    │   ├── small_easy.json            # Task 2: 3-row e약은요 fixture
    │   ├── sample_nb_doc.xml          # Task 3: NB_DOC_DATA XML fixture
    │   ├── small_dur.csv              # Task 4: 5-pair DUR fixture
    │   └── sample_history.json        # Task 5: parsed history fixture
    ├── test_db_builder.py             # Task 2
    ├── test_xml_parser.py             # Task 3
    ├── test_dur_normalizer.py         # Task 4
    ├── test_history_parser.py         # Task 5
    ├── test_drug_matcher.py           # Task 6
    ├── test_dur_checker.py            # Task 7
    ├── test_drug_info.py              # Task 8
    ├── test_schemas.py                # Task 9
    ├── test_pipeline.py               # Task 10
    └── test_guardrails.py             # Task 11
```

**Decomposition rationale:**
- Tasks 2-8: Deterministic modules, one per pipeline sub-stage. Unchanged from v1 except Task 6 (matcher) and Task 7 (DUR checker).
- Task 9 (NEW): `schemas.py` — Pydantic models shared across all modules. Extracted because pipeline state flows through every node.
- Task 10 (NEW): `pipeline.py` + `tools.py` + `prompts.py` — LangGraph orchestration replaces v1's monolithic `agent.py`. Split into 3 files by responsibility: graph topology, tool implementations, prompt content.
- Task 11: `guardrails.py` — expanded from v1 with 3 additional checks.
- Task 12: `app.py` — Streamlit UI, minor adjustments for new pipeline.
- Task 13: Full DB build + E2E smoke test.

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.env.example`
- Create: `src/pillcare/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Install Python 3.11 via uv**

```bash
cd /Users/User/Documents/pill-care
uv python install 3.11
```

- [ ] **Step 2: Initialize uv project**

```bash
uv init --package --name pillcare --python 3.11
```

Delete any scaffold files (`hello.py` etc.) if generated.

- [ ] **Step 3: Verify dependency versions via context7/PyPI**

```bash
npx ctx7@latest library langgraph "LangGraph state graph agent orchestration"
npx ctx7@latest library langchain-anthropic "LangChain Anthropic Claude integration"
npx ctx7@latest library anthropic "python SDK for Claude with tool_use"
npx ctx7@latest library rapidfuzz "fuzzy string matching Python"
npx ctx7@latest library pydantic "data validation and settings management"
npx ctx7@latest library pytest "Python testing framework"
npx ctx7@latest library streamlit "Python web app framework"
npx ctx7@latest library python-dotenv "load .env files in Python"
npx ctx7@latest library msoffcrypto-tool "decrypt Microsoft Office files"
```

Pick current stable versions compatible with Python 3.11. Verify langgraph and langchain-anthropic are compatible with each other (same langchain-core version).

- [ ] **Step 4: Install dependencies with pinned verified versions**

```bash
uv add "langgraph==<verified>" "langchain-anthropic==<verified>" "langchain-core==<verified>" "anthropic==<verified>" "rapidfuzz==<verified>" "pydantic==<verified>" "python-dotenv==<verified>" "msoffcrypto-tool==<verified>" "openpyxl==<verified>"
uv add --dev "pytest==<verified>" "streamlit==<verified>"
```

- [ ] **Step 5: Create `.env.example`**

```
# Copy to .env and fill in your key
ANTHROPIC_API_KEY=sk-ant-...
MFDS_API_KEY=3iGPxpCbDiTPYBMX63OlN2JFVhR2o62RGYp4l7GhVF3d3240QJeXKrMCxt7WQdrsqruqu+2Hz7+RORu9k1SuMA==
```

- [ ] **Step 6: Create package and test structure**

Create `src/pillcare/__init__.py`:

```python
"""필케어 (PillCare) — 복약 정보 안내 파이프라인 POC."""

__version__ = "0.1.0"
```

Create `tests/__init__.py` as empty file.

Create `tests/conftest.py`:

```python
"""Shared pytest fixtures for 필케어 tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).parent.parent / "data"
```

- [ ] **Step 7: Verify pytest runs**

```bash
uv run pytest -v
```

Expected: `no tests ran` (collection succeeds).

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .python-version .env.example src/ tests/ uv.lock
git commit -m "chore: bootstrap project with uv, LangGraph, and verified deps"
```

---

## Task 2: DB Builder — SQLite from Crawled Data + FTS5 Index

**Files:**
- Create: `src/pillcare/db_builder.py`
- Create: `tests/test_db_builder.py`
- Create: `tests/fixtures/small_permit.json`
- Create: `tests/fixtures/small_easy.json`

- [ ] **Step 1: Create test fixtures**

Create `tests/fixtures/small_permit.json`:

```json
[
  {
    "ITEM_SEQ": "199701416",
    "ITEM_NAME": "리도펜연질캡슐(이부프로펜)",
    "ITEM_ENG_NAME": "Lidopen Soft Cap.(Ibuprofen)",
    "ENTP_NAME": "(주)메디카코리아",
    "ETC_OTC_CODE": "일반의약품",
    "MATERIAL_NAME": "총량 : 1캡슐 중|성분명 : 이부프로펜|분량 : 200|단위 : 밀리그램|규격 : KP|성분정보 : |비고 :",
    "MAIN_ITEM_INGR": "[M040702]이부프로펜",
    "MAIN_INGR_ENG": "Ibuprofen",
    "CHART": "주황색의 장방형 연질캡슐제",
    "ATC_CODE": "M01AE01",
    "STORAGE_METHOD": "실온보관(1-30℃)",
    "VALID_TERM": "제조일로부터 24 개월",
    "EDI_CODE": "649301290",
    "EE_DOC_DATA": "<DOC title=\"효능효과\" type=\"EE\"><SECTION title=\"\"><ARTICLE title=\"\"><PARAGRAPH>감기로 인한 발열 및 동통(통증), 두통, 치통, 근육통, 관절통</PARAGRAPH></ARTICLE></SECTION></DOC>",
    "UD_DOC_DATA": "<DOC title=\"용법용량\" type=\"UD\"><SECTION title=\"\"><ARTICLE title=\"\"><PARAGRAPH>성인: 1회 1-2캡슐, 1일 3-4회 복용</PARAGRAPH></ARTICLE></SECTION></DOC>",
    "NB_DOC_DATA": "<DOC title=\"사용상의주의사항\" type=\"NB\"><SECTION title=\"\"><ARTICLE title=\"1. 다음 환자에는 투여하지 말 것.\"><PARAGRAPH>이 약에 과민증 환자</PARAGRAPH></ARTICLE><ARTICLE title=\"5. 상호작용\"><PARAGRAPH>다른 비스테로이드성 소염진통제와 함께 복용하지 마십시오.</PARAGRAPH></ARTICLE><ARTICLE title=\"3. 이상반응\"><PARAGRAPH>쇽 증상, 소화성궤양, 위장출혈</PARAGRAPH></ARTICLE></SECTION></DOC>",
    "TOTAL_CONTENT": "1캡슐 중",
    "MAKE_MATERIAL_FLAG": "완제의약품",
    "INDUTY_TYPE": "의약품",
    "BIZRNO": "1208165228"
  },
  {
    "ITEM_SEQ": "200003404",
    "ITEM_NAME": "알게텍정",
    "ITEM_ENG_NAME": "Algetec Tab.",
    "ENTP_NAME": "알게텍제약(주)",
    "ETC_OTC_CODE": "전문의약품",
    "MATERIAL_NAME": "총량 : 1정 중|성분명 : 알마게이트|분량 : 500|단위 : 밀리그램|규격 : 별규|성분정보 : |비고 :",
    "MAIN_ITEM_INGR": "[M254901]알마게이트",
    "MAIN_INGR_ENG": "Almagate",
    "CHART": "백색의 원형 정제",
    "ATC_CODE": "A02AD",
    "STORAGE_METHOD": "기밀용기, 실온(1-30℃)보관",
    "VALID_TERM": "제조일로부터 36 개월",
    "EDI_CODE": "057600010",
    "EE_DOC_DATA": "<DOC title=\"효능효과\" type=\"EE\"><SECTION title=\"\"><ARTICLE title=\"\"><PARAGRAPH>위·십이지장궤양, 위염, 위산과다</PARAGRAPH></ARTICLE></SECTION></DOC>",
    "UD_DOC_DATA": "<DOC title=\"용법용량\" type=\"UD\"><SECTION title=\"\"><ARTICLE title=\"\"><PARAGRAPH>성인 1회 1-2정, 1일 3-4회 식간 및 취침 시 복용</PARAGRAPH></ARTICLE></SECTION></DOC>",
    "NB_DOC_DATA": "<DOC title=\"사용상의주의사항\" type=\"NB\"><SECTION title=\"\"><ARTICLE title=\"1. 다음 환자에는 투여하지 말 것.\"><PARAGRAPH>이 약에 과민증 환자</PARAGRAPH></ARTICLE><ARTICLE title=\"5. 상호작용\"><PARAGRAPH>테트라사이클린계 항생물질의 흡수를 저해할 수 있으므로 동시 투여를 피한다.</PARAGRAPH></ARTICLE></SECTION></DOC>",
    "TOTAL_CONTENT": "1정 중",
    "MAKE_MATERIAL_FLAG": "완제의약품",
    "INDUTY_TYPE": "의약품",
    "BIZRNO": "1234567890"
  },
  {
    "ITEM_SEQ": "200500001",
    "ITEM_NAME": "코대원정",
    "ITEM_ENG_NAME": "Codaewon Tab.",
    "ENTP_NAME": "대원제약(주)",
    "ETC_OTC_CODE": "전문의약품",
    "MATERIAL_NAME": "총량 : 1정 중|성분명 : 클로르페니라민말레산염|분량 : 2|단위 : 밀리그램|성분명 : 디히드로코데인타르타르산염|분량 : 5|단위 : 밀리그램",
    "MAIN_ITEM_INGR": "[M175201]클로르페니라민말레산염|[M146801]디히드로코데인타르타르산염",
    "MAIN_INGR_ENG": "Chlorpheniramine Maleate|Dihydrocodeine Tartrate",
    "CHART": "백색의 원형 정제",
    "ATC_CODE": "R05DA",
    "STORAGE_METHOD": "기밀용기, 실온(1-30℃)보관",
    "VALID_TERM": "제조일로부터 36 개월",
    "EDI_CODE": null,
    "EE_DOC_DATA": "<DOC title=\"효능효과\" type=\"EE\"><SECTION title=\"\"><ARTICLE title=\"\"><PARAGRAPH>기침</PARAGRAPH></ARTICLE></SECTION></DOC>",
    "UD_DOC_DATA": "<DOC title=\"용법용량\" type=\"UD\"><SECTION title=\"\"><ARTICLE title=\"\"><PARAGRAPH>성인 1회 1정, 1일 3회</PARAGRAPH></ARTICLE></SECTION></DOC>",
    "NB_DOC_DATA": "<DOC title=\"사용상의주의사항\" type=\"NB\"><SECTION title=\"\"><ARTICLE title=\"1. 경고\"><PARAGRAPH>MAO 억제제를 복용 중인 환자는 이 약을 복용하지 마십시오.</PARAGRAPH></ARTICLE><ARTICLE title=\"5. 상호작용\"><PARAGRAPH>MAO 억제제, 중추신경억제제와 병용 시 작용이 증강됩니다.</PARAGRAPH></ARTICLE></SECTION></DOC>",
    "TOTAL_CONTENT": "1정 중",
    "MAKE_MATERIAL_FLAG": "완제의약품",
    "INDUTY_TYPE": "의약품",
    "BIZRNO": "9876543210"
  }
]
```

Note: 3rd fixture (코대원정) has **multi-ingredient** `MAIN_ITEM_INGR` with pipe separator — critical for testing Task 7.

Create `tests/fixtures/small_easy.json`:

```json
[
  {
    "itemSeq": "199701416",
    "itemName": "리도펜연질캡슐(이부프로펜)",
    "entpName": "(주)메디카코리아",
    "efcyQesitm": "이 약은 감기로 인한 발열 및 동통(통증), 두통, 치통에 사용합니다.",
    "useMethodQesitm": "성인은 1회 1-2캡슐, 1일 3-4회 복용합니다.",
    "atpnWarnQesitm": "매일 세 잔 이상 정기적 음주자가 이 약을 복용할 때는 의사와 상의하십시오.",
    "atpnQesitm": "이 약에 과민증 환자는 복용하지 마십시오.",
    "intrcQesitm": "다른 비스테로이드성 소염진통제와 함께 복용하지 마십시오.",
    "seQesitm": "쇽 증상, 소화성궤양, 위장출혈이 나타날 수 있습니다.",
    "depositMethodQesitm": "실온에서 보관하십시오."
  }
]
```

- [ ] **Step 2: Write failing test for db_builder**

Create `tests/test_db_builder.py`:

```python
"""Tests for SQLite DB builder."""

import json
import sqlite3
from pathlib import Path

import pytest

from pillcare.db_builder import build_db


@pytest.fixture
def small_permit(fixtures_dir: Path) -> list[dict]:
    with open(fixtures_dir / "small_permit.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def small_easy(fixtures_dir: Path) -> list[dict]:
    with open(fixtures_dir / "small_easy.json", encoding="utf-8") as f:
        return json.load(f)


def test_build_db_creates_drugs_table(tmp_path: Path, small_permit, small_easy):
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM drugs")
    assert cursor.fetchone()[0] == 3

    cursor = conn.execute(
        "SELECT item_name, atc_code, main_item_ingr FROM drugs WHERE item_seq = '199701416'"
    )
    row = cursor.fetchone()
    assert row[0] == "리도펜연질캡슐(이부프로펜)"
    assert row[1] == "M01AE01"
    assert "[M040702]이부프로펜" in row[2]
    conn.close()


def test_build_db_creates_drugs_easy_table(tmp_path: Path, small_permit, small_easy):
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM drugs_easy")
    assert cursor.fetchone()[0] == 1

    cursor = conn.execute(
        "SELECT efcy_qesitm FROM drugs_easy WHERE item_seq = '199701416'"
    )
    row = cursor.fetchone()
    assert "감기" in row[0]
    conn.close()


def test_build_db_creates_fts5_index(tmp_path: Path, small_permit, small_easy):
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    # FTS5 trigram search for Korean substring
    cursor = conn.execute(
        "SELECT item_name FROM drugs_fts WHERE drugs_fts MATCH '리도펜'"
    )
    rows = cursor.fetchall()
    assert len(rows) >= 1
    assert "리도펜" in rows[0][0]

    # FTS5 search for English ingredient
    cursor = conn.execute(
        "SELECT item_name FROM drugs_fts WHERE drugs_fts MATCH 'Ibuprofen'"
    )
    rows = cursor.fetchall()
    assert len(rows) >= 1
    conn.close()


def test_build_db_is_idempotent(tmp_path: Path, small_permit, small_easy):
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM drugs")
    assert cursor.fetchone()[0] == 3
    conn.close()
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_db_builder.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'pillcare.db_builder'`

- [ ] **Step 4: Implement db_builder.py**

Create `src/pillcare/db_builder.py`:

```python
"""Build SQLite DB from crawled 식약처 API data."""

import sqlite3
from pathlib import Path


_DRUGS_DDL = """
CREATE TABLE IF NOT EXISTS drugs (
    item_seq        TEXT PRIMARY KEY,
    item_name       TEXT NOT NULL,
    item_eng_name   TEXT,
    entp_name       TEXT NOT NULL,
    etc_otc_code    TEXT,
    material_name   TEXT,
    main_item_ingr  TEXT,
    main_ingr_eng   TEXT,
    chart           TEXT,
    atc_code        TEXT,
    storage_method  TEXT,
    valid_term      TEXT,
    edi_code        TEXT,
    ee_doc_data     TEXT,
    ud_doc_data     TEXT,
    nb_doc_data     TEXT,
    total_content   TEXT,
    updated_at      TEXT
)
"""

_DRUGS_EASY_DDL = """
CREATE TABLE IF NOT EXISTS drugs_easy (
    item_seq                TEXT PRIMARY KEY REFERENCES drugs(item_seq),
    efcy_qesitm             TEXT,
    use_method_qesitm       TEXT,
    atpn_warn_qesitm        TEXT,
    atpn_qesitm             TEXT,
    intrc_qesitm            TEXT,
    se_qesitm               TEXT,
    deposit_method_qesitm   TEXT
)
"""

_DRUG_SECTIONS_DDL = """
CREATE TABLE IF NOT EXISTS drug_sections (
    item_seq      TEXT REFERENCES drugs(item_seq),
    section_type  TEXT NOT NULL,
    section_title TEXT,
    section_text  TEXT NOT NULL,
    section_order INTEGER,
    PRIMARY KEY (item_seq, section_type, section_order)
)
"""

_DUR_PAIRS_DDL = """
CREATE TABLE IF NOT EXISTS dur_pairs (
    ingr_code_1   TEXT NOT NULL,
    ingr_name_1   TEXT NOT NULL,
    ingr_code_2   TEXT NOT NULL,
    ingr_name_2   TEXT NOT NULL,
    reason        TEXT NOT NULL,
    notice_date   TEXT,
    PRIMARY KEY (ingr_code_1, ingr_code_2)
)
"""

_BUNDLE_ATC_DDL = """
CREATE TABLE IF NOT EXISTS bundle_atc (
    trust_item_name          TEXT,
    trust_mainingr           TEXT,
    trust_atc_code           TEXT,
    trust_hira_mainingr_code TEXT,
    trust_hira_product_code  TEXT
)
"""

_MEDICATION_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS medication_history (
    profile_id      TEXT NOT NULL,
    seq             INTEGER,
    drug_name       TEXT NOT NULL,
    drug_class      TEXT,
    ingredient      TEXT,
    drug_code       TEXT,
    unit            TEXT,
    dose_per_time   REAL,
    times_per_day   INTEGER,
    duration_days   INTEGER,
    safety_letter   TEXT,
    antithrombotic  TEXT,
    department      TEXT,
    item_seq        TEXT REFERENCES drugs(item_seq),
    ingr_codes      TEXT
)
"""

_FTS5_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS drugs_fts USING fts5(
    item_name, item_eng_name, main_item_ingr, main_ingr_eng,
    content=drugs, content_rowid=rowid,
    tokenize='trigram'
)
"""

_FTS5_POPULATE = """
INSERT INTO drugs_fts(drugs_fts) VALUES('rebuild')
"""

_EDI_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_drugs_edi_code ON drugs(edi_code)
"""

_ITEM_NAME_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_drugs_item_name ON drugs(item_name)
"""


def build_db(
    db_path: Path,
    permit_data: list[dict],
    easy_data: list[dict] | None = None,
) -> Path:
    """Create or rebuild the SQLite DB from crawled data.

    Args:
        db_path: Where to create the DB file.
        permit_data: List of dicts from drug_permit_detail.json.
        easy_data: List of dicts from easy_drug_info.json (optional).

    Returns:
        The db_path for chaining.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    for ddl in [
        _DRUGS_DDL, _DRUGS_EASY_DDL, _DRUG_SECTIONS_DDL,
        _DUR_PAIRS_DDL, _BUNDLE_ATC_DDL, _MEDICATION_HISTORY_DDL,
    ]:
        conn.execute(ddl)

    # Upsert drugs
    conn.execute("DELETE FROM drugs")
    for item in permit_data:
        conn.execute(
            """INSERT OR REPLACE INTO drugs
            (item_seq, item_name, item_eng_name, entp_name, etc_otc_code,
             material_name, main_item_ingr, main_ingr_eng, chart, atc_code,
             storage_method, valid_term, edi_code, ee_doc_data, ud_doc_data,
             nb_doc_data, total_content)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.get("ITEM_SEQ"), item.get("ITEM_NAME"),
                item.get("ITEM_ENG_NAME"), item.get("ENTP_NAME"),
                item.get("ETC_OTC_CODE"), item.get("MATERIAL_NAME"),
                item.get("MAIN_ITEM_INGR"), item.get("MAIN_INGR_ENG"),
                item.get("CHART"), item.get("ATC_CODE"),
                item.get("STORAGE_METHOD"), item.get("VALID_TERM"),
                item.get("EDI_CODE"), item.get("EE_DOC_DATA"),
                item.get("UD_DOC_DATA"), item.get("NB_DOC_DATA"),
                item.get("TOTAL_CONTENT"),
            ),
        )

    # Create indexes
    conn.execute(_EDI_INDEX_DDL)
    conn.execute(_ITEM_NAME_INDEX_DDL)

    # Build FTS5 trigram index
    # Drop and recreate FTS5 (virtual tables don't support IF NOT EXISTS cleanly on rebuild)
    conn.execute("DROP TABLE IF EXISTS drugs_fts")
    conn.execute(_FTS5_DDL)
    conn.execute(_FTS5_POPULATE)

    # Upsert drugs_easy
    if easy_data:
        conn.execute("DELETE FROM drugs_easy")
        for item in easy_data:
            conn.execute(
                """INSERT OR REPLACE INTO drugs_easy
                (item_seq, efcy_qesitm, use_method_qesitm, atpn_warn_qesitm,
                 atpn_qesitm, intrc_qesitm, se_qesitm, deposit_method_qesitm)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    item.get("itemSeq"), item.get("efcyQesitm"),
                    item.get("useMethodQesitm"), item.get("atpnWarnQesitm"),
                    item.get("atpnQesitm"), item.get("intrcQesitm"),
                    item.get("seQesitm"), item.get("depositMethodQesitm"),
                ),
            )

    conn.commit()
    conn.close()
    return db_path
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_db_builder.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pillcare/db_builder.py tests/test_db_builder.py tests/fixtures/small_permit.json tests/fixtures/small_easy.json
git commit -m "feat: add db_builder — SQLite from crawled data with FTS5 trigram index"
```

---

## Task 3: XML Parser — NB_DOC_DATA → Sections

**Same as v1.** See `2026-04-15-medication-guidance-pipeline.md` Task 3.

**Files:**
- Create: `src/pillcare/xml_parser.py`
- Create: `tests/test_xml_parser.py`
- Create: `tests/fixtures/sample_nb_doc.xml`

No changes from v1. The xml_parser implementation handles the known section types. Edge cases (CDATA, nested ARTICLE, malformed XML) will be tested in Task 13 against the full 43K dataset.

---

## Task 4: DUR Normalizer — CSV → Normalized Pairs

**Same as v1.** See `2026-04-15-medication-guidance-pipeline.md` Task 4.

**Files:**
- Create: `src/pillcare/dur_normalizer.py`
- Create: `tests/test_dur_normalizer.py`
- Create: `tests/fixtures/small_dur.csv`

No changes from v1.

---

## Task 5: History Parser — XLS → Medication Records

**Same as v1.** See `2026-04-15-medication-guidance-pipeline.md` Task 5.

**Files:**
- Create: `src/pillcare/history_parser.py`
- Create: `tests/test_history_parser.py`
- Create: `tests/fixtures/sample_history.json`

No changes from v1.

---

## Task 6: Drug Matcher — 4-Phase Matching (EDI → Exact → FTS5 → Fuzzy)

**v2 CHANGE: Added EDI code matching (Phase 1), FTS5 trigram search (Phase 3), multi-ingredient code extraction.**

**Files:**
- Create: `src/pillcare/drug_matcher.py`
- Create: `tests/test_drug_matcher.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_drug_matcher.py`:

```python
"""Tests for 4-phase drug matcher."""

import json
import sqlite3
from pathlib import Path

import pytest

from pillcare.db_builder import build_db
from pillcare.drug_matcher import match_drug, DrugMatch, extract_ingr_codes


@pytest.fixture
def db_path(tmp_path: Path, fixtures_dir: Path) -> Path:
    with open(fixtures_dir / "small_permit.json", encoding="utf-8") as f:
        permit = json.load(f)
    with open(fixtures_dir / "small_easy.json", encoding="utf-8") as f:
        easy = json.load(f)
    return build_db(tmp_path / "test.db", permit_data=permit, easy_data=easy)


def test_match_by_edi_code(db_path):
    """Phase 1: EDI code exact match (highest priority)."""
    result = match_drug(db_path, "아무약이름", edi_code="649301290")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score == 100


def test_match_exact_name(db_path):
    """Phase 2: Exact item_name match."""
    result = match_drug(db_path, "리도펜연질캡슐(이부프로펜)")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score == 100


def test_match_fts5_substring(db_path):
    """Phase 3: FTS5 trigram substring match."""
    result = match_drug(db_path, "리도펜")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score >= 80


def test_match_fuzzy_partial(db_path):
    """Phase 4: rapidfuzz fallback."""
    result = match_drug(db_path, "리도펜연질캡슐")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score >= 70


def test_match_returns_none_for_unknown(db_path):
    result = match_drug(db_path, "존재하지않는약물XYZ")
    assert result is None


def test_extract_ingr_codes_single():
    """Single ingredient: '[M040702]이부프로펜'."""
    codes = extract_ingr_codes("[M040702]이부프로펜")
    assert codes == ["M040702"]


def test_extract_ingr_codes_multi():
    """Multi ingredient: pipe-separated."""
    codes = extract_ingr_codes(
        "[M175201]클로르페니라민말레산염|[M146801]디히드로코데인타르타르산염"
    )
    assert codes == ["M175201", "M146801"]


def test_extract_ingr_codes_empty():
    assert extract_ingr_codes("") == []
    assert extract_ingr_codes(None) == []


def test_match_returns_ingr_codes(db_path):
    """DrugMatch should include extracted ingredient codes."""
    result = match_drug(db_path, "코대원정")
    assert result is not None
    assert result.item_seq == "200500001"
    assert len(result.ingr_codes) == 2
    assert "M175201" in result.ingr_codes
    assert "M146801" in result.ingr_codes
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_drug_matcher.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement drug_matcher.py**

Create `src/pillcare/drug_matcher.py`:

```python
"""4-phase drug matcher: EDI → Exact → FTS5 → Fuzzy."""

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz


@dataclass
class DrugMatch:
    item_seq: str
    item_name: str
    main_item_ingr: str
    main_ingr_eng: str
    atc_code: str
    ingr_codes: list[str] = field(default_factory=list)
    score: int = 0


_INGR_CODE_RE = re.compile(r"\[([A-Z]\d+)\]")


def extract_ingr_codes(main_item_ingr: str | None) -> list[str]:
    """Extract ingredient codes from MAIN_ITEM_INGR field.

    Examples:
        '[M040702]이부프로펜' → ['M040702']
        '[M175201]클로르페니라민|[M146801]디히드로코데인' → ['M175201', 'M146801']
    """
    if not main_item_ingr:
        return []
    return _INGR_CODE_RE.findall(main_item_ingr)


def _row_to_match(row: sqlite3.Row, score: int) -> DrugMatch:
    ingr = row["main_item_ingr"] or ""
    return DrugMatch(
        item_seq=row["item_seq"],
        item_name=row["item_name"],
        main_item_ingr=ingr,
        main_ingr_eng=row["main_ingr_eng"] or "",
        atc_code=row["atc_code"] or "",
        ingr_codes=extract_ingr_codes(ingr),
        score=score,
    )


def match_drug(
    db_path: Path,
    query: str,
    edi_code: str | None = None,
    min_score: int = 70,
) -> DrugMatch | None:
    """Match a drug name/code against the drugs table.

    4-phase strategy:
    1. EDI code exact match (if edi_code provided)
    2. Exact item_name match
    3. FTS5 trigram search
    4. rapidfuzz token_set_ratio fallback

    Args:
        db_path: Path to the SQLite DB.
        query: Drug name from prescription history.
        edi_code: Optional EDI (insurance) code for direct match.
        min_score: Minimum fuzzy match score (0-100).

    Returns:
        Best DrugMatch or None if no match above threshold.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Phase 1: EDI code match
    if edi_code:
        row = conn.execute(
            "SELECT * FROM drugs WHERE edi_code = ?", (edi_code,)
        ).fetchone()
        if row:
            result = _row_to_match(row, 100)
            conn.close()
            return result

    # Phase 2: Exact item_name match
    row = conn.execute(
        "SELECT * FROM drugs WHERE item_name = ?", (query,)
    ).fetchone()
    if row:
        result = _row_to_match(row, 100)
        conn.close()
        return result

    # Phase 3: FTS5 trigram search
    try:
        fts_rows = conn.execute(
            "SELECT d.* FROM drugs_fts f JOIN drugs d ON f.rowid = d.rowid "
            "WHERE drugs_fts MATCH ? ORDER BY rank LIMIT 5",
            (query,),
        ).fetchall()
        if fts_rows:
            # Score FTS results with fuzzy matching for ranking
            best_score = 0
            best_row = None
            for r in fts_rows:
                s = fuzz.token_set_ratio(query, r["item_name"])
                if s > best_score:
                    best_score = s
                    best_row = r
            if best_row and best_score >= min_score:
                result = _row_to_match(best_row, best_score)
                conn.close()
                return result
    except sqlite3.OperationalError:
        # FTS5 MATCH can fail on certain query patterns
        pass

    # Phase 4: Full scan with rapidfuzz (fallback)
    rows = conn.execute(
        "SELECT * FROM drugs"
    ).fetchall()
    conn.close()

    best_score = 0
    best_row = None
    for row in rows:
        score = fuzz.token_set_ratio(query, row["item_name"])
        if score > best_score:
            best_score = score
            best_row = row

    # Also try ingredient name matching
    if best_score < min_score:
        for row in rows:
            ingr = row["main_item_ingr"] or ""
            score = fuzz.token_set_ratio(query, ingr)
            if score > best_score:
                best_score = score
                best_row = row

    if best_score >= min_score and best_row is not None:
        return _row_to_match(best_row, best_score)

    return None
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_drug_matcher.py -v
```

Expected: 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/drug_matcher.py tests/test_drug_matcher.py
git commit -m "feat: add drug_matcher — 4-phase matching with EDI, FTS5 trigram, multi-ingredient"
```

---

## Task 7: DUR Checker — Multi-Ingredient N×N Cross-Check

**v2 CHANGE: Each drug can have multiple ingredient codes. All combinations are checked.**

**Files:**
- Create: `src/pillcare/dur_checker.py`
- Create: `tests/test_dur_checker.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_dur_checker.py`:

```python
"""Tests for multi-ingredient N×N DUR cross-check."""

import sqlite3
from pathlib import Path

import pytest

from pillcare.dur_checker import check_dur, DurAlert


@pytest.fixture
def db_with_dur(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE dur_pairs (
            ingr_code_1 TEXT, ingr_name_1 TEXT,
            ingr_code_2 TEXT, ingr_name_2 TEXT,
            reason TEXT, notice_date TEXT,
            PRIMARY KEY (ingr_code_1, ingr_code_2))
    """)
    conn.execute(
        "INSERT INTO dur_pairs VALUES (?,?,?,?,?,?)",
        ("M040702", "이부프로펜", "M04790101", "와파린나트륨", "출혈 위험 증가", "20200101"),
    )
    conn.execute(
        "INSERT INTO dur_pairs VALUES (?,?,?,?,?,?)",
        ("M175201", "클로르페니라민", "M999901", "MAO억제제", "혈압 위기", "20200301"),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def drug_list_multi_ingr():
    """Drug list where 코대원정 has 2 ingredients."""
    return [
        {
            "drug_name": "펠루비정",
            "department": "가정의학과",
            "ingr_codes": ["M040702"],
        },
        {
            "drug_name": "쿠마딘정",
            "department": "내과",
            "ingr_codes": ["M04790101"],
        },
        {
            "drug_name": "코대원정",
            "department": "가정의학과",
            "ingr_codes": ["M175201", "M146801"],  # multi-ingredient
        },
        {
            "drug_name": "MAO약",
            "department": "정신과",
            "ingr_codes": ["M999901"],
        },
    ]


def test_check_dur_finds_single_ingr_pair(db_with_dur, drug_list_multi_ingr):
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    reasons = {a.reason for a in alerts}
    assert "출혈 위험 증가" in reasons


def test_check_dur_finds_multi_ingr_pair(db_with_dur, drug_list_multi_ingr):
    """코대원정's M175201 (클로르페니라민) × MAO약's M999901 should trigger."""
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    reasons = {a.reason for a in alerts}
    assert "혈압 위기" in reasons


def test_check_dur_detects_cross_clinic(db_with_dur, drug_list_multi_ingr):
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    ibu_warf = next(a for a in alerts if "출혈" in a.reason)
    assert ibu_warf.cross_clinic is True  # 가정의학과 × 내과


def test_check_dur_multi_ingr_alert_shows_correct_names(db_with_dur, drug_list_multi_ingr):
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    mao_alert = next(a for a in alerts if "혈압" in a.reason)
    assert mao_alert.drug_name_1 == "코대원정"
    assert mao_alert.drug_name_2 == "MAO약"
    assert mao_alert.ingr_code_1 == "M175201"


def test_check_dur_no_alerts_for_safe_drugs(db_with_dur):
    safe_drugs = [
        {"drug_name": "알게텍정", "department": "가정의학과", "ingr_codes": ["M254901"]},
        {"drug_name": "안전한약", "department": "내과", "ingr_codes": ["M999999"]},
    ]
    alerts = check_dur(db_with_dur, safe_drugs)
    assert len(alerts) == 0


def test_check_dur_total_count(db_with_dur, drug_list_multi_ingr):
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    # 펠루비×쿠마딘 (M040702×M04790101) + 코대원×MAO (M175201×M999901) = 2
    assert len(alerts) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_dur_checker.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement dur_checker.py**

Create `src/pillcare/dur_checker.py`:

```python
"""Multi-ingredient N×N DUR cross-check."""

import sqlite3
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path


@dataclass
class DurAlert:
    drug_name_1: str
    department_1: str
    ingr_code_1: str
    ingr_name_1: str
    drug_name_2: str
    department_2: str
    ingr_code_2: str
    ingr_name_2: str
    reason: str
    cross_clinic: bool


def check_dur(
    db_path: Path,
    drugs: list[dict],
) -> list[DurAlert]:
    """Check all drug pairs for DUR contraindications.

    Each drug in the list may have multiple ingredient codes.
    All cross-ingredient combinations are checked.

    Args:
        db_path: Path to SQLite DB with dur_pairs table.
        drugs: List of dicts with keys: drug_name, department, ingr_codes (list[str]).

    Returns:
        List of DurAlert for each contraindicated pair found.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Load all DUR pairs into a lookup dict for O(1) access
    dur_rows = conn.execute("SELECT * FROM dur_pairs").fetchall()
    conn.close()

    dur_lookup: dict[tuple[str, str], dict] = {}
    for row in dur_rows:
        key_1 = (row["ingr_code_1"], row["ingr_code_2"])
        key_2 = (row["ingr_code_2"], row["ingr_code_1"])
        entry = dict(row)
        dur_lookup[key_1] = entry
        dur_lookup[key_2] = entry

    alerts = []
    seen: set[tuple[str, str]] = set()  # Deduplicate by (drug_name_1, drug_name_2)

    for d1, d2 in combinations(drugs, 2):
        for code_a in d1["ingr_codes"]:
            for code_b in d2["ingr_codes"]:
                key = (code_a, code_b)
                if key not in dur_lookup:
                    continue

                dedup_key = (d1["drug_name"], d2["drug_name"], code_a, code_b)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                row = dur_lookup[key]
                # Determine which name corresponds to which code
                if row["ingr_code_1"] == code_a:
                    name_a, name_b = row["ingr_name_1"], row["ingr_name_2"]
                else:
                    name_a, name_b = row["ingr_name_2"], row["ingr_name_1"]

                alerts.append(DurAlert(
                    drug_name_1=d1["drug_name"],
                    department_1=d1["department"],
                    ingr_code_1=code_a,
                    ingr_name_1=name_a,
                    drug_name_2=d2["drug_name"],
                    department_2=d2["department"],
                    ingr_code_2=code_b,
                    ingr_name_2=name_b,
                    reason=row["reason"],
                    cross_clinic=(d1["department"] != d2["department"]),
                ))

    return alerts
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_dur_checker.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/dur_checker.py tests/test_dur_checker.py
git commit -m "feat: add dur_checker — multi-ingredient N×N DUR cross-check"
```

---

## Task 8: Drug Info Collector

**Same as v1.** See `2026-04-15-medication-guidance-pipeline.md` Task 8.

**Files:**
- Create: `src/pillcare/drug_info.py`
- Create: `tests/test_drug_info.py`

No changes from v1.

---

## Task 9: Pydantic Schemas — Pipeline State & Output Models

**NEW in v2.** Shared data models used across all pipeline nodes.

**Files:**
- Create: `src/pillcare/schemas.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_schemas.py`:

```python
"""Tests for Pydantic schemas."""

import pytest

from pillcare.schemas import (
    PipelineState,
    MatchedDrug,
    DurAlertModel,
    DrugGuidance,
    GuidanceSection,
    GuidanceResult,
    SourceTier,
)


def test_matched_drug_from_match_result():
    drug = MatchedDrug(
        item_seq="199701416",
        drug_name="펠루비정",
        item_name="펠루비정(페루비프로펜)",
        department="가정의학과",
        ingr_codes=["M040702"],
        edi_code="671803380",
        match_score=100,
    )
    assert drug.item_seq == "199701416"
    assert len(drug.ingr_codes) == 1


def test_guidance_section_requires_source_tier():
    section = GuidanceSection(
        title="효능효과",
        content="이 약은 통증에 사용합니다.",
        source_tier=SourceTier.T1_PERMIT,
    )
    assert section.source_tier == SourceTier.T1_PERMIT


def test_drug_guidance_has_10_sections():
    """All 10 복약지도 items can be represented."""
    sections = {
        "명칭": GuidanceSection(title="명칭", content="...", source_tier=SourceTier.T1_PERMIT),
        "성상": GuidanceSection(title="성상", content="...", source_tier=SourceTier.T1_PERMIT),
        "효능효과": GuidanceSection(title="효능효과", content="...", source_tier=SourceTier.T1_EASY),
        "투여의의": GuidanceSection(title="투여의의", content="...", source_tier=SourceTier.T4_AI),
        "용법용량": GuidanceSection(title="용법용량", content="...", source_tier=SourceTier.T1_EASY),
        "저장방법": GuidanceSection(title="저장방법", content="...", source_tier=SourceTier.T1_PERMIT),
        "주의사항": GuidanceSection(title="주의사항", content="...", source_tier=SourceTier.T1_PERMIT),
        "상호작용": GuidanceSection(title="상호작용", content="...", source_tier=SourceTier.T1_DUR),
        "투여종료후": GuidanceSection(title="투여종료후", content="...", source_tier=SourceTier.T4_AI),
        "기타": GuidanceSection(title="기타", content="...", source_tier=SourceTier.T4_AI),
    }
    guidance = DrugGuidance(drug_name="펠루비정", sections=sections)
    assert len(guidance.sections) == 10


def test_pipeline_state_initial():
    state = PipelineState(profile_id="test-user")
    assert state.matched_drugs == []
    assert state.dur_alerts == []
    assert state.errors == []


def test_guidance_result_t4_ratio():
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(drug_name="A", sections={
                "명칭": GuidanceSection(title="명칭", content="...", source_tier=SourceTier.T1_PERMIT),
                "투여의의": GuidanceSection(title="투여의의", content="...", source_tier=SourceTier.T4_AI),
            }),
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    assert result.t4_ratio() == 0.5  # 1 T4 out of 2 total
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_schemas.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement schemas.py**

Create `src/pillcare/schemas.py`:

```python
"""Pydantic models for pipeline state and structured output."""

from enum import Enum

from pydantic import BaseModel, Field


class SourceTier(str, Enum):
    T1_PERMIT = "T1:허가정보"
    T1_EASY = "T1:e약은요"
    T1_DUR = "T1:DUR"
    T4_AI = "T4:AI"


class MatchedDrug(BaseModel):
    item_seq: str
    drug_name: str
    item_name: str
    department: str
    ingr_codes: list[str] = Field(default_factory=list)
    edi_code: str | None = None
    match_score: int = 0


class DurAlertModel(BaseModel):
    drug_name_1: str
    department_1: str
    ingr_code_1: str
    ingr_name_1: str
    drug_name_2: str
    department_2: str
    ingr_code_2: str
    ingr_name_2: str
    reason: str
    cross_clinic: bool


class GuidanceSection(BaseModel):
    title: str
    content: str
    source_tier: SourceTier


class DrugGuidance(BaseModel):
    drug_name: str
    sections: dict[str, GuidanceSection] = Field(default_factory=dict)


class DurWarning(BaseModel):
    drug_1: str
    drug_2: str
    reason: str
    cross_clinic: bool


class GuidanceResult(BaseModel):
    drug_guidances: list[DrugGuidance] = Field(default_factory=list)
    dur_warnings: list[DurWarning] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
    warning_labels: list[str] = Field(default_factory=list)

    def t4_ratio(self) -> float:
        """Calculate the ratio of T4 (AI-generated) sections."""
        total = 0
        t4_count = 0
        for dg in self.drug_guidances:
            for section in dg.sections.values():
                total += 1
                if section.source_tier == SourceTier.T4_AI:
                    t4_count += 1
        return t4_count / total if total > 0 else 0.0


# Note: LangGraph uses GraphState (TypedDict) defined in pipeline.py
# as the runtime state container. This Pydantic model is kept as a
# serializable subset for API/persistence use cases (no _llm, no _retry_count).

class PipelineState(BaseModel):
    """Serializable pipeline state (subset of GraphState, no internal fields)."""

    profile_id: str
    raw_records: list[dict] = Field(default_factory=list)
    matched_drugs: list[MatchedDrug] = Field(default_factory=list)
    dur_alerts: list[DurAlertModel] = Field(default_factory=list)
    drug_infos: list[dict] = Field(default_factory=list)
    guidance_result: GuidanceResult | None = None
    errors: list[str] = Field(default_factory=list)
    db_path: str = ""
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_schemas.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/schemas.py tests/test_schemas.py
git commit -m "feat: add schemas — Pydantic models for pipeline state and structured output"
```

---

## Task 10: LangGraph Pipeline — StateGraph + Tools + Prompts

**NEW in v2. This is the core architectural change.** Replaces v1's monolithic `agent.py` with a LangGraph StateGraph.

**Files:**
- Create: `src/pillcare/prompts.py`
- Create: `src/pillcare/tools.py`
- Create: `src/pillcare/pipeline.py`
- Create: `tests/test_pipeline.py`

### Sub-task 10a: Prompts

- [ ] **Step 1: Create prompts.py**

Create `src/pillcare/prompts.py`:

```python
"""System prompts and prompt templates for the LLM generation node."""

SYSTEM_PROMPT = """당신은 복약 정보 안내 AI입니다. 아래 도구로 제공된 의약품 정보를 바탕으로 복약 정보 안내문을 생성합니다.

## 역할 경계
- 절대 금지: 진단, 처방, 용량 변경 권고, 투약 중단 판단
- 모든 경고의 결론: "의사 또는 약사와 상담하십시오"
- 용어: "복약지도" 대신 "복약 정보 안내"를 사용

## 출력 규칙
- 모든 문장에 출처 티어 태그 필수: [T1:허가정보], [T1:DUR], [T1:e약은요], [T4:AI]
- T4 태그 문장은 반드시 "※ AI가 생성한 일반 정보입니다. 정확한 내용은 의사 또는 약사와 상담하십시오." 부기
- DUR 금기는 반드시 최상단에 경고로 표시
- 다기관 처방 교차 금기는 별도 강조

## 복약 정보 체크리스트 (10개 항목)
1) 명칭: [T1] 제품명, 성분명, 제조사, 제형, 함량
2) 성상: [T1] 외형 설명
3) 효능효과: [T1] 허가사항 기반
4) 투여의의: [T4] 약이 필요한 이유 — 효능효과 + ATC 분류로 맥락 보충
5) 용법용량: [T1] 사용시간, 횟수, 용량
6) 저장방법: [T1] 보관조건, 유효기간
7) 주의/부작용: [T1] 흔한 이상반응 + 중대 이상반응
8) 상호작용: [T1:DUR] 병용금기 + [T1:허가정보] 상호작용 섹션
9) 투여종료후: [T4] 해당 시
10) 기타: [T1/T4] 복용 누락, 일반 주의 등

## 금칙 어휘
절대 사용하지 말 것: 진단합니다, 처방합니다, 투약판단, 용량을 조절, 복용을 중단하세요, 복약지도"""

DRUG_GUIDANCE_TEMPLATE = """아래 약물에 대해 복약 정보 안내 10개 항목을 작성하십시오.

## 약물 정보
제품명: {item_name}
성분명: {main_item_ingr}
영문성분명: {main_ingr_eng}
제조사: {entp_name}
ATC코드: {atc_code}
전문/일반: {etc_otc_code}
성상: {chart}
함량: {total_content}
보관방법: {storage_method}
유효기간: {valid_term}

## 효능효과 (T1:허가정보)
{ee_text}

## 용법용량 (T1:허가정보)
{ud_text}

## 사용상주의사항 섹션 (T1:허가정보)
{nb_sections}

## e약은요 환자용 텍스트 (T1:e약은요)
{easy_text}

## DUR 병용금기 경고 (T1:DUR)
{dur_alerts}

submit_guidance 도구를 사용하여 구조화된 결과를 제출하십시오."""

BANNED_WORDS = [
    "진단합니다", "처방합니다", "투약판단",
    "용량을 조절", "복용을 중단하세요", "복약지도",
]
```

- [ ] **Step 2: Commit prompts**

```bash
git add src/pillcare/prompts.py
git commit -m "feat: add prompts — system prompt and templates for LLM node"
```

### Sub-task 10b: Tools

- [ ] **Step 3: Create tools.py**

Create `src/pillcare/tools.py`:

```python
"""Tool node functions for LangGraph pipeline.

Deterministic nodes that process PipelineState. Each function takes the
current state dict and returns a partial state update.
"""

from dataclasses import asdict
from pathlib import Path

from pillcare.drug_info import get_drug_info
from pillcare.drug_matcher import match_drug
from pillcare.dur_checker import check_dur
from pillcare.schemas import DurAlertModel, MatchedDrug, PipelineState


def match_drugs_node(state: dict) -> dict:
    """Match all drug names from history records to DB entries.

    Input state keys: raw_records, db_path
    Output state keys: matched_drugs, errors
    """
    db_path = Path(state["db_path"])
    matched: list[dict] = []
    errors: list[str] = list(state.get("errors", []))

    for rec in state["raw_records"]:
        result = match_drug(
            db_path,
            rec["drug_name"],
            edi_code=rec.get("drug_code"),
        )
        if result:
            matched.append(MatchedDrug(
                item_seq=result.item_seq,
                drug_name=rec["drug_name"],
                item_name=result.item_name,
                department=rec.get("department", "미지정"),
                ingr_codes=result.ingr_codes,
                edi_code=rec.get("drug_code"),
                match_score=result.score,
            ).model_dump())
        else:
            errors.append(f"매칭 실패: {rec['drug_name']}")

    return {"matched_drugs": matched, "errors": errors}


def check_dur_node(state: dict) -> dict:
    """Run N×N DUR cross-check on matched drugs.

    Input state keys: matched_drugs, db_path
    Output state keys: dur_alerts
    """
    db_path = Path(state["db_path"])
    drugs_for_check = [
        {
            "drug_name": d["drug_name"],
            "department": d["department"],
            "ingr_codes": d["ingr_codes"],
        }
        for d in state["matched_drugs"]
    ]

    alerts = check_dur(db_path, drugs_for_check)
    return {
        "dur_alerts": [
            DurAlertModel(
                drug_name_1=a.drug_name_1,
                department_1=a.department_1,
                ingr_code_1=a.ingr_code_1,
                ingr_name_1=a.ingr_name_1,
                drug_name_2=a.drug_name_2,
                department_2=a.department_2,
                ingr_code_2=a.ingr_code_2,
                ingr_name_2=a.ingr_name_2,
                reason=a.reason,
                cross_clinic=a.cross_clinic,
            ).model_dump()
            for a in alerts
        ]
    }


def collect_drug_info_node(state: dict) -> dict:
    """Collect full drug info for all matched drugs.

    Input state keys: matched_drugs, db_path
    Output state keys: drug_infos
    """
    db_path = Path(state["db_path"])
    infos = []
    for drug in state["matched_drugs"]:
        info = get_drug_info(db_path, drug["item_seq"])
        if info:
            infos.append(asdict(info))
    return {"drug_infos": infos}
```

- [ ] **Step 4: Commit tools**

```bash
git add src/pillcare/tools.py
git commit -m "feat: add tools — deterministic LangGraph node functions"
```

### Sub-task 10c: Pipeline (LangGraph StateGraph)

- [ ] **Step 5: Write failing test for pipeline**

Create `tests/test_pipeline.py`:

```python
"""Tests for LangGraph pipeline with mocked LLM."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pillcare.db_builder import build_db
from pillcare.xml_parser import parse_nb_doc
from pillcare.dur_normalizer import DurPair
from pillcare.schemas import PipelineState, SourceTier
from pillcare.pipeline import build_pipeline, run_pipeline


@pytest.fixture
def full_db(tmp_path: Path, fixtures_dir: Path) -> Path:
    """Build a test DB with drugs, sections, and DUR pairs."""
    with open(fixtures_dir / "small_permit.json", encoding="utf-8") as f:
        permit = json.load(f)
    with open(fixtures_dir / "small_easy.json", encoding="utf-8") as f:
        easy = json.load(f)

    db_path = build_db(tmp_path / "test.db", permit_data=permit, easy_data=easy)

    conn = sqlite3.connect(db_path)
    # Populate drug_sections
    for item in permit:
        nb = item.get("NB_DOC_DATA", "")
        sections = parse_nb_doc(nb)
        for s in sections:
            conn.execute(
                "INSERT OR REPLACE INTO drug_sections VALUES (?,?,?,?,?)",
                (item["ITEM_SEQ"], s.section_type, s.section_title,
                 s.section_text, s.section_order),
            )

    # Add a DUR pair: 이부프로펜 × 클로르페니라민
    conn.execute(
        "INSERT INTO dur_pairs VALUES (?,?,?,?,?,?)",
        ("M040702", "이부프로펜", "M175201", "클로르페니라민말레산염",
         "중추신경 억제 증강", "20200101"),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_records():
    return [
        {"drug_name": "리도펜연질캡슐(이부프로펜)", "drug_code": "649301290",
         "department": "가정의학과"},
        {"drug_name": "코대원정", "drug_code": None,
         "department": "내과"},
    ]


@pytest.fixture
def mock_llm_response():
    """Mock ChatAnthropic response for the generate node."""
    mock = MagicMock()
    # Simulate a tool_use response (submit_guidance call)
    mock_msg = MagicMock()
    mock_msg.content = json.dumps({
        "drug_name": "리도펜연질캡슐(이부프로펜)",
        "sections": {
            "명칭": {"title": "명칭", "content": "[T1:허가정보] 리도펜연질캡슐", "source_tier": "T1:허가정보"},
            "효능효과": {"title": "효능효과", "content": "[T1:e약은요] 감기 발열 통증", "source_tier": "T1:e약은요"},
        },
    })
    mock_msg.tool_calls = []
    mock_msg.type = "ai"
    mock.invoke.return_value = mock_msg
    return mock


def test_deterministic_nodes_run(full_db, sample_records):
    """Test that match → DUR check → collect_info works without LLM."""
    from pillcare.tools import match_drugs_node, check_dur_node, collect_drug_info_node

    state = {
        "db_path": str(full_db),
        "raw_records": sample_records,
        "errors": [],
    }

    # Match drugs
    result = match_drugs_node(state)
    assert len(result["matched_drugs"]) == 2
    state.update(result)

    # DUR check
    result = check_dur_node(state)
    assert len(result["dur_alerts"]) >= 1  # 이부프로펜 × 클로르페니라민
    state.update(result)

    # Collect info
    result = collect_drug_info_node(state)
    assert len(result["drug_infos"]) == 2


def test_dur_cross_clinic_detected(full_db, sample_records):
    """DUR alert should flag cross-clinic (가정의학과 × 내과)."""
    from pillcare.tools import match_drugs_node, check_dur_node

    state = {"db_path": str(full_db), "raw_records": sample_records, "errors": []}
    state.update(match_drugs_node(state))
    result = check_dur_node(state)

    cross_alerts = [a for a in result["dur_alerts"] if a["cross_clinic"]]
    assert len(cross_alerts) >= 1


def test_build_pipeline_returns_graph(full_db):
    """Pipeline graph compiles without error."""
    graph = build_pipeline(db_path=str(full_db), llm=MagicMock())
    assert graph is not None


def test_generate_node_with_mock_llm(full_db, sample_records):
    """Test LLM generate node with mocked ChatAnthropic."""
    from pillcare.tools import match_drugs_node, check_dur_node, collect_drug_info_node
    from pillcare.pipeline import _generate_node

    # Build state through deterministic nodes
    state = {"db_path": str(full_db), "raw_records": sample_records, "errors": []}
    state.update(match_drugs_node(state))
    state.update(check_dur_node(state))
    state.update(collect_drug_info_node(state))

    # Mock LLM that returns structured text with section headers
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = (
        "### 1. 명칭\n[T1:허가정보] 리도펜연질캡슐 (이부프로펜 200mg)\n\n"
        "### 3. 효능효과\n[T1:e약은요] 이 약은 감기 발열 통증에 사용합니다.\n\n"
        "### 7. 주의사항\n[T1:허가정보] 위장출혈 주의. 의사 또는 약사와 상담하십시오.\n"
    )
    mock_llm.invoke.return_value = mock_response
    state["_llm"] = mock_llm
    state["_retry_count"] = 0

    result = _generate_node(state)
    assert result["guidance_result"] is not None
    assert mock_llm.invoke.call_count >= 1  # Called once per drug
```

- [ ] **Step 6: Run test to verify it fails**

```bash
uv run pytest tests/test_pipeline.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 7: Implement pipeline.py**

Create `src/pillcare/pipeline.py`:

```python
"""LangGraph StateGraph pipeline for medication guidance generation."""

import json
from typing import Annotated, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from pillcare.guardrails import post_verify
from pillcare.prompts import DRUG_GUIDANCE_TEMPLATE, SYSTEM_PROMPT
from pillcare.schemas import (
    DrugGuidance,
    DurWarning,
    GuidanceResult,
    GuidanceSection,
    SourceTier,
)
from pillcare.tools import check_dur_node, collect_drug_info_node, match_drugs_node


# --- State type for LangGraph ---
# Using TypedDict so LangGraph preserves all keys across nodes.
# Nodes only need to return the keys they update; un-returned keys persist.

from typing import TypedDict

class GraphState(TypedDict, total=False):
    profile_id: str
    raw_records: list[dict]
    matched_drugs: list[dict]
    dur_alerts: list[dict]
    drug_infos: list[dict]
    guidance_result: dict | None
    errors: list[str]
    db_path: str
    _llm: Any          # LLM instance, set once in initial state
    _retry_count: int   # Incremented by verify node, checked by conditional edge


# --- Node functions ---

def _match_node(state: dict) -> dict:
    return match_drugs_node(state)


def _dur_node(state: dict) -> dict:
    return check_dur_node(state)


def _collect_node(state: dict) -> dict:
    return collect_drug_info_node(state)


def _generate_node(state: dict) -> dict:
    """LLM generation node: generates guidance per drug using Claude.

    Uses the LLM instance stored in state["_llm"].
    Generates guidance for each drug sequentially.
    """
    llm = state["_llm"]
    drug_infos = state.get("drug_infos", [])
    dur_alerts = state.get("dur_alerts", [])

    drug_guidances = []
    dur_warnings = []
    summary_points = []
    warning_labels = []

    # Extract warning labels from drug info (별첨3: NB 경고 섹션 + atpnWarnQesitm)
    for info in drug_infos:
        sections = info.get("sections", {})
        if "경고" in sections:
            warning_labels.append(f"{info.get('item_name', '')}: {sections['경고'][:100]}")
        easy = info.get("easy", {})
        if easy and easy.get("atpn_warn_qesitm"):
            warning_labels.append(f"{info.get('item_name', '')}: {easy['atpn_warn_qesitm'][:100]}")

    # Add DUR alerts to warning labels
    for alert in dur_alerts:
        cross = " [다기관]" if alert["cross_clinic"] else ""
        warning_labels.append(
            f"[병용금기] {alert['drug_name_1']} × {alert['drug_name_2']}: {alert['reason']}{cross}"
        )

    # Build DUR warning models
    for alert in dur_alerts:
        dur_warnings.append(DurWarning(
            drug_1=alert["drug_name_1"],
            drug_2=alert["drug_name_2"],
            reason=alert["reason"],
            cross_clinic=alert["cross_clinic"],
        ))

    # Format DUR alerts text
    dur_text = ""
    if dur_alerts:
        lines = []
        for a in dur_alerts:
            cross = " [다기관 교차 처방]" if a["cross_clinic"] else ""
            lines.append(f"- {a['drug_name_1']} × {a['drug_name_2']}: {a['reason']}{cross}")
        dur_text = "\n".join(lines)

    # Generate per-drug guidance
    for info in drug_infos:
        # Format NB sections
        sections_text = ""
        if info.get("sections"):
            for stype, stext in info["sections"].items():
                sections_text += f"\n### {stype}\n{stext}\n"

        # Format easy text
        easy_text = ""
        if info.get("easy"):
            for key, val in info["easy"].items():
                if val:
                    easy_text += f"{key}: {val}\n"

        # Format EE/UD from XML (plain text extraction)
        ee_text = info.get("ee_doc_data", "") or "(없음)"
        ud_text = info.get("ud_doc_data", "") or "(없음)"

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
            ee_text=ee_text,
            ud_text=ud_text,
            nb_sections=sections_text or "(없음)",
            easy_text=easy_text or "(없음)",
            dur_alerts=dur_text or "(없음)",
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = llm.invoke(messages)
        response_text = response.content if isinstance(response.content, str) else str(response.content)

        # Parse response into DrugGuidance
        guidance = _parse_drug_guidance(info.get("item_name", ""), response_text)
        drug_guidances.append(guidance.model_dump())

        # Extract summary points from response
        if dur_text:
            for a in dur_alerts:
                if a["drug_name_1"] == info.get("item_name") or a["drug_name_2"] == info.get("item_name"):
                    summary_points.append(
                        f"{a['drug_name_1']}과 {a['drug_name_2']}: {a['reason']} [T1:DUR]"
                    )

    result = GuidanceResult(
        drug_guidances=[DrugGuidance(**g) for g in drug_guidances],
        dur_warnings=dur_warnings,
        summary=list(set(summary_points)),
        warning_labels=warning_labels,
    )

    return {"guidance_result": result.model_dump()}


def _parse_drug_guidance(drug_name: str, response_text: str) -> DrugGuidance:
    """Parse LLM response text into a structured DrugGuidance.

    Looks for section headers (### 1. 명칭, ### 2. 성상, etc.) and
    extracts content + source tier tags.
    """
    sections: dict[str, GuidanceSection] = {}
    section_names = [
        "명칭", "성상", "효능효과", "투여의의", "용법용량",
        "저장방법", "주의사항", "상호작용", "투여종료후", "기타",
    ]

    # Simple section extraction by header pattern
    current_section = None
    current_lines: list[str] = []

    import re as _re
    # Match section headers like "### 1. 명칭", "## 명칭", "3) 효능효과" etc.
    _header_re = _re.compile(
        r"^(?:#{1,3}\s*)?(?:\d+[\.\)]\s*)?"
        r"(" + "|".join(_re.escape(s) for s in section_names) + r")"
    )

    for line in response_text.split("\n"):
        # Check if line is a section header (strict regex match)
        matched_section = None
        m = _header_re.match(line.strip())
        if m:
            matched_section = m.group(1)

        if matched_section:
            # Save previous section
            if current_section and current_lines:
                content = "\n".join(current_lines).strip()
                tier = _detect_source_tier(content)
                sections[current_section] = GuidanceSection(
                    title=current_section, content=content, source_tier=tier,
                )
            current_section = matched_section
            current_lines = []
        elif current_section:
            current_lines.append(line)

    # Save last section
    if current_section and current_lines:
        content = "\n".join(current_lines).strip()
        tier = _detect_source_tier(content)
        sections[current_section] = GuidanceSection(
            title=current_section, content=content, source_tier=tier,
        )

    return DrugGuidance(drug_name=drug_name, sections=sections)


def _detect_source_tier(content: str) -> SourceTier:
    """Detect the dominant source tier from content tags."""
    if "[T1:DUR]" in content:
        return SourceTier.T1_DUR
    if "[T1:허가정보]" in content:
        return SourceTier.T1_PERMIT
    if "[T1:e약은요]" in content:
        return SourceTier.T1_EASY
    return SourceTier.T4_AI


def _verify_node(state: dict) -> dict:
    """Post-verification node: checks guardrails and flags issues.
    
    Increments _retry_count so _should_retry can cap retries.
    """
    result_data = state.get("guidance_result")
    retry_count = state.get("_retry_count", 0)

    if not result_data:
        return {
            "errors": state.get("errors", []) + ["생성 결과 없음"],
            "_retry_count": retry_count + 1,
        }

    result = GuidanceResult(**result_data) if isinstance(result_data, dict) else result_data
    dur_alerts = state.get("dur_alerts", [])

    verification_errors = post_verify(result, dur_alerts)
    errors = list(state.get("errors", []))
    errors.extend(verification_errors)

    return {"errors": errors, "_retry_count": retry_count + 1}


def _should_retry(state: dict) -> str:
    """Conditional edge: retry generation if critical errors found."""
    errors = state.get("errors", [])
    critical = [e for e in errors if e.startswith("[CRITICAL]")]
    retry_count = state.get("_retry_count", 0)
    if critical and retry_count < 2:
        return "retry"
    return "done"


# --- Graph builder ---

def build_pipeline(db_path: str, llm: Any) -> Any:
    """Build the LangGraph StateGraph for the medication guidance pipeline.

    Args:
        db_path: Path to the SQLite DB.
        llm: LangChain-compatible LLM instance (e.g., ChatAnthropic).

    Returns:
        Compiled LangGraph graph.
    """
    graph = StateGraph(GraphState)

    graph.add_node("match_drugs", _match_node)
    graph.add_node("check_dur", _dur_node)
    graph.add_node("collect_info", _collect_node)
    graph.add_node("generate", _generate_node)
    graph.add_node("verify", _verify_node)

    graph.set_entry_point("match_drugs")
    graph.add_edge("match_drugs", "check_dur")
    graph.add_edge("check_dur", "collect_info")
    graph.add_edge("collect_info", "generate")
    graph.add_edge("generate", "verify")
    graph.add_conditional_edges("verify", _should_retry, {"retry": "generate", "done": END})

    return graph.compile()


def run_pipeline(
    db_path: str,
    llm: Any,
    records: list[dict],
    profile_id: str = "default",
) -> dict:
    """Run the full pipeline on a list of medication records.

    Args:
        db_path: Path to the SQLite DB.
        llm: LangChain-compatible LLM instance.
        records: Parsed medication history records.
        profile_id: User profile identifier.

    Returns:
        Final pipeline state dict.
    """
    graph = build_pipeline(db_path, llm)

    initial_state = {
        "profile_id": profile_id,
        "raw_records": records,
        "matched_drugs": [],
        "dur_alerts": [],
        "drug_infos": [],
        "guidance_result": None,
        "errors": [],
        "db_path": db_path,
        "_llm": llm,
        "_retry_count": 0,
    }

    return graph.invoke(initial_state)
```

- [ ] **Step 8: Run tests**

```bash
uv run pytest tests/test_pipeline.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 9: Commit**

```bash
git add src/pillcare/pipeline.py src/pillcare/tools.py tests/test_pipeline.py
git commit -m "feat: add LangGraph pipeline — StateGraph with deterministic + LLM nodes"
```

---

## Task 11: Guardrails — Enhanced Post-Verification

**v2 CHANGE: Added source tag validation, T4 ratio limit, mandatory closing phrase check.**

**Files:**
- Create: `src/pillcare/guardrails.py`
- Create: `tests/test_guardrails.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_guardrails.py`:

```python
"""Tests for enhanced post-verification guardrails."""

import pytest

from pillcare.guardrails import (
    verify_dur_coverage,
    filter_banned_words,
    verify_source_tags,
    verify_t4_ratio,
    verify_closing_phrase,
    post_verify,
    BANNED_WORDS,
)
from pillcare.schemas import (
    DrugGuidance,
    GuidanceResult,
    GuidanceSection,
    DurWarning,
    SourceTier,
)


# --- DUR coverage ---

def test_verify_dur_coverage_detects_missing():
    dur_alerts = [
        {"drug_name_1": "펠루비정", "drug_name_2": "록스펜정", "reason": "NSAIDs 병용"},
        {"drug_name_1": "이부프로펜", "drug_name_2": "와파린", "reason": "출혈 위험"},
    ]
    # Only one DUR pair in dur_warnings → the other is missing
    result = GuidanceResult(
        drug_guidances=[],
        dur_warnings=[DurWarning(drug_1="펠루비정", drug_2="록스펜정", reason="NSAIDs 병용", cross_clinic=False)],
        summary=[], warning_labels=[],
    )
    missing = verify_dur_coverage(result, dur_alerts)
    assert len(missing) == 1
    assert "와파린" in missing[0]["drug_name_2"]


def test_verify_dur_coverage_all_present():
    dur_alerts = [
        {"drug_name_1": "펠루비정", "drug_name_2": "록스펜정", "reason": "NSAIDs 병용"},
    ]
    result = GuidanceResult(
        drug_guidances=[],
        dur_warnings=[DurWarning(drug_1="펠루비정", drug_2="록스펜정", reason="NSAIDs 병용", cross_clinic=False)],
        summary=[], warning_labels=[],
    )
    missing = verify_dur_coverage(result, dur_alerts)
    assert len(missing) == 0


# --- Banned words ---

def test_filter_banned_words_removes_violations():
    text = "이 약을 진단합니다. 복약지도를 시행합니다. 의사와 상담하십시오."
    cleaned = filter_banned_words(text)
    for word in BANNED_WORDS:
        assert word not in cleaned


def test_filter_banned_words_preserves_clean_text():
    text = "이 약은 감기에 사용합니다. 의사 또는 약사와 상담하십시오."
    cleaned = filter_banned_words(text)
    assert cleaned == text


# --- Source tag validation ---

def test_verify_source_tags_detects_untagged():
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(drug_name="A", sections={
                "명칭": GuidanceSection(
                    title="명칭",
                    content="리도펜연질캡슐입니다.",  # No [T1:...] tag
                    source_tier=SourceTier.T1_PERMIT,
                ),
            }),
        ],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_source_tags(result)
    assert len(errors) >= 1
    assert "명칭" in errors[0]


def test_verify_source_tags_passes_tagged():
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(drug_name="A", sections={
                "명칭": GuidanceSection(
                    title="명칭",
                    content="[T1:허가정보] 리도펜연질캡슐입니다.",
                    source_tier=SourceTier.T1_PERMIT,
                ),
            }),
        ],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_source_tags(result)
    assert len(errors) == 0


# --- T4 ratio ---

def test_verify_t4_ratio_fails_above_limit():
    sections = {}
    for i, name in enumerate(["명칭", "성상", "효능효과", "투여의의", "용법용량",
                                "저장방법", "주의사항", "상호작용", "투여종료후", "기타"]):
        tier = SourceTier.T4_AI if i >= 5 else SourceTier.T1_PERMIT
        sections[name] = GuidanceSection(title=name, content=f"[{tier.value}] ...", source_tier=tier)

    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections=sections)],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_t4_ratio(result, max_ratio=0.3)
    assert len(errors) >= 1  # 5/10 = 0.5 > 0.3


def test_verify_t4_ratio_passes_within_limit():
    sections = {
        "명칭": GuidanceSection(title="명칭", content="[T1:허가정보] ...", source_tier=SourceTier.T1_PERMIT),
        "투여의의": GuidanceSection(title="투여의의", content="[T4:AI] ...", source_tier=SourceTier.T4_AI),
    }
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections=sections)],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_t4_ratio(result, max_ratio=0.5)
    assert len(errors) == 0


# --- Closing phrase ---

def test_verify_closing_phrase_detects_missing():
    sections = {
        "주의사항": GuidanceSection(
            title="주의사항",
            content="[T1:허가정보] 위장출혈이 나타날 수 있습니다.",
            source_tier=SourceTier.T1_PERMIT,
        ),
    }
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections=sections)],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_closing_phrase(result)
    assert len(errors) >= 1


def test_verify_closing_phrase_passes():
    sections = {
        "주의사항": GuidanceSection(
            title="주의사항",
            content="[T1:허가정보] 위장출혈이 나타날 수 있습니다. 의사 또는 약사와 상담하십시오.",
            source_tier=SourceTier.T1_PERMIT,
        ),
    }
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections=sections)],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_closing_phrase(result)
    assert len(errors) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_guardrails.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement guardrails.py**

Create `src/pillcare/guardrails.py`:

```python
"""Enhanced post-verification guardrails for generated medication guidance."""

import re

from pillcare.prompts import BANNED_WORDS
from pillcare.schemas import GuidanceResult, SourceTier

# Sections that MUST contain closing phrase
_WARNING_SECTIONS = {"주의사항", "상호작용", "투여종료후"}
_CLOSING_PHRASE = "의사 또는 약사와 상담하십시오"
_SOURCE_TAG_RE = re.compile(r"\[T[14]:(허가정보|e약은요|DUR|AI)\]")


def verify_dur_coverage(
    result: "GuidanceResult",
    dur_alerts: list[dict],
) -> list[dict]:
    """Check that all DUR alerts appear in GuidanceResult.dur_warnings.

    Uses structured field matching (drug names in dur_warnings list),
    not free-text search — immune to LLM paraphrasing.
    """
    warned_pairs = set()
    for w in result.dur_warnings:
        warned_pairs.add((w.drug_1, w.drug_2))
        warned_pairs.add((w.drug_2, w.drug_1))

    missing = []
    for alert in dur_alerts:
        name_1 = alert.get("drug_name_1", "")
        name_2 = alert.get("drug_name_2", "")
        if (name_1, name_2) not in warned_pairs:
            missing.append(alert)
    return missing


def filter_banned_words(text: str) -> str:
    """Remove banned words/phrases from generated text."""
    result = text
    for word in BANNED_WORDS:
        result = result.replace(word, "")
    # Clean double spaces
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip()


def verify_source_tags(result: GuidanceResult) -> list[str]:
    """Verify all guidance sections have source tier tags in content."""
    errors = []
    for dg in result.drug_guidances:
        for section_name, section in dg.sections.items():
            if not _SOURCE_TAG_RE.search(section.content):
                errors.append(
                    f"출처 태그 누락: {dg.drug_name} / {section_name}"
                )
    return errors


def verify_t4_ratio(result: GuidanceResult, max_ratio: float = 0.3) -> list[str]:
    """Verify T4 (AI-generated) sections don't exceed max_ratio."""
    ratio = result.t4_ratio()
    if ratio > max_ratio:
        return [
            f"[CRITICAL] T4 비율 초과: {ratio:.1%} (한도: {max_ratio:.0%})"
        ]
    return []


def verify_closing_phrase(result: GuidanceResult) -> list[str]:
    """Verify warning sections end with mandatory closing phrase."""
    errors = []
    for dg in result.drug_guidances:
        for section_name, section in dg.sections.items():
            if section_name in _WARNING_SECTIONS:
                if _CLOSING_PHRASE not in section.content:
                    errors.append(
                        f"필수 종결 문구 누락: {dg.drug_name} / {section_name}"
                    )
    return errors


def post_verify(
    result: GuidanceResult,
    dur_alerts: list[dict],
) -> list[str]:
    """Run all post-verification checks.

    Returns list of error strings. Errors prefixed with [CRITICAL]
    may trigger re-generation.
    """
    errors: list[str] = []

    # 1. DUR coverage check (structured matching, not free-text)
    missing = verify_dur_coverage(result, dur_alerts)
    for m in missing:
        errors.append(
            f"[CRITICAL] DUR 누락: {m['drug_name_1']} × {m['drug_name_2']}"
        )

    # 2. Source tag validation
    errors.extend(verify_source_tags(result))

    # 3. T4 ratio check
    errors.extend(verify_t4_ratio(result))

    # 4. Closing phrase check
    errors.extend(verify_closing_phrase(result))

    return errors
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_guardrails.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/guardrails.py tests/test_guardrails.py
git commit -m "feat: add guardrails — DUR coverage, source tags, T4 ratio, closing phrase"
```

---

## Task 12: Streamlit UI

**Files:**
- Create: `src/pillcare/app.py`

This task is manually smoke-tested, no automated tests.

- [ ] **Step 1: Implement app.py**

Create `src/pillcare/app.py`:

```python
"""Streamlit UI for PillCare medication guidance POC."""

import os
from dataclasses import asdict
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from langchain_anthropic import ChatAnthropic

from pillcare.history_parser import parse_history_xls
from pillcare.pipeline import run_pipeline
from pillcare.schemas import GuidanceResult

DB_PATH = Path("data/pillcare.db")


def main():
    st.set_page_config(page_title="필케어 — 복약 정보 안내", layout="wide")
    st.title("필케어 (PillCare)")
    st.caption("개인 투약이력 기반 grounded 복약 정보 안내 POC")

    if not DB_PATH.exists():
        st.error(f"DB not found at {DB_PATH}. Run `python -m pillcare.db_builder` first.")
        return

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("ANTHROPIC_API_KEY not set in .env")
        return

    # File upload
    uploaded_files = st.file_uploader(
        "심평원 '내가 먹는 약' 투약이력 파일 업로드 (.xls)",
        type=["xls"],
        accept_multiple_files=True,
    )

    password = st.text_input("파일 비밀번호", type="password")

    # Department input per file (BEFORE the analyze button)
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
        # Parse all history files
        with st.spinner("투약이력 파싱 중..."):
            all_records = []
            for uf in uploaded_files:
                dept = departments.get(uf.name, "미지정")
                tmp_path = Path(f"/tmp/{uf.name}")
                tmp_path.write_bytes(uf.read())
                records = parse_history_xls(tmp_path, password=password, department=dept)
                for rec in records:
                    all_records.append({
                        "drug_name": rec.drug_name,
                        "drug_code": rec.drug_code,
                        "department": rec.department,
                    })

        st.success(f"{len(all_records)}개 약물 파싱 완료")

        # Run full LangGraph pipeline
        with st.spinner("파이프라인 실행 중 (매칭 → DUR 체크 → 정보 수집 → 생성 → 검증)..."):
            llm = ChatAnthropic(
                model="claude-sonnet-4-6",
                api_key=api_key,
                max_tokens=4096,
            )
            final_state = run_pipeline(
                db_path=str(DB_PATH),
                llm=llm,
                records=all_records,
            )

        # Display results
        result_data = final_state.get("guidance_result")
        if result_data:
            result = GuidanceResult(**result_data) if isinstance(result_data, dict) else result_data

            # DUR warnings
            if result.dur_warnings:
                st.subheader("병용금기 경고")
                for w in result.dur_warnings:
                    cross = " (다기관 교차)" if w.cross_clinic else ""
                    st.error(f"**{w.drug_1}** x **{w.drug_2}**: {w.reason}{cross}")

            # Detailed guidance
            if result.drug_guidances:
                st.subheader("상세 복약 정보 (별첨1)")
                for dg in result.drug_guidances:
                    with st.expander(dg.drug_name):
                        for section_name, section in dg.sections.items():
                            st.markdown(f"**{section.title}** `{section.source_tier.value}`")
                            st.write(section.content)

            # Summary
            if result.summary:
                st.subheader("핵심 요약 (별첨2)")
                for point in result.summary:
                    st.write(f"- {point}")

        # Errors
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

- [ ] **Step 2: Manual smoke test**

```bash
uv run streamlit run src/pillcare/app.py
```

Open browser, upload sample xls files, verify the full pipeline runs.

- [ ] **Step 3: Commit**

```bash
git add src/pillcare/app.py
git commit -m "feat: add Streamlit UI with LangGraph pipeline integration"
```

---

## Task 13: Full DB Build + End-to-End Smoke Test

**Files:**
- Modify: `src/pillcare/db_builder.py` (add CLI entry point)

- [ ] **Step 1: Add CLI entry point to db_builder.py**

Add to the bottom of `src/pillcare/db_builder.py`:

```python
def build_full_db(data_dir: Path, db_path: Path) -> Path:
    """Build the complete DB from all crawled data files."""
    import json
    from pillcare.xml_parser import parse_nb_doc
    from pillcare.dur_normalizer import normalize_dur

    # Load permit data
    print("Loading drug_permit_detail.json...")
    with open(data_dir / "drug_permit_detail.json", encoding="utf-8") as f:
        permit_data = json.load(f)
    print(f"  {len(permit_data)} items")

    # Load easy data
    print("Loading easy_drug_info.json...")
    with open(data_dir / "easy_drug_info.json", encoding="utf-8") as f:
        easy_data = json.load(f)
    print(f"  {len(easy_data)} items")

    # Build base tables + FTS5 index
    print("Building base tables and FTS5 index...")
    build_db(db_path, permit_data=permit_data, easy_data=easy_data)

    # Parse NB_DOC_DATA → drug_sections
    print("Parsing NB_DOC_DATA XML into sections...")
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM drug_sections")
    count = 0
    parse_errors = 0
    for item in permit_data:
        nb = item.get("NB_DOC_DATA", "")
        if not nb:
            continue
        sections = parse_nb_doc(nb)
        if not sections and nb.strip():
            parse_errors += 1
        for s in sections:
            conn.execute(
                "INSERT OR REPLACE INTO drug_sections VALUES (?,?,?,?,?)",
                (item["ITEM_SEQ"], s.section_type, s.section_title,
                 s.section_text, s.section_order),
            )
            count += 1
    conn.commit()
    print(f"  {count} sections inserted ({parse_errors} parse failures)")

    # Normalize DUR
    dur_csv = data_dir / "한국의약품안전관리원_병용금기약물_20240625.csv"
    if dur_csv.exists():
        print("Normalizing DUR pairs...")
        pairs = normalize_dur(dur_csv, encoding="cp949")
        conn.execute("DELETE FROM dur_pairs")
        for p in pairs:
            conn.execute(
                "INSERT OR REPLACE INTO dur_pairs VALUES (?,?,?,?,?,?)",
                (p.ingr_code_1, p.ingr_name_1, p.ingr_code_2,
                 p.ingr_name_2, p.reason, p.notice_date),
            )
        conn.commit()
        print(f"  {len(pairs)} pairs inserted")

    # Load bundle ATC
    bundle_path = data_dir / "bundle_drug_info.json"
    if bundle_path.exists():
        print("Loading bundle ATC data...")
        with open(bundle_path, encoding="utf-8") as f:
            bundle_data = json.load(f)
        conn.execute("DELETE FROM bundle_atc")
        for item in bundle_data:
            conn.execute(
                "INSERT INTO bundle_atc VALUES (?,?,?,?,?)",
                (
                    item.get("trustItemName"),
                    item.get("trustMainingr"),
                    item.get("trustAtcCode"),
                    item.get("trustHiraMainingrCode"),
                    item.get("trustHiraPrductCode"),
                ),
            )
        conn.commit()
        print(f"  {len(bundle_data)} bundle records inserted")

    conn.close()
    print(f"DB built: {db_path} ({db_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return db_path


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    db_path = data_dir / "pillcare.db"
    build_full_db(data_dir, db_path)
```

- [ ] **Step 2: Run full DB build**

```bash
uv run python -m pillcare.db_builder
```

Expected: DB created at `data/pillcare.db` with all tables populated. Note parse_errors count — this measures NB_DOC_DATA edge cases.

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest -v
```

Expected: All tests PASS.

- [ ] **Step 4: End-to-end smoke test with Streamlit**

```bash
uv run streamlit run src/pillcare/app.py
```

Upload sample xls files, verify full LangGraph pipeline.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/db_builder.py
git commit -m "feat: add full DB build CLI with FTS5 + NB_DOC_DATA parse error tracking"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: All 5 pipeline stages mapped to LangGraph nodes (match → dur_check → collect → generate → verify). 10-item checklist in prompts.py. DUR deterministic + RAG enrichment (Option C) preserved.
- [x] **v1 gap closure — P0**: Agent is now LangGraph StateGraph with per-drug generation (not single prompt). Multi-ingredient DUR checking implemented.
- [x] **v1 gap closure — P1**: EDI code matching (Phase 1) added. FTS5 trigram index added. Structured output via Pydantic schemas. Per-drug sequential generation.
- [x] **v1 gap closure — P2**: Enhanced guardrails (source tags, T4 ratio, closing phrase). Prompt caching ready (ChatAnthropic supports it natively).
- [x] **Placeholder scan**: All code blocks complete. No TBD/TODO.
- [x] **Type consistency**: DrugMatch (drug_matcher) → MatchedDrug (schemas) → DurAlertModel (schemas) → DrugGuidance/GuidanceResult (schemas). Pipeline state uses GraphState TypedDict for LangGraph compatibility.
- [x] **File paths**: All paths match file structure diagram.
- [x] **Unchanged tasks**: Tasks 3, 4, 5, 8 reference v1 explicitly — code is identical.
- [x] **Review fix — CRITICAL #1**: GraphState is now TypedDict with explicit `_llm` and `_retry_count` fields. LangGraph preserves all TypedDict keys across nodes.
- [x] **Review fix — CRITICAL #2**: `_verify_node` now returns `_retry_count + 1` to prevent infinite retry loops.
- [x] **Review fix — CRITICAL #3**: Plan header clarified: POC uses source tier tag parsing; Anthropic Citations API is production path.
- [x] **Review fix — IMPORTANT #4**: `_parse_drug_guidance` uses strict regex `^#{1,3}\s*\d*\.?\s*<section_name>` instead of substring match.
- [x] **Review fix — SUGGEST #7**: Added `test_generate_node_with_mock_llm` test.
- [x] **Review fix — SUGGEST #8**: `warning_labels` now populated from NB 경고 sections + atpnWarnQesitm + DUR alerts.
