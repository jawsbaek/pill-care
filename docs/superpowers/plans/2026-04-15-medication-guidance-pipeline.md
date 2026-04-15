# 복약 정보 안내 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data layer + processing pipeline that takes personal medication history (심평원 "내가 먹는 약") and generates grounded medication guidance per 복약지도 10-item checklist, with DUR deterministic cross-check and source tier tagging.

**Architecture:** SQLite DB built from crawled 식약처 API data (43K drugs) → NB_DOC_DATA XML parser → DUR normalizer → personal history parser → DUR N×N cross-check → drug info collector → Claude agent with tool-use → post-verification. All deterministic stages (1-3, 5) are pure functions with TDD. Stage 4 (Claude agent) uses mocked client for testing.

**Tech Stack:** Python 3.11 · uv · anthropic SDK (Claude Sonnet 4.6 with tool_use) · sqlite3 (stdlib) · rapidfuzz · pytest · streamlit · python-dotenv · msoffcrypto-tool (xls decrypt)

**Relationship to prior POC plan:** This plan supersedes `2026-04-11-pillcare-poc.md` Tasks 2-7. Task 1 (project setup) from the prior plan is reused. Vision/OCR (prior Task 5) is deferred — this plan uses structured xls input instead.

---

## File Structure

```
pill-care/
├── pyproject.toml                     # (Task 1 — project setup)
├── .python-version                    # Python 3.11
├── .env.example                       # ANTHROPIC_API_KEY
├── .gitignore
├── data/
│   ├── drug_permit_detail.json        # 43,250 items (crawled, 2.2GB — gitignored)
│   ├── drug_permit_detail.csv         # 43,250 items (crawled, 48MB)
│   ├── easy_drug_info.json            # 4,711 items (crawled)
│   ├── bundle_drug_info.json          # 16,322 items (crawled)
│   ├── medicines.csv                  # 25,685 items (downloaded)
│   ├── 한국의약품안전관리원_병용금기약물_20240625.csv  # 542,996 rows (downloaded, gitignored)
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
│   ├── db_builder.py                  # Task 2: SQLite DB builder from crawled data
│   ├── xml_parser.py                  # Task 3: NB_DOC_DATA XML → sections
│   ├── dur_normalizer.py              # Task 4: DUR CSV → normalized pairs
│   ├── history_parser.py              # Task 5: xls → medication_history records
│   ├── drug_matcher.py                # Task 6: drug name → item_seq fuzzy match
│   ├── dur_checker.py                 # Task 7: N×N DUR cross-check
│   ├── drug_info.py                   # Task 8: item_seq → structured drug info
│   ├── agent.py                       # Task 9: Claude tool-use agent
│   ├── guardrails.py                  # Task 10: post-verification + safety filters
│   └── app.py                         # Task 11: Streamlit UI
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
    ├── test_agent.py                  # Task 9
    └── test_guardrails.py             # Task 10
```

**Decomposition rationale:**
- Each module maps to one pipeline stage or sub-stage.
- `db_builder` (Task 2) creates the SQLite DB from crawled JSON/CSV — run once.
- `xml_parser` (Task 3) is called by `db_builder` to populate `drug_sections`.
- `dur_normalizer` (Task 4) is called by `db_builder` to populate `dur_pairs`.
- `history_parser` (Task 5) handles xls decrypt + parse — runtime input.
- `drug_matcher` (Task 6) matches parsed drug names to DB — runtime.
- `dur_checker` (Task 7) does N×N cross-check — runtime, deterministic.
- `drug_info` (Task 8) collects all info for matched drugs — runtime.
- `agent` (Task 9) orchestrates Claude tool-use — runtime, LLM.
- `guardrails` (Task 10) post-verifies — runtime, deterministic.
- `app` (Task 11) is Streamlit UI — manual test only.

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
npx ctx7@latest library anthropic "python SDK for Claude with tool_use"
npx ctx7@latest library rapidfuzz "fuzzy string matching Python"
npx ctx7@latest library pytest "Python testing framework"
npx ctx7@latest library streamlit "Python web app framework"
npx ctx7@latest library python-dotenv "load .env files in Python"
npx ctx7@latest library msoffcrypto-tool "decrypt Microsoft Office files"
```

Pick current stable versions compatible with Python 3.11.

- [ ] **Step 4: Install dependencies with pinned verified versions**

```bash
uv add "anthropic==<verified>" "rapidfuzz==<verified>" "python-dotenv==<verified>" "msoffcrypto-tool==<verified>" "openpyxl==<verified>"
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
git commit -m "chore: bootstrap project with uv and verified deps"
```

---

## Task 2: DB Builder — SQLite from Crawled Data

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
  }
]
```

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
    assert cursor.fetchone()[0] == 2

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


def test_build_db_is_idempotent(tmp_path: Path, small_permit, small_easy):
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM drugs")
    assert cursor.fetchone()[0] == 2
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

Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pillcare/db_builder.py tests/test_db_builder.py tests/fixtures/small_permit.json tests/fixtures/small_easy.json
git commit -m "feat: add db_builder — SQLite from crawled permit + e약은요 data"
```

---

## Task 3: XML Parser — NB_DOC_DATA → Sections

**Files:**
- Create: `src/pillcare/xml_parser.py`
- Create: `tests/test_xml_parser.py`
- Create: `tests/fixtures/sample_nb_doc.xml`

- [ ] **Step 1: Create XML fixture**

Create `tests/fixtures/sample_nb_doc.xml`:

```xml
<DOC title="사용상의주의사항" type="NB">
  <SECTION title="">
    <ARTICLE title="1. 경고">
      <PARAGRAPH tagName="p">매일 세 잔 이상 정기적 음주자가 이 약을 복용하면 위장출혈 위험이 있습니다.</PARAGRAPH>
    </ARTICLE>
    <ARTICLE title="2. 다음 환자에는 투여하지 말 것.">
      <PARAGRAPH tagName="p">이 약에 과민증 환자, 위장관궤양 환자</PARAGRAPH>
    </ARTICLE>
    <ARTICLE title="3. 다음 환자에는 신중히 투여할 것.">
      <PARAGRAPH tagName="p">혈액이상 환자, 간장애 환자</PARAGRAPH>
    </ARTICLE>
    <ARTICLE title="4. 이상반응">
      <PARAGRAPH tagName="p">쇽 증상(호흡곤란, 혈압저하), 소화성궤양, 위장출혈</PARAGRAPH>
      <PARAGRAPH tagName="p">두통, 어지러움, 졸음이 나타날 수 있습니다.</PARAGRAPH>
    </ARTICLE>
    <ARTICLE title="5. 상호작용">
      <PARAGRAPH tagName="p">다른 비스테로이드성 소염진통제와 함께 복용하지 마십시오.</PARAGRAPH>
      <PARAGRAPH tagName="p">ACE 저해제, 리튬, 와파린 복용 시 의사와 상의하십시오.</PARAGRAPH>
    </ARTICLE>
    <ARTICLE title="6. 임부 및 수유부에 대한 투여">
      <PARAGRAPH tagName="p">임신 말기 3개월에는 투여하지 마십시오.</PARAGRAPH>
    </ARTICLE>
    <ARTICLE title="7. 소아에 대한 투여">
      <PARAGRAPH tagName="p">만 7세 이하 소아에 대한 안전성이 확립되어 있지 않습니다.</PARAGRAPH>
    </ARTICLE>
    <ARTICLE title="8. 고령자에 대한 투여">
      <PARAGRAPH tagName="p">고령자는 이상반응이 나타나기 쉬우므로 소량부터 투여를 시작합니다.</PARAGRAPH>
    </ARTICLE>
    <ARTICLE title="9. 과량투여시의 처치">
      <PARAGRAPH tagName="p">위세척 등 적절한 처치를 합니다.</PARAGRAPH>
    </ARTICLE>
    <ARTICLE title="10. 일반적 주의">
      <PARAGRAPH tagName="p">장기 복용 시 정기적으로 혈액검사를 실시합니다.</PARAGRAPH>
    </ARTICLE>
  </SECTION>
</DOC>
```

- [ ] **Step 2: Write failing test**

Create `tests/test_xml_parser.py`:

```python
"""Tests for NB_DOC_DATA XML parser."""

from pathlib import Path

import pytest

from pillcare.xml_parser import parse_nb_doc, Section


@pytest.fixture
def sample_xml(fixtures_dir: Path) -> str:
    return (fixtures_dir / "sample_nb_doc.xml").read_text(encoding="utf-8")


def test_parse_nb_doc_returns_sections(sample_xml):
    sections = parse_nb_doc(sample_xml)
    assert len(sections) >= 8
    types = {s.section_type for s in sections}
    assert "금기" in types
    assert "상호작용" in types
    assert "이상반응" in types


def test_section_type_mapping(sample_xml):
    sections = parse_nb_doc(sample_xml)
    by_type = {s.section_type: s for s in sections}
    assert "위장관궤양" in by_type["금기"].section_text
    assert "비스테로이드" in by_type["상호작용"].section_text
    assert "임신" in by_type["임부수유"].section_text


def test_section_preserves_multiple_paragraphs(sample_xml):
    sections = parse_nb_doc(sample_xml)
    interaction = next(s for s in sections if s.section_type == "상호작용")
    assert "ACE" in interaction.section_text
    assert "비스테로이드" in interaction.section_text


def test_section_order(sample_xml):
    sections = parse_nb_doc(sample_xml)
    orders = [s.section_order for s in sections]
    assert orders == sorted(orders)


def test_parse_empty_xml():
    sections = parse_nb_doc("")
    assert sections == []


def test_parse_none():
    sections = parse_nb_doc(None)
    assert sections == []
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_xml_parser.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement xml_parser.py**

Create `src/pillcare/xml_parser.py`:

```python
"""Parse NB_DOC_DATA XML into structured sections."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class Section:
    section_type: str
    section_title: str
    section_text: str
    section_order: int


_TITLE_TO_TYPE: list[tuple[str, str]] = [
    ("투여하지 말 것", "금기"),
    ("복용하지 말 것", "금기"),
    ("신중히 투여", "신중투여"),
    ("상의할 것", "신중투여"),
    ("이상반응", "이상반응"),
    ("부작용", "이상반응"),
    ("상호작용", "상호작용"),
    ("임부", "임부수유"),
    ("수유부", "임부수유"),
    ("소아", "소아"),
    ("고령자", "고령자"),
    ("과량투여", "과량투여"),
    ("일반적 주의", "일반주의"),
    ("복용시 주의", "일반주의"),
    ("보관", "보관주의"),
    ("취급", "보관주의"),
    ("경고", "경고"),
]


def _classify_title(title: str) -> str:
    for keyword, section_type in _TITLE_TO_TYPE:
        if keyword in title:
            return section_type
    return "기타"


def _extract_text(article: ET.Element) -> str:
    paragraphs = []
    for para in article.iter("PARAGRAPH"):
        text = para.text or ""
        tail = para.tail or ""
        full = (text + tail).strip()
        if full:
            paragraphs.append(full)
    if not paragraphs:
        # Fallback: get all text content
        text = ET.tostring(article, encoding="unicode", method="text").strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def parse_nb_doc(xml_str: str | None) -> list[Section]:
    """Parse NB_DOC_DATA XML string into a list of Section objects.

    Args:
        xml_str: Raw XML string from 허가정보 NB_DOC_DATA field.

    Returns:
        List of Section objects, sorted by section_order.
    """
    if not xml_str:
        return []

    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []

    sections = []
    order = 0
    for article in root.iter("ARTICLE"):
        title = article.get("title", "").strip()
        if not title:
            continue
        text = _extract_text(article)
        if not text:
            continue
        # Strip leading numbering: "1. ", "2. " etc.
        clean_title = re.sub(r"^\d+\.\s*", "", title)
        section_type = _classify_title(clean_title)
        sections.append(Section(
            section_type=section_type,
            section_title=title,
            section_text=text,
            section_order=order,
        ))
        order += 1

    return sections
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_xml_parser.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pillcare/xml_parser.py tests/test_xml_parser.py tests/fixtures/sample_nb_doc.xml
git commit -m "feat: add xml_parser — NB_DOC_DATA XML to structured sections"
```

---

## Task 4: DUR Normalizer — CSV → Normalized Pairs

**Files:**
- Create: `src/pillcare/dur_normalizer.py`
- Create: `tests/test_dur_normalizer.py`
- Create: `tests/fixtures/small_dur.csv`

- [ ] **Step 1: Create DUR fixture**

Create `tests/fixtures/small_dur.csv` (cp949 encoding, matching real data format):

```python
# Generate this file programmatically in the test setup since it needs cp949:
```

Actually, create it as UTF-8 for test simplicity. Create `tests/fixtures/small_dur.csv`:

```csv
성분명1,성분코드1,제품코드1,제품명1,업체명1,급여구분1,성분명2,성분코드2,제품코드2,제품명2,업체명2,급여구분2,공고번호,공고일자,금기사유
이부프로펜,M040702,199701416,리도펜연질캡슐,메디카코리아,급여,와파린나트륨,M04790101,200000001,쿠마딘정,제약사A,급여,2020-001,20200101,출혈 위험 증가
이부프로펜,M040702,199701417,이부펜정,제약사B,급여,와파린나트륨,M04790101,200000002,와파린정,제약사C,급여,2020-001,20200101,출혈 위험 증가
이부프로펜,M040702,199701416,리도펜연질캡슐,메디카코리아,급여,리튬카보네이트,M068301,200000003,리튬정,제약사D,급여,2020-002,20200301,리튬 혈중농도 상승
메트포르민염산염,M09030101,200100001,글루코파지정,한국MSD,급여,요오드화조영제,M99901,200100002,조영제X,제약사E,급여,2020-003,20200601,기능적 신부전에 의해 유산 산성증 촉진
메트포르민염산염,M09030101,200100003,다이아벡스정,대웅제약,급여,요오드화조영제,M99901,200100004,조영제Y,제약사F,급여,2020-003,20200601,기능성 신부전에 의한 유산산성증 촉진
```

- [ ] **Step 2: Write failing test**

Create `tests/test_dur_normalizer.py`:

```python
"""Tests for DUR CSV normalizer."""

from pathlib import Path

import pytest

from pillcare.dur_normalizer import normalize_dur, DurPair


@pytest.fixture
def small_dur_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "small_dur.csv"


def test_normalize_dur_deduplicates_to_ingredient_level(small_dur_path):
    pairs = normalize_dur(small_dur_path, encoding="utf-8")
    # 이부프로펜×와파린: 2 product rows → 1 pair
    # 이부프로펜×리튬: 1 pair
    # 메트포르민×요오드화조영제: 2 product rows → 1 pair
    assert len(pairs) == 3


def test_normalize_dur_merges_reason_text_variants(small_dur_path):
    pairs = normalize_dur(small_dur_path, encoding="utf-8")
    met_pair = next(
        p for p in pairs
        if "메트포르민" in p.ingr_name_1 or "메트포르민" in p.ingr_name_2
    )
    # "유산 산성증" and "유산산성증" variants should be merged
    assert "유산" in met_pair.reason
    assert met_pair.reason.count("유산") == 1  # not duplicated


def test_normalize_dur_pair_fields(small_dur_path):
    pairs = normalize_dur(small_dur_path, encoding="utf-8")
    ibu_warf = next(
        p for p in pairs
        if "이부프로펜" in p.ingr_name_1 and "와파린" in p.ingr_name_2
    )
    assert ibu_warf.ingr_code_1 == "M040702"
    assert ibu_warf.ingr_code_2 == "M04790101"
    assert "출혈" in ibu_warf.reason


def test_normalize_dur_bidirectional_lookup(small_dur_path):
    pairs = normalize_dur(small_dur_path, encoding="utf-8")
    # Should be findable regardless of order
    codes = set()
    for p in pairs:
        codes.add((p.ingr_code_1, p.ingr_code_2))
        codes.add((p.ingr_code_2, p.ingr_code_1))
    assert ("M040702", "M04790101") in codes
    assert ("M04790101", "M040702") in codes
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_dur_normalizer.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement dur_normalizer.py**

Create `src/pillcare/dur_normalizer.py`:

```python
"""Normalize DUR CSV (product-level 542K rows) to ingredient-pair level."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DurPair:
    ingr_code_1: str
    ingr_name_1: str
    ingr_code_2: str
    ingr_name_2: str
    reason: str
    notice_date: str


def _normalize_reason(reason: str) -> str:
    """Normalize spacing/wording variants in 금기사유."""
    text = reason.strip()
    # Normalize common variants
    text = re.sub(r"기능[적성]\s*신부전에\s*의한?\s*유산\s*산성증", "기능적 신부전에 의한 유산산성증", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _make_key(code_1: str, code_2: str) -> tuple[str, str]:
    """Ensure consistent ordering for dedup."""
    return (min(code_1, code_2), max(code_1, code_2))


def normalize_dur(csv_path: Path, encoding: str = "cp949") -> list[DurPair]:
    """Read DUR CSV and normalize to ingredient-pair level.

    Args:
        csv_path: Path to 한국의약품안전관리원_병용금기약물 CSV.
        encoding: File encoding (cp949 for original, utf-8 for test fixtures).

    Returns:
        Deduplicated list of DurPair at ingredient level.
    """
    pair_map: dict[tuple[str, str], DurPair] = {}

    with open(csv_path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_1 = row["성분코드1"].strip()
            code_2 = row["성분코드2"].strip()
            if not code_1 or not code_2:
                continue

            key = _make_key(code_1, code_2)
            reason = _normalize_reason(row.get("금기사유", ""))

            if key not in pair_map:
                # Use consistent ordering matching the key
                if key[0] == code_1:
                    pair_map[key] = DurPair(
                        ingr_code_1=code_1,
                        ingr_name_1=row["성분명1"].strip(),
                        ingr_code_2=code_2,
                        ingr_name_2=row["성분명2"].strip(),
                        reason=reason,
                        notice_date=row.get("공고일자", "").strip(),
                    )
                else:
                    pair_map[key] = DurPair(
                        ingr_code_1=code_2,
                        ingr_name_1=row["성분명2"].strip(),
                        ingr_code_2=code_1,
                        ingr_name_2=row["성분명1"].strip(),
                        reason=reason,
                        notice_date=row.get("공고일자", "").strip(),
                    )

    return list(pair_map.values())
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_dur_normalizer.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pillcare/dur_normalizer.py tests/test_dur_normalizer.py tests/fixtures/small_dur.csv
git commit -m "feat: add dur_normalizer — DUR CSV to ingredient-pair level"
```

---

## Task 5: History Parser — XLS → Medication Records

**Files:**
- Create: `src/pillcare/history_parser.py`
- Create: `tests/test_history_parser.py`
- Create: `tests/fixtures/sample_history.json`

- [ ] **Step 1: Create fixture**

Create `tests/fixtures/sample_history.json` (pre-parsed format, for tests that don't need xls decryption):

```json
[
  {
    "seq": 1, "drug_name": "알게텍정", "drug_class": "제산제",
    "ingredient": "almagate", "drug_code": "057600010", "unit": "1정",
    "dose_per_time": 1.0, "times_per_day": 3, "duration_days": 3,
    "safety_letter": "N", "antithrombotic": "N", "department": "가정의학과"
  },
  {
    "seq": 2, "drug_name": "펠루비정", "drug_class": "해열·진통·소염제",
    "ingredient": "pelubiprofen", "drug_code": "671803380", "unit": "1정",
    "dose_per_time": 1.0, "times_per_day": 3, "duration_days": 3,
    "safety_letter": "N", "antithrombotic": "N", "department": "가정의학과"
  },
  {
    "seq": 1, "drug_name": "록스펜정", "drug_class": "해열·진통·소염제",
    "ingredient": "loxoprofen sodium hydrate (as loxoprofen sodium)",
    "drug_code": "648500640", "unit": "1정",
    "dose_per_time": 1.0, "times_per_day": 3, "duration_days": 3,
    "safety_letter": "N", "antithrombotic": "N", "department": "안과"
  }
]
```

- [ ] **Step 2: Write failing test**

Create `tests/test_history_parser.py`:

```python
"""Tests for medication history parser."""

import json
from pathlib import Path

import pytest

from pillcare.history_parser import parse_history_xls, MedRecord


def test_parse_real_xls_family_medicine():
    """Integration test with real encrypted sample file."""
    path = Path("person_sample/개인투약이력 가정의학과.xls")
    if not path.exists():
        pytest.skip("Sample file not available")

    records = parse_history_xls(path, password="19971207", department="가정의학과")
    assert len(records) == 5
    assert records[0].drug_name == "알게텍정"
    assert records[0].ingredient == "almagate"
    assert records[0].department == "가정의학과"
    assert records[0].drug_code == "057600010"


def test_parse_real_xls_ophthalmology():
    path = Path("person_sample/개인투약이력 안과.xls")
    if not path.exists():
        pytest.skip("Sample file not available")

    records = parse_history_xls(path, password="19971207", department="안과")
    assert len(records) == 6
    assert records[4].drug_name == "록스펜정"
    assert "loxoprofen" in records[4].ingredient


def test_med_record_fields():
    """Test MedRecord dataclass from fixture data."""
    rec = MedRecord(
        seq=1, drug_name="알게텍정", drug_class="제산제",
        ingredient="almagate", drug_code="057600010", unit="1정",
        dose_per_time=1.0, times_per_day=3, duration_days=3,
        safety_letter="N", antithrombotic="N", department="가정의학과",
    )
    assert rec.drug_name == "알게텍정"
    assert rec.times_per_day == 3
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_history_parser.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement history_parser.py**

Create `src/pillcare/history_parser.py`:

```python
"""Parse 심평원 '내가 먹는 약' encrypted XLS into MedRecord list."""

import io
from dataclasses import dataclass
from pathlib import Path

import msoffcrypto
import openpyxl


@dataclass
class MedRecord:
    seq: int
    drug_name: str
    drug_class: str
    ingredient: str
    drug_code: str
    unit: str
    dose_per_time: float
    times_per_day: int
    duration_days: int
    safety_letter: str
    antithrombotic: str
    department: str


def parse_history_xls(
    path: Path,
    password: str,
    department: str,
) -> list[MedRecord]:
    """Decrypt and parse a 심평원 개인투약이력 XLS file.

    Args:
        path: Path to the encrypted .xls file.
        password: Decryption password.
        department: 진료과 label to attach (e.g. "가정의학과").

    Returns:
        List of MedRecord, one per drug row.
    """
    with open(path, "rb") as f:
        office_file = msoffcrypto.OfficeFile(f)
        decrypted = io.BytesIO()
        office_file.load_key(password=password)
        office_file.decrypt(decrypted)
        decrypted.seek(0)

    wb = openpyxl.load_workbook(decrypted, read_only=True)
    ws = wb.active

    # Find the header row (contains "번호", "제품명", ...)
    header_row_idx = None
    headers = []
    for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        cells = [str(c).strip() if c else "" for c in row]
        if "번호" in cells and "제품명" in cells:
            header_row_idx = idx
            headers = cells
            break

    if header_row_idx is None:
        wb.close()
        return []

    col_map = {name: i for i, name in enumerate(headers)}
    records = []

    for row in ws.iter_rows(min_row=header_row_idx + 1, values_only=True):
        cells = [c for c in row]
        seq_val = cells[col_map["번호"]]
        if seq_val is None:
            continue
        try:
            seq = int(seq_val)
        except (ValueError, TypeError):
            continue

        def g(col_name: str) -> str:
            idx = col_map.get(col_name)
            if idx is None or idx >= len(cells):
                return ""
            return str(cells[idx]).strip() if cells[idx] is not None else ""

        def gf(col_name: str) -> float:
            v = g(col_name)
            try:
                return float(v)
            except (ValueError, TypeError):
                return 0.0

        def gi(col_name: str) -> int:
            v = g(col_name)
            try:
                return int(float(v))
            except (ValueError, TypeError):
                return 0

        records.append(MedRecord(
            seq=seq,
            drug_name=g("제품명"),
            drug_class=g("약효분류"),
            ingredient=g("성분명"),
            drug_code=g("약품코드"),
            unit=g("단위"),
            dose_per_time=gf("1회 투약량"),
            times_per_day=gi("1일 투여횟수"),
            duration_days=gi("총 투약일수"),
            safety_letter=g("안전성 서한(속보)"),
            antithrombotic=g("항혈전제 여부"),
            department=department,
        ))

    wb.close()
    return records
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_history_parser.py -v
```

Expected: 3 tests PASS (2 integration tests with real files + 1 unit test).

- [ ] **Step 6: Commit**

```bash
git add src/pillcare/history_parser.py tests/test_history_parser.py tests/fixtures/sample_history.json
git commit -m "feat: add history_parser — decrypt and parse 심평원 투약이력 xls"
```

---

## Task 6: Drug Matcher — Drug Name → item_seq

**Files:**
- Create: `src/pillcare/drug_matcher.py`
- Create: `tests/test_drug_matcher.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_drug_matcher.py`:

```python
"""Tests for drug name → item_seq matcher."""

import json
import sqlite3
from pathlib import Path

import pytest

from pillcare.db_builder import build_db
from pillcare.drug_matcher import match_drug, DrugMatch


@pytest.fixture
def db_path(tmp_path: Path, fixtures_dir: Path) -> Path:
    with open(fixtures_dir / "small_permit.json", encoding="utf-8") as f:
        permit = json.load(f)
    with open(fixtures_dir / "small_easy.json", encoding="utf-8") as f:
        easy = json.load(f)
    return build_db(tmp_path / "test.db", permit_data=permit, easy_data=easy)


def test_match_exact_name(db_path):
    result = match_drug(db_path, "리도펜연질캡슐(이부프로펜)")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score == 100


def test_match_partial_name(db_path):
    result = match_drug(db_path, "리도펜연질캡슐")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score >= 70


def test_match_returns_none_for_unknown(db_path):
    result = match_drug(db_path, "존재하지않는약물XYZ")
    assert result is None


def test_match_by_ingredient_fallback(db_path):
    result = match_drug(db_path, "이부프로펜 200mg 캡슐")
    # Should find via ingredient matching
    assert result is not None
    assert result.item_seq == "199701416"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_drug_matcher.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement drug_matcher.py**

Create `src/pillcare/drug_matcher.py`:

```python
"""Match drug names from prescription history to drugs DB."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz


@dataclass
class DrugMatch:
    item_seq: str
    item_name: str
    main_item_ingr: str
    atc_code: str
    score: int


def match_drug(
    db_path: Path,
    query: str,
    min_score: int = 70,
) -> DrugMatch | None:
    """Match a drug name query against the drugs table.

    Strategy:
    1. Exact item_name match → score 100
    2. Fuzzy item_name match (token_set_ratio) ≥ min_score
    3. Fallback: fuzzy match against main_item_ingr

    Args:
        db_path: Path to the SQLite DB.
        query: Drug name from prescription history.
        min_score: Minimum fuzzy match score (0-100).

    Returns:
        Best DrugMatch or None if no match above threshold.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT item_seq, item_name, main_item_ingr, atc_code FROM drugs"
    ).fetchall()
    conn.close()

    if not rows:
        return None

    # Phase 1: exact match
    for row in rows:
        if row["item_name"] == query:
            return DrugMatch(
                item_seq=row["item_seq"],
                item_name=row["item_name"],
                main_item_ingr=row["main_item_ingr"] or "",
                atc_code=row["atc_code"] or "",
                score=100,
            )

    # Phase 2: fuzzy match on item_name
    best_score = 0
    best_row = None
    for row in rows:
        score = fuzz.token_set_ratio(query, row["item_name"])
        if score > best_score:
            best_score = score
            best_row = row

    if best_score >= min_score and best_row is not None:
        return DrugMatch(
            item_seq=best_row["item_seq"],
            item_name=best_row["item_name"],
            main_item_ingr=best_row["main_item_ingr"] or "",
            atc_code=best_row["atc_code"] or "",
            score=best_score,
        )

    # Phase 3: fuzzy match on main_item_ingr (ingredient name)
    best_score = 0
    best_row = None
    for row in rows:
        ingr = row["main_item_ingr"] or ""
        score = fuzz.token_set_ratio(query, ingr)
        if score > best_score:
            best_score = score
            best_row = row

    if best_score >= min_score and best_row is not None:
        return DrugMatch(
            item_seq=best_row["item_seq"],
            item_name=best_row["item_name"],
            main_item_ingr=best_row["main_item_ingr"] or "",
            atc_code=best_row["atc_code"] or "",
            score=best_score,
        )

    return None
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_drug_matcher.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/drug_matcher.py tests/test_drug_matcher.py
git commit -m "feat: add drug_matcher — fuzzy name matching with ingredient fallback"
```

---

## Task 7: DUR Checker — N×N Cross-Check

**Files:**
- Create: `src/pillcare/dur_checker.py`
- Create: `tests/test_dur_checker.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_dur_checker.py`:

```python
"""Tests for N×N DUR cross-check."""

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
        ("M040702", "이부프로펜", "M068301", "리튬카보네이트", "리튬 혈중농도 상승", "20200301"),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def drug_list():
    return [
        {"ingr_code": "M040702", "drug_name": "펠루비정", "department": "가정의학과"},
        {"ingr_code": "M04790101", "drug_name": "쿠마딘정", "department": "내과"},
        {"ingr_code": "M068301", "drug_name": "리튬정", "department": "정신과"},
        {"ingr_code": "M254901", "drug_name": "알게텍정", "department": "가정의학과"},
    ]


def test_check_dur_finds_known_pairs(db_with_dur, drug_list):
    alerts = check_dur(db_with_dur, drug_list)
    assert len(alerts) == 2


def test_check_dur_detects_cross_clinic(db_with_dur, drug_list):
    alerts = check_dur(db_with_dur, drug_list)
    ibu_warf = next(a for a in alerts if "와파린" in a.ingr_name_2 or "와파린" in a.ingr_name_1)
    assert ibu_warf.cross_clinic is True


def test_check_dur_includes_reason(db_with_dur, drug_list):
    alerts = check_dur(db_with_dur, drug_list)
    reasons = {a.reason for a in alerts}
    assert "출혈 위험 증가" in reasons
    assert "리튬 혈중농도 상승" in reasons


def test_check_dur_no_alerts_for_safe_drugs(db_with_dur):
    safe_drugs = [
        {"ingr_code": "M254901", "drug_name": "알게텍정", "department": "가정의학과"},
        {"ingr_code": "M999999", "drug_name": "안전한약", "department": "내과"},
    ]
    alerts = check_dur(db_with_dur, safe_drugs)
    assert len(alerts) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_dur_checker.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement dur_checker.py**

Create `src/pillcare/dur_checker.py`:

```python
"""N×N DUR cross-check for a list of drugs."""

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
    """Check all drug pairs against DUR contraindication table.

    Args:
        db_path: Path to SQLite DB with dur_pairs table.
        drugs: List of dicts with keys: ingr_code, drug_name, department.

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
        dur_lookup[key_1] = dict(row)
        dur_lookup[key_2] = dict(row)

    alerts = []
    for d1, d2 in combinations(drugs, 2):
        key = (d1["ingr_code"], d2["ingr_code"])
        if key in dur_lookup:
            row = dur_lookup[key]
            alerts.append(DurAlert(
                drug_name_1=d1["drug_name"],
                department_1=d1["department"],
                ingr_code_1=d1["ingr_code"],
                ingr_name_1=row["ingr_name_1"] if row["ingr_code_1"] == d1["ingr_code"] else row["ingr_name_2"],
                drug_name_2=d2["drug_name"],
                department_2=d2["department"],
                ingr_code_2=d2["ingr_code"],
                ingr_name_2=row["ingr_name_2"] if row["ingr_code_2"] == d2["ingr_code"] else row["ingr_name_1"],
                reason=row["reason"],
                cross_clinic=(d1["department"] != d2["department"]),
            ))

    return alerts
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_dur_checker.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/dur_checker.py tests/test_dur_checker.py
git commit -m "feat: add dur_checker — N×N DUR cross-check with cross-clinic flag"
```

---

## Task 8: Drug Info Collector

**Files:**
- Create: `src/pillcare/drug_info.py`
- Create: `tests/test_drug_info.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_drug_info.py`:

```python
"""Tests for drug info collector."""

import json
import sqlite3
from pathlib import Path

import pytest

from pillcare.db_builder import build_db
from pillcare.xml_parser import parse_nb_doc
from pillcare.drug_info import get_drug_info, DrugInfo


@pytest.fixture
def db_with_sections(tmp_path: Path, fixtures_dir: Path) -> Path:
    with open(fixtures_dir / "small_permit.json", encoding="utf-8") as f:
        permit = json.load(f)
    with open(fixtures_dir / "small_easy.json", encoding="utf-8") as f:
        easy = json.load(f)
    db_path = build_db(tmp_path / "test.db", permit_data=permit, easy_data=easy)

    # Populate drug_sections from NB_DOC_DATA
    conn = sqlite3.connect(db_path)
    for item in permit:
        nb = item.get("NB_DOC_DATA", "")
        sections = parse_nb_doc(nb)
        for s in sections:
            conn.execute(
                "INSERT OR REPLACE INTO drug_sections VALUES (?,?,?,?,?)",
                (item["ITEM_SEQ"], s.section_type, s.section_title, s.section_text, s.section_order),
            )
    conn.commit()
    conn.close()
    return db_path


def test_get_drug_info_returns_all_fields(db_with_sections):
    info = get_drug_info(db_with_sections, "199701416")
    assert info is not None
    assert info.item_name == "리도펜연질캡슐(이부프로펜)"
    assert info.main_ingr_eng == "Ibuprofen"
    assert info.chart == "주황색의 장방형 연질캡슐제"
    assert "M01AE01" in info.atc_code


def test_get_drug_info_includes_sections(db_with_sections):
    info = get_drug_info(db_with_sections, "199701416")
    assert "금기" in info.sections
    assert "상호작용" in info.sections


def test_get_drug_info_includes_easy_text(db_with_sections):
    info = get_drug_info(db_with_sections, "199701416")
    assert info.easy is not None
    assert "감기" in info.easy["efcy_qesitm"]


def test_get_drug_info_returns_none_for_unknown(db_with_sections):
    info = get_drug_info(db_with_sections, "999999999")
    assert info is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_drug_info.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement drug_info.py**

Create `src/pillcare/drug_info.py`:

```python
"""Collect all medication guidance data for a single drug."""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DrugInfo:
    item_seq: str
    item_name: str
    item_eng_name: str
    entp_name: str
    etc_otc_code: str
    material_name: str
    main_item_ingr: str
    main_ingr_eng: str
    chart: str
    atc_code: str
    storage_method: str
    valid_term: str
    total_content: str
    sections: dict[str, str] = field(default_factory=dict)  # section_type → text
    easy: dict[str, str] | None = None  # e약은요 fields


def get_drug_info(db_path: Path, item_seq: str) -> DrugInfo | None:
    """Collect all info for a drug by item_seq.

    Joins drugs + drug_sections + drugs_easy tables.

    Args:
        db_path: Path to SQLite DB.
        item_seq: 품목일련번호.

    Returns:
        DrugInfo with all available data, or None if not found.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        "SELECT * FROM drugs WHERE item_seq = ?", (item_seq,)
    ).fetchone()
    if row is None:
        conn.close()
        return None

    info = DrugInfo(
        item_seq=row["item_seq"],
        item_name=row["item_name"] or "",
        item_eng_name=row["item_eng_name"] or "",
        entp_name=row["entp_name"] or "",
        etc_otc_code=row["etc_otc_code"] or "",
        material_name=row["material_name"] or "",
        main_item_ingr=row["main_item_ingr"] or "",
        main_ingr_eng=row["main_ingr_eng"] or "",
        chart=row["chart"] or "",
        atc_code=row["atc_code"] or "",
        storage_method=row["storage_method"] or "",
        valid_term=row["valid_term"] or "",
        total_content=row["total_content"] or "",
    )

    # Load sections
    sec_rows = conn.execute(
        "SELECT section_type, section_text FROM drug_sections WHERE item_seq = ? ORDER BY section_order",
        (item_seq,),
    ).fetchall()
    for sr in sec_rows:
        stype = sr["section_type"]
        if stype in info.sections:
            info.sections[stype] += "\n\n" + sr["section_text"]
        else:
            info.sections[stype] = sr["section_text"]

    # Load easy text
    easy_row = conn.execute(
        "SELECT * FROM drugs_easy WHERE item_seq = ?", (item_seq,)
    ).fetchone()
    if easy_row:
        info.easy = {
            "efcy_qesitm": easy_row["efcy_qesitm"] or "",
            "use_method_qesitm": easy_row["use_method_qesitm"] or "",
            "atpn_warn_qesitm": easy_row["atpn_warn_qesitm"] or "",
            "atpn_qesitm": easy_row["atpn_qesitm"] or "",
            "intrc_qesitm": easy_row["intrc_qesitm"] or "",
            "se_qesitm": easy_row["se_qesitm"] or "",
            "deposit_method_qesitm": easy_row["deposit_method_qesitm"] or "",
        }

    conn.close()
    return info
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_drug_info.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/drug_info.py tests/test_drug_info.py
git commit -m "feat: add drug_info — collect all guidance data per drug"
```

---

## Task 9: Claude Agent — Tool-Use Orchestration

**Files:**
- Create: `src/pillcare/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_agent.py`:

```python
"""Tests for Claude tool-use agent with mocked client."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pillcare.agent import MedicationAgent, GuidanceResult


@pytest.fixture
def mock_anthropic():
    client = MagicMock()
    # Mock a simple response that returns text content
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.type = "text"
    mock_content.text = json.dumps({
        "detailed": [
            {
                "drug_name": "펠루비정",
                "sections": {
                    "명칭": "[T1:허가정보] 펠루비정 (pelubiprofen 30mg)",
                    "효능효과": "[T1:e약은요] 이 약은 관절염, 통증에 사용합니다.",
                },
            }
        ],
        "dur_warnings": [
            {
                "drug_1": "펠루비정",
                "drug_2": "록스펜정",
                "reason": "동일계열 NSAIDs 병용 위험 [T1:DUR]",
                "cross_clinic": True,
            }
        ],
        "summary": ["펠루비정과 록스펜정은 같은 계열 약물입니다. [T1:DUR]"],
        "warning_labels": ["해열진통제 병용 주의"],
    })
    mock_response.content = [mock_content]
    mock_response.stop_reason = "end_turn"
    client.messages.create.return_value = mock_response
    return client


def test_agent_generates_guidance(mock_anthropic):
    agent = MedicationAgent(client=mock_anthropic)
    drug_infos = [{"item_name": "펠루비정", "sections": {}}]
    dur_alerts = [{"drug_1": "펠루비정", "drug_2": "록스펜정", "reason": "NSAIDs 병용"}]

    result = agent.generate(drug_infos=drug_infos, dur_alerts=dur_alerts, patient_context={})
    assert result is not None
    assert len(result.detailed) >= 1
    assert len(result.dur_warnings) >= 1


def test_agent_calls_anthropic_with_system_prompt(mock_anthropic):
    agent = MedicationAgent(client=mock_anthropic)
    agent.generate(drug_infos=[], dur_alerts=[], patient_context={})

    call_kwargs = mock_anthropic.messages.create.call_args
    system = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
    assert "복약 정보" in system or "복약" in str(system)


def test_agent_includes_guardrail_in_system(mock_anthropic):
    agent = MedicationAgent(client=mock_anthropic)
    agent.generate(drug_infos=[], dur_alerts=[], patient_context={})

    call_kwargs = mock_anthropic.messages.create.call_args
    system = str(call_kwargs)
    assert "진단" in system or "의사 또는 약사" in system
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_agent.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement agent.py**

Create `src/pillcare/agent.py`:

```python
"""Claude tool-use agent for medication guidance generation."""

import json
from dataclasses import dataclass, field


SYSTEM_PROMPT = """당신은 복약 정보 안내 AI입니다.

## 역할 경계
- 절대 금지: 진단, 처방, 용량 변경 권고, 투약 중단 판단
- 모든 경고의 결론: "의사 또는 약사와 상담하십시오"
- 용어: "복약지도" 대신 "복약 정보 안내"를 사용

## 출력 규칙
- 모든 문장에 출처 티어 태그 필수: [T1:허가정보], [T1:DUR], [T1:e약은요], [T4:AI]
- T4 태그 문장은 "※ AI가 생성한 일반 정보입니다" 부기
- DUR 금기는 반드시 최상단에 경고로 표시
- 다기관 처방 교차 금기는 별도 강조

## 복약 정보 체크리스트 (10개 항목)
1) 명칭: [T1] 제품명, 성분명, 제조사, 제형, 함량
2) 성상: [T1] 외형 설명
3) 효능효과: [T1] 허가사항 기반
4) 투여의의: [T4] 약이 필요한 이유
5) 용법용량: [T1] 사용시간, 횟수, 용량
6) 저장방법: [T1] 보관조건, 유효기간
7) 주의/부작용: [T1] 흔한 이상반응 + 중대 이상반응
8) 상호작용: [T1:DUR] 병용금기 + [T1:허가정보]
9) 투여종료후: [T4] 해당 시
10) 기타: [T1/T4] 복용 누락 등

## 출력 형식
JSON으로 응답하십시오:
{
  "detailed": [{"drug_name": "...", "sections": {"명칭": "...", "효능효과": "...", ...}}],
  "dur_warnings": [{"drug_1": "...", "drug_2": "...", "reason": "...", "cross_clinic": bool}],
  "summary": ["핵심 포인트 1", ...],
  "warning_labels": ["경고라벨 1", ...]
}"""

BANNED_WORDS = ["진단합니다", "처방합니다", "투약판단", "용량을 조절", "복용을 중단하세요", "복약지도"]


@dataclass
class GuidanceResult:
    detailed: list[dict] = field(default_factory=list)
    dur_warnings: list[dict] = field(default_factory=list)
    summary: list[str] = field(default_factory=list)
    warning_labels: list[str] = field(default_factory=list)
    raw_response: str = ""


class MedicationAgent:
    def __init__(self, client, model: str = "claude-sonnet-4-6"):
        self._client = client
        self._model = model

    def generate(
        self,
        drug_infos: list[dict],
        dur_alerts: list[dict],
        patient_context: dict,
    ) -> GuidanceResult:
        """Generate medication guidance using Claude.

        Args:
            drug_infos: List of drug info dicts (from DrugInfo).
            dur_alerts: List of DUR alert dicts (from DurAlert).
            patient_context: Patient metadata (departments, etc).

        Returns:
            GuidanceResult with structured output.
        """
        user_message = self._build_user_message(drug_infos, dur_alerts, patient_context)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = ""
        for block in response.content:
            if block.type == "text":
                raw += block.text

        return self._parse_response(raw)

    def _build_user_message(
        self,
        drug_infos: list[dict],
        dur_alerts: list[dict],
        patient_context: dict,
    ) -> str:
        parts = []
        parts.append("아래 환자의 투약 정보를 바탕으로 복약 정보 안내문을 생성하십시오.\n")

        if patient_context:
            parts.append(f"## 환자 정보\n{json.dumps(patient_context, ensure_ascii=False)}\n")

        if dur_alerts:
            parts.append("## DUR 병용금기 경고 (T1 — 확정된 금기)\n")
            for alert in dur_alerts:
                parts.append(f"- {json.dumps(alert, ensure_ascii=False)}")
            parts.append("")

        parts.append("## 약물별 상세 정보 (T1)\n")
        for info in drug_infos:
            parts.append(f"### {info.get('item_name', 'Unknown')}")
            parts.append(json.dumps(info, ensure_ascii=False, indent=2))
            parts.append("")

        return "\n".join(parts)

    def _parse_response(self, raw: str) -> GuidanceResult:
        result = GuidanceResult(raw_response=raw)
        try:
            # Extract JSON from response (may be wrapped in markdown)
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0]

            data = json.loads(json_str)
            result.detailed = data.get("detailed", [])
            result.dur_warnings = data.get("dur_warnings", [])
            result.summary = data.get("summary", [])
            result.warning_labels = data.get("warning_labels", [])
        except (json.JSONDecodeError, IndexError):
            pass

        return result
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_agent.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/agent.py tests/test_agent.py
git commit -m "feat: add agent — Claude tool-use orchestration with guardrails"
```

---

## Task 10: Guardrails — Post-Verification + Safety Filters

**Files:**
- Create: `src/pillcare/guardrails.py`
- Create: `tests/test_guardrails.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_guardrails.py`:

```python
"""Tests for post-verification guardrails."""

import pytest

from pillcare.guardrails import verify_dur_coverage, filter_banned_words, BANNED_WORDS


def test_verify_dur_coverage_detects_missing():
    dur_alerts = [
        {"drug_name_1": "펠루비정", "drug_name_2": "록스펜정", "reason": "NSAIDs 병용"},
        {"drug_name_1": "이부프로펜", "drug_name_2": "와파린", "reason": "출혈 위험"},
    ]
    generated_text = "펠루비정과 록스펜정은 동일 계열입니다."
    # "이부프로펜×와파린" is not mentioned → should be flagged
    missing = verify_dur_coverage(generated_text, dur_alerts)
    assert len(missing) == 1
    assert "와파린" in missing[0]["drug_name_2"]


def test_verify_dur_coverage_all_present():
    dur_alerts = [
        {"drug_name_1": "펠루비정", "drug_name_2": "록스펜정", "reason": "NSAIDs 병용"},
    ]
    generated_text = "펠루비정과 록스펜정은 동일 계열의 약물입니다."
    missing = verify_dur_coverage(generated_text, dur_alerts)
    assert len(missing) == 0


def test_filter_banned_words_removes_violations():
    text = "이 약을 진단합니다. 복약지도를 시행합니다. 의사와 상담하십시오."
    cleaned = filter_banned_words(text)
    for word in BANNED_WORDS:
        assert word not in cleaned


def test_filter_banned_words_preserves_clean_text():
    text = "이 약은 감기에 사용합니다. 의사 또는 약사와 상담하십시오."
    cleaned = filter_banned_words(text)
    assert cleaned == text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_guardrails.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement guardrails.py**

Create `src/pillcare/guardrails.py`:

```python
"""Post-verification guardrails for generated medication guidance."""

BANNED_WORDS = [
    "진단합니다",
    "처방합니다",
    "투약판단",
    "용량을 조절",
    "복용을 중단하세요",
    "복약지도",
]


def verify_dur_coverage(
    generated_text: str,
    dur_alerts: list[dict],
) -> list[dict]:
    """Check that all DUR alerts are mentioned in generated text.

    Args:
        generated_text: The full generated guidance text.
        dur_alerts: List of DUR alert dicts with drug_name_1, drug_name_2.

    Returns:
        List of DUR alerts that were NOT mentioned in the text.
    """
    missing = []
    for alert in dur_alerts:
        name_1 = alert.get("drug_name_1", "")
        name_2 = alert.get("drug_name_2", "")
        if name_1 in generated_text and name_2 in generated_text:
            continue
        missing.append(alert)
    return missing


def filter_banned_words(text: str) -> str:
    """Remove banned words/phrases from generated text.

    Args:
        text: Generated guidance text.

    Returns:
        Cleaned text with banned words replaced.
    """
    result = text
    for word in BANNED_WORDS:
        result = result.replace(word, "[삭제된 표현]")
    # Clean up: remove "[삭제된 표현]" artifacts
    while "[삭제된 표현]" in result:
        result = result.replace("[삭제된 표현]", "")
    # Clean double spaces
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_guardrails.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/guardrails.py tests/test_guardrails.py
git commit -m "feat: add guardrails — DUR coverage check + banned word filter"
```

---

## Task 11: Streamlit UI

**Files:**
- Create: `src/pillcare/app.py`

This task is manually smoke-tested, no automated tests.

- [ ] **Step 1: Implement app.py**

Create `src/pillcare/app.py`:

```python
"""Streamlit UI for PillCare medication guidance POC."""

import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pillcare.history_parser import parse_history_xls
from pillcare.drug_matcher import match_drug
from pillcare.dur_checker import check_dur
from pillcare.drug_info import get_drug_info
from pillcare.agent import MedicationAgent, GuidanceResult
from pillcare.guardrails import verify_dur_coverage, filter_banned_words

DB_PATH = Path("data/pillcare.db")


def main():
    st.set_page_config(page_title="필케어 — 복약 정보 안내", layout="wide")
    st.title("💊 필케어 (PillCare)")
    st.caption("개인 투약이력 기반 grounded 복약 정보 안내 POC")

    if not DB_PATH.exists():
        st.error(f"DB not found at {DB_PATH}. Run `python -m pillcare.db_builder` first.")
        return

    # File upload
    uploaded_files = st.file_uploader(
        "심평원 '내가 먹는 약' 투약이력 파일 업로드 (.xls)",
        type=["xls"],
        accept_multiple_files=True,
    )

    password = st.text_input("파일 비밀번호", type="password")

    if not uploaded_files or not password:
        st.info("투약이력 파일을 업로드하고 비밀번호를 입력하세요.")
        return

    if st.button("🔍 분석 시작"):
        with st.spinner("투약이력 파싱 중..."):
            all_records = []
            for uf in uploaded_files:
                dept = st.text_input(f"{uf.name}의 진료과", key=f"dept_{uf.name}")
                if not dept:
                    dept = "미지정"
                # Save temp file for parsing
                tmp_path = Path(f"/tmp/{uf.name}")
                tmp_path.write_bytes(uf.read())
                records = parse_history_xls(tmp_path, password=password, department=dept)
                all_records.extend(records)

        st.success(f"{len(all_records)}개 약물 파싱 완료")

        # Match drugs
        with st.spinner("약물 매칭 중..."):
            matched_drugs = []
            for rec in all_records:
                m = match_drug(DB_PATH, rec.drug_name)
                if m:
                    matched_drugs.append({
                        "ingr_code": m.main_item_ingr.split("]")[0].replace("[", "") if "]" in m.main_item_ingr else "",
                        "drug_name": rec.drug_name,
                        "department": rec.department,
                        "item_seq": m.item_seq,
                        "match_score": m.score,
                    })

        # DUR check
        with st.spinner("DUR 병용금기 체크 중..."):
            dur_alerts = check_dur(DB_PATH, matched_drugs)

        if dur_alerts:
            st.error(f"⚠️ {len(dur_alerts)}건의 병용금기 발견!")
            for alert in dur_alerts:
                cross = " 🏥 다기관 교차" if alert.cross_clinic else ""
                st.warning(f"**{alert.drug_name_1}** × **{alert.drug_name_2}**: {alert.reason}{cross}")

        # Collect drug info
        with st.spinner("약물 정보 수집 중..."):
            drug_infos = []
            for md in matched_drugs:
                info = get_drug_info(DB_PATH, md["item_seq"])
                if info:
                    drug_infos.append(asdict(info))

        # Generate guidance
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            st.error("ANTHROPIC_API_KEY not set in .env")
            return

        with st.spinner("복약 정보 안내문 생성 중..."):
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            agent = MedicationAgent(client=client)
            result = agent.generate(
                drug_infos=drug_infos,
                dur_alerts=[asdict(a) for a in dur_alerts],
                patient_context={"departments": list({r.department for r in all_records})},
            )

        # Display results
        st.header("📋 복약 정보 안내")

        if result.dur_warnings:
            st.subheader("⚠️ 병용금기 경고")
            for w in result.dur_warnings:
                st.error(f"**{w['drug_1']}** × **{w['drug_2']}**: {w['reason']}")

        if result.detailed:
            st.subheader("📄 상세 복약 정보 (별첨1)")
            for drug in result.detailed:
                with st.expander(drug.get("drug_name", "약물")):
                    for section, text in drug.get("sections", {}).items():
                        st.markdown(f"**{section}**")
                        st.write(text)

        if result.summary:
            st.subheader("📝 핵심 요약 (별첨2)")
            for point in result.summary:
                st.write(f"• {point}")

        if result.warning_labels:
            st.subheader("🏷️ 경고 라벨 (별첨3)")
            for label in result.warning_labels:
                st.warning(label)


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
git commit -m "feat: add Streamlit UI for medication guidance POC"
```

---

## Task 12: Full DB Build + End-to-End Smoke Test

**Files:**
- Modify: `src/pillcare/db_builder.py` (add CLI entry point)

- [ ] **Step 1: Add CLI entry point to db_builder.py**

Add to the bottom of `src/pillcare/db_builder.py`:

```python
def build_full_db(data_dir: Path, db_path: Path) -> Path:
    """Build the complete DB from all crawled data files.

    Args:
        data_dir: Directory containing crawled JSON/CSV files.
        db_path: Where to create the DB.
    """
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

    # Build base tables
    print("Building base tables...")
    build_db(db_path, permit_data=permit_data, easy_data=easy_data)

    # Parse NB_DOC_DATA → drug_sections
    print("Parsing NB_DOC_DATA XML into sections...")
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM drug_sections")
    count = 0
    for item in permit_data:
        nb = item.get("NB_DOC_DATA", "")
        if not nb:
            continue
        sections = parse_nb_doc(nb)
        for s in sections:
            conn.execute(
                "INSERT OR REPLACE INTO drug_sections VALUES (?,?,?,?,?)",
                (item["ITEM_SEQ"], s.section_type, s.section_title, s.section_text, s.section_order),
            )
            count += 1
    conn.commit()
    print(f"  {count} sections inserted")

    # Normalize DUR
    dur_csv = data_dir / "한국의약품안전관리원_병용금기약물_20240625.csv"
    if dur_csv.exists():
        print("Normalizing DUR pairs...")
        pairs = normalize_dur(dur_csv, encoding="cp949")
        conn.execute("DELETE FROM dur_pairs")
        for p in pairs:
            conn.execute(
                "INSERT OR REPLACE INTO dur_pairs VALUES (?,?,?,?,?,?)",
                (p.ingr_code_1, p.ingr_name_1, p.ingr_code_2, p.ingr_name_2, p.reason, p.notice_date),
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

Expected: DB created at `data/pillcare.db` with all tables populated.

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest -v
```

Expected: All tests PASS.

- [ ] **Step 4: End-to-end smoke test with Streamlit**

```bash
uv run streamlit run src/pillcare/app.py
```

Upload sample xls files, verify full pipeline.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/db_builder.py
git commit -m "feat: add full DB build CLI + end-to-end pipeline"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: All 5 pipeline stages (입력파싱→DUR체크→정보수집→Agent생성→사후검증) have corresponding tasks.
- [x] **Placeholder scan**: All code blocks are complete, no TBD/TODO.
- [x] **Type consistency**: DrugMatch, DurPair, DurAlert, MedRecord, DrugInfo, Section, GuidanceResult — consistent across tasks.
- [x] **File paths**: All paths match the file structure diagram.
- [x] **10-item checklist**: Mapped in agent.py SYSTEM_PROMPT, data sourced from db_builder→drug_info pipeline.
- [x] **DUR deterministic + RAG enrichment (Option C)**: DUR check in Task 7 is deterministic (Stage 2), drug_info in Task 8 provides RAG-like enrichment from parsed sections (Stage 3), agent in Task 9 combines both.
