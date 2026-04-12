# 필케어 POC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-scenario, end-to-end working POC demonstrating the 필케어 agent pipeline (약봉투 image → VLM OCR → 식약처 DB 매칭 → 심평원 DUR 체크 → Claude tool-use agent response with Grounded citations) so it can be captured as screenshots for the 5p proposal and as video footage for the 3-min YouTube submission.

**Architecture:** Pure-function domain modules (drug_matcher, dur_checker, citations) wrapped by a thin Claude vision layer (vision) and a Claude tool-use orchestration loop (agent), exposed through a minimal Streamlit single-page UI (app). Claude SDK calls are encapsulated so that pure-function modules stay TDD-friendly and the agent loop can be integration-tested with a mocked Anthropic client.

**Tech Stack:** Python 3.11 · uv · anthropic SDK (Claude Sonnet 4.6 with vision + tool_use) · pandas · rapidfuzz · pytest · streamlit · python-dotenv

**Scope:**
- ✅ POC software (8 tasks below)
- ❌ 5p 제안서 작성 (설계 spec §5-P1~P5 레이아웃에 따라 팀이 직접 작성)
- ❌ 3분 영상 제작 (설계 spec §6 스토리보드에 따라 팀이 직접 제작)
- ❌ Phase 2 풀 구현 W1-W6 (본선 선정 시 별도 plan)

---

## File Structure

```
pill-care/
├── pyproject.toml                 # uv project config (Task 1)
├── .python-version                # Python 3.11 (Task 1)
├── .env.example                   # ANTHROPIC_API_KEY placeholder (Task 1)
├── .gitignore                     # ignore .env, __pycache__ (Task 1)
├── README.md                      # Demo instructions (Task 9)
├── medicines.csv                  # EXISTS (식약처 낱알식별, 25,689 rows)
├── samples/
│   ├── dur_sample.json            # Hardcoded DUR 병용금기 샘플 (Task 3)
│   └── prescription_sample.jpg    # Sample 약봉투 image (Task 8, team supplies)
├── src/
│   └── pillcare/
│       ├── __init__.py            # (Task 1)
│       ├── drug_matcher.py        # Pure function: medicines.csv 매칭 (Task 2)
│       ├── dur_checker.py         # Pure function: DUR 병용금기 체크 (Task 3)
│       ├── citations.py           # Citation dataclass + formatting (Task 4)
│       ├── vision.py              # Claude vision OCR wrapper (Task 5)
│       ├── agent.py               # Tool-use agent orchestration (Task 6)
│       └── app.py                 # Streamlit UI (Task 7)
└── tests/
    ├── __init__.py                # (Task 1)
    ├── conftest.py                # Shared fixtures (Task 1)
    ├── fixtures/
    │   └── small_medicines.csv    # Test fixture (Task 2)
    ├── test_drug_matcher.py       # (Task 2)
    ├── test_dur_checker.py        # (Task 3)
    ├── test_citations.py          # (Task 4)
    └── test_agent.py              # Integration test (Task 6)
```

**Decomposition rationale**:
- Pure function modules (drug_matcher, dur_checker, citations) are unit-tested with TDD.
- Claude API wrappers (vision, agent) are integration-tested with a mocked Anthropic client injected via constructor.
- The Streamlit UI (app.py) is manually smoke-tested — no automated test.
- Sample data (dur_sample.json, prescription_sample.jpg) lives in `samples/`, test fixtures in `tests/fixtures/`.

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/pillcare/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Install Python 3.11 via uv**

Run: `uv python install 3.11`
Expected: Python 3.11 downloaded and available.

- [ ] **Step 2: Initialize uv project**

Run: `cd /Users/User/Documents/pill-care && uv init --package --name pillcare --python 3.11`
Expected: `pyproject.toml` and `.python-version` created. If `hello.py` or similar scaffold files are created, delete them.

- [ ] **Step 3: Verify dependency versions via context7/PyPI before installing**

Run each in parallel and pick the current stable version that is compatible with Python 3.11:

```bash
npx ctx7@latest library anthropic "python SDK for Claude with tool_use and vision"
npx ctx7@latest library pandas "Python dataframe library"
npx ctx7@latest library rapidfuzz "fuzzy string matching Python"
npx ctx7@latest library pytest "Python testing framework"
npx ctx7@latest library streamlit "Python web app framework"
npx ctx7@latest library pillow "Python imaging library"
npx ctx7@latest library python-dotenv "load .env files in Python"
```

Record verified versions in the Task 1 commit message.

- [ ] **Step 4: Install dependencies with pinned verified versions**

Run (replace `<verified>` with versions from Step 3):

```bash
uv add "anthropic==<verified>" "pandas==<verified>" "rapidfuzz==<verified>" "pillow==<verified>" "python-dotenv==<verified>"
uv add --dev "pytest==<verified>" "streamlit==<verified>"
```

Expected: `uv.lock` updated, no resolver conflicts.

- [ ] **Step 5: Create `.env.example`**

Create `.env.example` with:

```
# Copy this file to .env and fill in your API key
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 6: Create `.gitignore`**

Create `.gitignore` with:

```
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
uv.lock.bak
.DS_Store
```

- [ ] **Step 7: Create package and test structure**

Create `src/pillcare/__init__.py` with:

```python
"""필케어 (PillCare) — 통합 약물 지식 그래프 기반 자율 복약 관리 AI 에이전트 POC."""

__version__ = "0.1.0"
```

Create `tests/__init__.py` as empty file.

Create `tests/conftest.py` with:

```python
"""Shared pytest fixtures for 필케어 POC tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the tests/fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def samples_dir() -> Path:
    """Return the path to the repo-level samples directory."""
    return Path(__file__).parent.parent / "samples"
```

- [ ] **Step 8: Verify pytest runs (no tests yet, but collect succeeds)**

Run: `uv run pytest -v`
Expected: `no tests ran in X seconds` (collection succeeds, zero tests).

- [ ] **Step 9: Commit**

```bash
git init  # if not yet a git repo
git add pyproject.toml .python-version .env.example .gitignore src/ tests/ uv.lock
git commit -m "chore: bootstrap POC project with uv and verified deps"
```

---

## Task 2: Drug Matcher (fuzzy match against medicines.csv)

**Files:**
- Create: `src/pillcare/drug_matcher.py`
- Create: `tests/test_drug_matcher.py`
- Create: `tests/fixtures/small_medicines.csv`

**Domain note**: `medicines.csv` contains 25,689 Korean drug records from 식약처 낱알식별 정보. Columns include `ITEM_SEQ` (품목일련번호), `ITEM_NAME` (제품명), `ENTP_NAME` (업체명), `EDI_CODE` (보험 코드). We need a fuzzy-match function because VLM OCR will extract imperfect drug names.

- [ ] **Step 1: Create test fixture (small CSV with 5 rows)**

Create `tests/fixtures/small_medicines.csv`:

```csv
ITEM_SEQ,ITEM_NAME,ENTP_NAME,EDI_CODE
200808876,가스디알정50밀리그램(디메크로틴산마그네슘),일동제약(주),641900720
200808877,페라트라정2.5밀리그램(레트로졸),(주)유한양행,641900730
197800001,타이레놀정500밀리그램(아세트아미노펜),한국얀센(주),641900740
200000001,아스피린프로텍트정100밀리그램(아세틸살리실산),바이엘코리아(주),641900750
201000001,아달라트오로스정30밀리그램(니페디핀),바이엘코리아(주),641900760
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_drug_matcher.py`:

```python
"""Tests for the drug_matcher module."""

from pathlib import Path

import pandas as pd
import pytest

from pillcare.drug_matcher import DrugMatch, load_medicines, match_drug


def test_load_medicines_returns_dataframe(fixtures_dir: Path):
    db = load_medicines(fixtures_dir / "small_medicines.csv")
    assert isinstance(db, pd.DataFrame)
    assert len(db) == 5
    assert "ITEM_NAME" in db.columns


def test_match_drug_exact_match(fixtures_dir: Path):
    db = load_medicines(fixtures_dir / "small_medicines.csv")
    result = match_drug("타이레놀정500밀리그램(아세트아미노펜)", db)
    assert result is not None
    assert result.item_name == "타이레놀정500밀리그램(아세트아미노펜)"
    assert result.entp_name == "한국얀센(주)"
    assert result.edi_code == "641900740"
    assert result.score >= 95.0


def test_match_drug_partial_match(fixtures_dir: Path):
    db = load_medicines(fixtures_dir / "small_medicines.csv")
    result = match_drug("타이레놀 500mg", db)  # VLM OCR simplified form
    assert result is not None
    assert "타이레놀" in result.item_name


def test_match_drug_below_threshold_returns_none(fixtures_dir: Path):
    db = load_medicines(fixtures_dir / "small_medicines.csv")
    result = match_drug("완전히관계없는문자열XYZ123", db, min_score=80.0)
    assert result is None


def test_match_drug_with_missing_edi_code(fixtures_dir: Path, tmp_path: Path):
    csv_path = tmp_path / "no_edi.csv"
    csv_path.write_text(
        "ITEM_SEQ,ITEM_NAME,ENTP_NAME,EDI_CODE\n"
        "999999,테스트정,테스트사,\n",
        encoding="utf-8",
    )
    db = load_medicines(csv_path)
    result = match_drug("테스트정", db)
    assert result is not None
    assert result.edi_code is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_drug_matcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pillcare.drug_matcher'`

- [ ] **Step 4: Implement `src/pillcare/drug_matcher.py`**

```python
"""식약처 낱알식별 DB fuzzy match 모듈.

Pure function layer — VLM OCR 결과(부정확한 한국어 약물명)를 medicines.csv의
표준 품목에 매핑한다. Claude API에 의존하지 않으므로 TDD로 검증 가능.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process


@dataclass(frozen=True)
class DrugMatch:
    """A single fuzzy-match result from medicines.csv."""

    item_seq: str
    item_name: str
    entp_name: str
    edi_code: str | None
    score: float


def load_medicines(csv_path: str | Path) -> pd.DataFrame:
    """Load medicines.csv into a pandas DataFrame.

    Args:
        csv_path: Path to the medicines CSV (식약처 낱알식별 정보).

    Returns:
        DataFrame with all drug records.
    """
    return pd.read_csv(csv_path, dtype=str)


def match_drug(
    query: str,
    db: pd.DataFrame,
    min_score: float = 70.0,
) -> DrugMatch | None:
    """Fuzzy-match a drug name query against the medicines DB.

    Uses rapidfuzz token_set_ratio which handles word order and extra tokens
    gracefully — appropriate for noisy VLM OCR outputs.

    Args:
        query: Drug name as extracted by VLM OCR (may be imperfect).
        db: medicines DataFrame from load_medicines.
        min_score: Minimum rapidfuzz score (0-100) to accept a match.

    Returns:
        The best match as DrugMatch, or None if no match exceeds min_score.
    """
    names = db["ITEM_NAME"].tolist()
    result = process.extractOne(query, names, scorer=fuzz.token_set_ratio)
    if result is None:
        return None
    matched_name, score, idx = result
    if score < min_score:
        return None
    row = db.iloc[idx]
    edi_raw = row.get("EDI_CODE")
    edi_code = str(edi_raw) if pd.notna(edi_raw) and edi_raw != "" else None
    return DrugMatch(
        item_seq=str(row["ITEM_SEQ"]),
        item_name=row["ITEM_NAME"],
        entp_name=row["ENTP_NAME"],
        edi_code=edi_code,
        score=float(score),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_drug_matcher.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/pillcare/drug_matcher.py tests/test_drug_matcher.py tests/fixtures/small_medicines.csv
git commit -m "feat: add fuzzy drug matcher against 식약처 낱알식별 DB"
```

---

## Task 3: DUR Checker (hardcoded 병용금기 sample)

**Files:**
- Create: `samples/dur_sample.json`
- Create: `src/pillcare/dur_checker.py`
- Create: `tests/test_dur_checker.py`

**Domain note**: 심평원 DUR(KOGL Type 1) 실데이터는 수천 건이지만, POC는 **10개 내외의 대표 병용금기 쌍**을 JSON에 하드코딩해 단일 시나리오를 재현 가능하게 만든다. 실제 심평원 파일은 Phase 2 W1 UDKG Builder에서 통합.

- [ ] **Step 1: Create DUR sample JSON**

Create `samples/dur_sample.json`:

```json
[
  {
    "drug_a": "와파린정2밀리그람",
    "drug_b": "아스피린프로텍트정100밀리그램(아세틸살리실산)",
    "severity": "병용금기",
    "reason": "출혈 위험이 유의하게 증가할 수 있음. 두 약물 병용 시 의료진에게 확인 요청.",
    "source": "심평원 DUR 병용금기 목록 2024"
  },
  {
    "drug_a": "아달라트오로스정30밀리그램(니페디핀)",
    "drug_b": "리팜핀캡슐300밀리그램(리팜피신)",
    "severity": "병용금기",
    "reason": "리팜피신이 니페디핀 대사를 가속화하여 치료 효과가 현저히 감소할 수 있음.",
    "source": "심평원 DUR 병용금기 목록 2024"
  },
  {
    "drug_a": "타이레놀정500밀리그램(아세트아미노펜)",
    "drug_b": "와파린정2밀리그람",
    "severity": "병용주의",
    "reason": "장기 병용 시 INR 상승 가능. 의료진에게 확인 요청.",
    "source": "심평원 DUR 병용주의 목록 2024"
  },
  {
    "drug_a": "페라트라정2.5밀리그램(레트로졸)",
    "drug_b": "타목시펜정20밀리그램",
    "severity": "병용금기",
    "reason": "상호 치료 효과 감소. 동일 적응증 내 병용 불가.",
    "source": "심평원 DUR 병용금기 목록 2024"
  },
  {
    "drug_a": "가스디알정50밀리그램(디메크로틴산마그네슘)",
    "drug_b": "테트라사이클린캡슐250밀리그램",
    "severity": "병용금기",
    "reason": "마그네슘이 테트라사이클린 흡수를 저해하여 항생 효과 감소.",
    "source": "심평원 DUR 병용금기 목록 2024"
  }
]
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_dur_checker.py`:

```python
"""Tests for the dur_checker module."""

import json
from pathlib import Path

import pytest

from pillcare.dur_checker import Interaction, check_interactions, load_dur_sample


@pytest.fixture
def dur_sample(samples_dir: Path) -> list[dict]:
    return load_dur_sample(samples_dir / "dur_sample.json")


def test_load_dur_sample_returns_list(dur_sample: list[dict]):
    assert isinstance(dur_sample, list)
    assert len(dur_sample) >= 5
    assert "drug_a" in dur_sample[0]
    assert "severity" in dur_sample[0]


def test_check_interactions_empty_input(dur_sample: list[dict]):
    result = check_interactions([], dur_sample)
    assert result == []


def test_check_interactions_single_drug_no_interactions(dur_sample: list[dict]):
    result = check_interactions(["타이레놀정500밀리그램(아세트아미노펜)"], dur_sample)
    assert result == []


def test_check_interactions_finds_pair(dur_sample: list[dict]):
    drugs = [
        "와파린정2밀리그람",
        "아스피린프로텍트정100밀리그램(아세틸살리실산)",
    ]
    result = check_interactions(drugs, dur_sample)
    assert len(result) == 1
    interaction = result[0]
    assert isinstance(interaction, Interaction)
    assert interaction.severity == "병용금기"
    assert "출혈" in interaction.reason
    assert interaction.source == "심평원 DUR 병용금기 목록 2024"


def test_check_interactions_finds_multiple(dur_sample: list[dict]):
    drugs = [
        "와파린정2밀리그람",
        "아스피린프로텍트정100밀리그램(아세틸살리실산)",
        "타이레놀정500밀리그램(아세트아미노펜)",
    ]
    result = check_interactions(drugs, dur_sample)
    # 와파린+아스피린(병용금기), 와파린+타이레놀(병용주의) — 2 건
    assert len(result) == 2
    severities = {i.severity for i in result}
    assert severities == {"병용금기", "병용주의"}


def test_check_interactions_symmetric_order(dur_sample: list[dict]):
    """병용금기는 입력 순서에 무관하게 탐지되어야 한다."""
    drugs_reversed = [
        "아스피린프로텍트정100밀리그램(아세틸살리실산)",
        "와파린정2밀리그람",
    ]
    result = check_interactions(drugs_reversed, dur_sample)
    assert len(result) == 1
    assert result[0].severity == "병용금기"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_dur_checker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pillcare.dur_checker'`

- [ ] **Step 4: Implement `src/pillcare/dur_checker.py`**

```python
"""심평원 DUR 병용금기/병용주의 체크 모듈.

Pure function layer — 주어진 약물명 리스트에서 DUR 샘플 JSON과 일치하는
상호작용 쌍을 탐지한다. 입력 순서에 무관하게 대칭적으로 작동.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Interaction:
    """A single DUR interaction hit."""

    drug_a: str
    drug_b: str
    severity: str  # "병용금기", "병용주의", "연령금기", "임부금기"
    reason: str
    source: str


def load_dur_sample(json_path: str | Path) -> list[dict]:
    """Load the DUR sample JSON file.

    Args:
        json_path: Path to a JSON file containing DUR pairs.

    Returns:
        List of DUR entry dicts.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_interactions(
    drug_names: list[str],
    dur_data: list[dict],
) -> list[Interaction]:
    """Find all DUR interactions between drugs in the input list.

    Checks every DUR entry against the input drug set, so order of input
    is irrelevant (symmetric).

    Args:
        drug_names: List of drug names (as matched from medicines DB).
        dur_data: List of DUR entry dicts loaded from load_dur_sample.

    Returns:
        List of Interaction objects, one per matching DUR entry.
    """
    drug_set = {name.strip() for name in drug_names}
    results: list[Interaction] = []
    for entry in dur_data:
        drug_a = entry["drug_a"]
        drug_b = entry["drug_b"]
        if drug_a in drug_set and drug_b in drug_set:
            results.append(
                Interaction(
                    drug_a=drug_a,
                    drug_b=drug_b,
                    severity=entry["severity"],
                    reason=entry["reason"],
                    source=entry["source"],
                )
            )
    return results
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_dur_checker.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add samples/dur_sample.json src/pillcare/dur_checker.py tests/test_dur_checker.py
git commit -m "feat: add DUR 병용금기 checker with hardcoded sample data"
```

---

## Task 4: Citations Module

**Files:**
- Create: `src/pillcare/citations.py`
- Create: `tests/test_citations.py`

**Domain note**: Grounded RAG의 핵심은 모든 응답이 공공 DB 근거를 인용하도록 강제하는 것. 이 모듈은 Citation dataclass와 사용자에게 보여줄 출처 블록을 생성한다.

- [ ] **Step 1: Write failing tests**

Create `tests/test_citations.py`:

```python
"""Tests for the citations module."""

from pillcare.citations import Citation, format_citations


def test_format_citations_empty():
    assert format_citations([]) == ""


def test_format_citations_single():
    citations = [
        Citation(
            claim="타이레놀정 제품 정보",
            source_name="식약처 의약품 낱알식별 정보",
            url="https://www.data.go.kr/data/15075057/openapi.do",
            version="2024",
            accessed_at="2026-04-11T22:30:00",
        )
    ]
    result = format_citations(citations)
    assert "**출처:**" in result
    assert "식약처 의약품 낱알식별 정보" in result
    assert "2024" in result
    assert "2026-04-11T22:30:00" in result
    assert "https://www.data.go.kr/data/15075057/openapi.do" in result


def test_format_citations_multiple_numbered():
    citations = [
        Citation(
            claim="claim 1",
            source_name="식약처",
            url="https://a.example",
            version="2024",
            accessed_at="2026-04-11T22:00:00",
        ),
        Citation(
            claim="claim 2",
            source_name="심평원 DUR",
            url="https://b.example",
            version="2024-Q3",
            accessed_at="2026-04-11T22:00:01",
        ),
    ]
    result = format_citations(citations)
    assert "1. " in result
    assert "2. " in result
    assert result.index("식약처") < result.index("심평원 DUR")


def test_format_citations_deduplicates_same_source():
    """같은 source_name+version+url 조합은 1번만 표시된다."""
    citations = [
        Citation(
            claim="claim 1",
            source_name="식약처",
            url="https://a.example",
            version="2024",
            accessed_at="2026-04-11T22:00:00",
        ),
        Citation(
            claim="claim 2",
            source_name="식약처",
            url="https://a.example",
            version="2024",
            accessed_at="2026-04-11T22:00:05",
        ),
    ]
    result = format_citations(citations)
    assert result.count("식약처") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_citations.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pillcare.citations'`

- [ ] **Step 3: Implement `src/pillcare/citations.py`**

```python
"""Grounded RAG citation formatting.

All agent responses must cite their public DB sources. This module provides
the Citation dataclass and a formatter that produces a dedup'd numbered
source block suitable for appending to agent output.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    """A single grounding citation attached to an agent claim."""

    claim: str
    source_name: str
    url: str
    version: str
    accessed_at: str  # ISO datetime string


def format_citations(citations: list[Citation]) -> str:
    """Format citations as a numbered source block.

    Deduplicates citations that share the same (source_name, version, url)
    tuple — the deduplication key matches the displayed unit, so users
    see each distinct source exactly once.

    Args:
        citations: List of Citation objects gathered during an agent turn.

    Returns:
        A markdown-formatted source block, or empty string if input is empty.
    """
    if not citations:
        return ""

    seen: set[tuple[str, str, str]] = set()
    unique: list[Citation] = []
    for c in citations:
        key = (c.source_name, c.version, c.url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)

    lines = ["\n---\n**출처:**"]
    for i, c in enumerate(unique, 1):
        lines.append(
            f"{i}. [{c.source_name} {c.version}]({c.url}) — 조회: {c.accessed_at}"
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_citations.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pillcare/citations.py tests/test_citations.py
git commit -m "feat: add Citation dataclass and dedup'd formatter for Grounded RAG"
```

---

## Task 5: Claude Vision OCR Wrapper

**Files:**
- Create: `src/pillcare/vision.py`

**Domain note**: 약봉투/처방전 이미지에서 약물명·용량·복용 빈도를 추출한다. Claude Sonnet 4.6의 vision 기능을 사용. 이 모듈은 thin wrapper이므로 자동 테스트 대신 Task 8 end-to-end smoke test에서 검증한다.

- [ ] **Step 1: Implement `src/pillcare/vision.py`**

```python
"""Claude vision 기반 약봉투·처방전 OCR 래퍼.

Thin Claude SDK wrapper — 이미지 파일을 base64 인코딩하여 Claude에게 전달하고,
JSON 배열 형식의 약물 정보를 파싱한다. 실제 API 호출을 포함하므로 자동화된
단위 테스트 대신 Task 8 end-to-end smoke test에서 검증한다.
"""

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path

from anthropic import Anthropic


MODEL = "claude-sonnet-4-6"


@dataclass(frozen=True)
class ExtractedDrug:
    """A single drug extracted from a prescription image."""

    name: str
    dose: str | None
    frequency: str | None


EXTRACTION_PROMPT = """이 약봉투 또는 처방전 이미지에서 약물 정보를 추출하세요.

각 약물에 대해 다음 JSON 배열 형식으로만 응답하세요. 설명이나 다른 텍스트는 포함하지 마세요.

[
  {"name": "정확한 약물명", "dose": "용량 (예: 500mg)", "frequency": "복용 빈도 (예: 1일 3회)"}
]

- 약물명은 한국어 원문 그대로 추출하세요.
- 용량이나 빈도를 판독할 수 없으면 해당 필드를 null로 설정하세요.
- 이미지에서 식별 가능한 약물이 없으면 빈 배열 []을 반환하세요."""


def _encode_image(image_path: str | Path) -> tuple[str, str]:
    """Encode an image file to base64 and determine its media type."""
    path = Path(image_path)
    ext = path.suffix.lower().lstrip(".")
    if ext in ("jpg", "jpeg"):
        media_type = "image/jpeg"
    elif ext == "png":
        media_type = "image/png"
    elif ext == "webp":
        media_type = "image/webp"
    else:
        raise ValueError(f"Unsupported image format: {ext}")
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def extract_drugs_from_image(
    image_path: str | Path,
    client: Anthropic | None = None,
) -> list[ExtractedDrug]:
    """Extract drug information from a prescription image using Claude vision.

    Args:
        image_path: Path to a JPG/PNG/WEBP prescription image.
        client: Optional Anthropic client (for testing with mocks). If None,
                a new default Anthropic client is created.

    Returns:
        List of ExtractedDrug objects. Empty list if no drugs are identified
        or the response cannot be parsed.
    """
    client = client or Anthropic()
    image_data, media_type = _encode_image(image_path)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ],
    )

    # Claude may wrap the JSON in prose — extract the first JSON array
    text = "".join(block.text for block in response.content if block.type == "text")
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [
        ExtractedDrug(
            name=item["name"],
            dose=item.get("dose"),
            frequency=item.get("frequency"),
        )
        for item in items
        if isinstance(item, dict) and "name" in item
    ]
```

- [ ] **Step 2: Verify module imports cleanly**

Run: `uv run python -c "from pillcare.vision import extract_drugs_from_image, ExtractedDrug, MODEL; print(MODEL)"`
Expected: `claude-sonnet-4-6`

- [ ] **Step 3: Commit**

```bash
git add src/pillcare/vision.py
git commit -m "feat: add Claude vision OCR wrapper for prescription images"
```

---

## Task 6: Tool-Use Agent Orchestration

**Files:**
- Create: `src/pillcare/agent.py`
- Create: `tests/test_agent.py`

**Domain note**: Claude에 2개 tool(search_drug, check_dur)을 정의하고 tool_use loop를 구현한다. System prompt는 spec §7.2 언어 정책을 준수 — 판단·처방·진단 금지, 모든 응답에 의료진 확인 경로. 테스트는 Anthropic 클라이언트를 mock해서 tool_use → tool_result → end_turn 시퀀스를 검증.

- [ ] **Step 1: Write failing integration test**

Create `tests/test_agent.py`:

```python
"""Integration test for the agent tool-use loop with a mocked Anthropic client."""

from pathlib import Path
from unittest.mock import MagicMock
from types import SimpleNamespace

import pandas as pd
import pytest

from pillcare.agent import run_agent_text
from pillcare.citations import Citation


def _mk_text_block(text: str):
    return SimpleNamespace(type="text", text=text)


def _mk_tool_use_block(tool_id: str, name: str, input_data: dict):
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=input_data)


def _mk_response(stop_reason: str, content_blocks: list):
    return SimpleNamespace(stop_reason=stop_reason, content=content_blocks)


@pytest.fixture
def small_medicines_db(fixtures_dir: Path) -> pd.DataFrame:
    from pillcare.drug_matcher import load_medicines
    return load_medicines(fixtures_dir / "small_medicines.csv")


@pytest.fixture
def dur_sample(samples_dir: Path) -> list[dict]:
    from pillcare.dur_checker import load_dur_sample
    return load_dur_sample(samples_dir / "dur_sample.json")


def test_run_agent_text_single_turn_no_tools(small_medicines_db, dur_sample):
    """Claude returns end_turn immediately without any tool calls."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mk_response(
        stop_reason="end_turn",
        content_blocks=[_mk_text_block("확인된 약물이 없습니다. 의료진에게 확인을 요청하세요.")],
    )

    result = run_agent_text(
        drug_names=[],
        medicines_db=small_medicines_db,
        dur_data=dur_sample,
        client=mock_client,
    )

    assert "의료진" in result["response"]
    assert result["citations"] == []
    assert mock_client.messages.create.call_count == 1


def test_run_agent_text_tool_use_search_drug(small_medicines_db, dur_sample):
    """Agent calls search_drug once, then returns a final text response."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mk_response(
            stop_reason="tool_use",
            content_blocks=[
                _mk_tool_use_block(
                    "tool_1",
                    "search_drug",
                    {"drug_name": "타이레놀정500밀리그램(아세트아미노펜)"},
                ),
            ],
        ),
        _mk_response(
            stop_reason="end_turn",
            content_blocks=[
                _mk_text_block("타이레놀은 한국얀센에서 제조합니다. 의료진에게 확인을 요청하세요."),
            ],
        ),
    ]

    result = run_agent_text(
        drug_names=["타이레놀정500밀리그램(아세트아미노펜)"],
        medicines_db=small_medicines_db,
        dur_data=dur_sample,
        client=mock_client,
    )

    assert "타이레놀" in result["response"]
    assert len(result["citations"]) >= 1
    assert any(c.source_name == "식약처 의약품 낱알식별 정보" for c in result["citations"])
    assert mock_client.messages.create.call_count == 2


def test_run_agent_text_tool_use_check_dur_finds_interaction(small_medicines_db, dur_sample):
    """Agent calls check_dur and receives a 병용금기 hit."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mk_response(
            stop_reason="tool_use",
            content_blocks=[
                _mk_tool_use_block(
                    "tool_1",
                    "check_dur",
                    {
                        "drug_names": [
                            "와파린정2밀리그람",
                            "아스피린프로텍트정100밀리그램(아세틸살리실산)",
                        ]
                    },
                )
            ],
        ),
        _mk_response(
            stop_reason="end_turn",
            content_blocks=[
                _mk_text_block("⚠️ 병용금기 발견. 의료진에게 확인을 요청하세요."),
            ],
        ),
    ]

    result = run_agent_text(
        drug_names=[
            "와파린정2밀리그람",
            "아스피린프로텍트정100밀리그램(아세틸살리실산)",
        ],
        medicines_db=small_medicines_db,
        dur_data=dur_sample,
        client=mock_client,
    )

    assert "병용금기" in result["response"]
    assert any(c.source_name == "심평원 DUR" for c in result["citations"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pillcare.agent'`

- [ ] **Step 3: Implement `src/pillcare/agent.py`**

```python
"""Tool-use agent orchestration (Claude Sonnet 4.6 + 2 tools).

Given a list of drug names extracted from a prescription image, run a Claude
tool-use loop that orchestrates search_drug (식약처 DB) and check_dur (심평원 DUR)
to produce a grounded response with citations.

Safety boundaries (spec §7.2 언어 정책):
- No diagnosis, prescription, or dose advice.
- All responses must cite public DB sources.
- Defer to clinician on any interaction finding.
"""

from datetime import datetime
from typing import Any

import pandas as pd
from anthropic import Anthropic

from pillcare.citations import Citation, format_citations
from pillcare.drug_matcher import match_drug
from pillcare.dur_checker import check_interactions


MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """당신은 필케어(PillCare) — 한국 복약 정보 안내 AI 에이전트입니다.

원칙 (절대 준수):
1. 의료 판단을 하지 마세요. 진단·처방·용량 조절은 금지합니다.
2. 모든 주장에는 공공 DB 출처가 있어야 하며, 근거 없는 주장은 하지 마세요.
3. 상호작용 또는 주의사항을 발견하면 사용자에게 "의료진에게 확인을 요청하세요"라고 안내하세요.
4. 확신이 없으면 "의료진에게 확인을 요청하세요"라고 답하세요.
5. "복약지도"라는 표현은 사용하지 마세요. 대신 "복약 정보 안내"라고 하세요.

사용 가능한 도구:
- search_drug: 식약처 낱알식별 DB에서 약물명으로 검색
- check_dur: 심평원 DUR 기준으로 약물 리스트의 병용금기/병용주의 확인

작업 흐름:
1. 먼저 각 약물을 search_drug로 조회하여 공식 정보를 확보하세요.
2. 그 다음 check_dur로 전체 약물 리스트의 상호작용을 확인하세요.
3. 결과를 종합해 사용자에게 명확히 안내하고, 의료진 확인 경로를 제시하세요."""


TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_drug",
        "description": (
            "식약처 낱알식별 DB에서 약물명으로 검색하여 표준 제품 정보를 반환합니다. "
            "정확한 한국어 약물명을 입력으로 받습니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {
                    "type": "string",
                    "description": "검색할 약물명 (한국어)",
                }
            },
            "required": ["drug_name"],
        },
    },
    {
        "name": "check_dur",
        "description": (
            "심평원 DUR 기준으로 주어진 약물 리스트의 병용금기 및 병용주의를 확인합니다. "
            "두 개 이상의 약물을 동시에 전달하면 모든 쌍에 대해 검사합니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "DUR 검사 대상 약물명 리스트 (한국어)",
                }
            },
            "required": ["drug_names"],
        },
    },
]


def _execute_tool(
    name: str,
    tool_input: dict,
    medicines_db: pd.DataFrame,
    dur_data: list[dict],
    citations: list[Citation],
) -> str:
    """Execute a tool call, append any grounding citations, and return the tool result text."""
    now = datetime.now().isoformat(timespec="seconds")

    if name == "search_drug":
        query = tool_input["drug_name"]
        match = match_drug(query, medicines_db)
        if match is None:
            return f"검색 결과 없음: {query}"
        citations.append(
            Citation(
                claim=f"{match.item_name} 제품 정보",
                source_name="식약처 의약품 낱알식별 정보",
                url="https://www.data.go.kr/data/15075057/openapi.do",
                version="2024",
                accessed_at=now,
            )
        )
        return (
            f"제품명: {match.item_name}\n"
            f"제조사: {match.entp_name}\n"
            f"품목일련번호: {match.item_seq}\n"
            f"EDI 코드: {match.edi_code or '미등록'}"
        )

    if name == "check_dur":
        drug_names = tool_input["drug_names"]
        interactions = check_interactions(drug_names, dur_data)
        if not interactions:
            return "병용금기/병용주의 발견 없음"
        citations.append(
            Citation(
                claim="DUR 병용금기/병용주의 확인",
                source_name="심평원 DUR",
                url="https://www.data.go.kr/data/15127983/fileData.do",
                version="2024",
                accessed_at=now,
            )
        )
        lines = []
        for i in interactions:
            lines.append(f"[{i.severity}] {i.drug_a} + {i.drug_b}\n  사유: {i.reason}")
        return "\n".join(lines)

    return f"알 수 없는 도구: {name}"


def run_agent_text(
    drug_names: list[str],
    medicines_db: pd.DataFrame,
    dur_data: list[dict],
    client: Anthropic | None = None,
    max_iterations: int = 10,
) -> dict:
    """Run the tool-use agent loop on a list of already-extracted drug names.

    This entry point skips the vision step — the UI uses run_agent for the
    full pipeline, while tests and offline flows can call this directly.

    Args:
        drug_names: Drug names as extracted by VLM OCR (e.g., via vision.extract_drugs_from_image).
        medicines_db: medicines DataFrame from drug_matcher.load_medicines.
        dur_data: DUR sample list from dur_checker.load_dur_sample.
        client: Optional Anthropic client (injectable for testing).
        max_iterations: Maximum tool-use loop iterations before giving up.

    Returns:
        {"response": str, "citations": list[Citation]}
    """
    client = client or Anthropic()

    user_message = (
        "다음 약물이 약봉투·처방전에서 인식되었습니다:\n"
        + "\n".join(f"- {name}" for name in drug_names)
        + "\n\n각 약물의 공식 정보를 조회하고, 전체 조합의 DUR 상호작용을 확인한 뒤, "
        "필요한 주의사항을 근거와 함께 안내해주세요."
    )

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
    citations: list[Citation] = []

    for _ in range(max_iterations):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            return {
                "response": final_text + format_citations(citations),
                "citations": citations,
            }

        if response.stop_reason == "tool_use":
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_result_text = _execute_tool(
                        block.name,
                        block.input,
                        medicines_db,
                        dur_data,
                        citations,
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result_text,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop_reason — break and return whatever we have
        break

    return {
        "response": "에이전트 루프가 최대 반복 횟수에 도달했습니다. 의료진에게 확인을 요청하세요.",
        "citations": citations,
    }


def run_agent(
    image_path: str,
    medicines_db: pd.DataFrame,
    dur_data: list[dict],
    client: Anthropic | None = None,
) -> dict:
    """Run the full pipeline: vision OCR → tool-use agent → grounded response.

    Args:
        image_path: Path to a prescription image.
        medicines_db: medicines DataFrame.
        dur_data: DUR sample list.
        client: Optional Anthropic client.

    Returns:
        {"extracted_drugs": list[ExtractedDrug], "response": str, "citations": list[Citation]}
    """
    from pillcare.vision import extract_drugs_from_image

    client = client or Anthropic()
    extracted = extract_drugs_from_image(image_path, client)
    drug_names = [d.name for d in extracted]

    text_result = run_agent_text(
        drug_names=drug_names,
        medicines_db=medicines_db,
        dur_data=dur_data,
        client=client,
    )

    return {
        "extracted_drugs": extracted,
        "response": text_result["response"],
        "citations": text_result["citations"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_agent.py -v`
Expected: 3 passed.

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: 18 passed (5 drug_matcher + 6 dur_checker + 4 citations + 3 agent).

- [ ] **Step 6: Commit**

```bash
git add src/pillcare/agent.py tests/test_agent.py
git commit -m "feat: add Claude tool-use agent loop with Grounded citations"
```

---

## Task 7: Streamlit Demo UI

**Files:**
- Create: `src/pillcare/app.py`

**Domain note**: Streamlit single-page app — 이미지 업로더, agent 실행 버튼, 응답 표시, 출처 블록 표시. 영상 1:05-1:55 구간에서 이 화면을 녹화한다. 자동 테스트는 생략하고 Task 8에서 수동 smoke test.

- [ ] **Step 1: Implement `src/pillcare/app.py`**

```python
"""필케어 POC Streamlit 데모.

단일 페이지 UI: 약봉투 이미지 업로드 → Claude 에이전트 실행 → 응답 + 출처 표시.

실행:
    uv run streamlit run src/pillcare/app.py
"""

from pathlib import Path

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from pillcare.agent import run_agent
from pillcare.drug_matcher import load_medicines
from pillcare.dur_checker import load_dur_sample


load_dotenv()

REPO_ROOT = Path(__file__).parent.parent.parent
MEDICINES_CSV = REPO_ROOT / "medicines.csv"
DUR_SAMPLE = REPO_ROOT / "samples" / "dur_sample.json"


@st.cache_resource
def _load_resources():
    """Load medicines DB, DUR sample, and create a cached Anthropic client."""
    medicines_db = load_medicines(MEDICINES_CSV)
    dur_data = load_dur_sample(DUR_SAMPLE)
    client = Anthropic()
    return medicines_db, dur_data, client


def main() -> None:
    st.set_page_config(page_title="필케어 (PillCare) POC", page_icon="💊", layout="centered")
    st.title("💊 필케어 (PillCare)")
    st.caption("통합 약물 지식 그래프 기반 자율 복약 관리 AI 에이전트 — POC")

    st.markdown(
        "약봉투 또는 처방전 이미지를 업로드하면, 필케어 에이전트가 식약처 낱알식별 DB와 "
        "심평원 DUR 을 조회하여 공공 DB 근거와 함께 결과를 안내합니다."
    )
    st.info(
        "⚠️ 본 서비스는 정보 안내용입니다. 판단·처방·진단을 수행하지 않으며, "
        "모든 복약 결정은 반드시 의료진에게 확인하세요."
    )

    uploaded = st.file_uploader(
        "약봉투/처방전 이미지 업로드",
        type=["jpg", "jpeg", "png", "webp"],
    )

    if uploaded is None:
        st.stop()

    temp_path = REPO_ROOT / "samples" / "_uploaded_temp.jpg"
    temp_path.write_bytes(uploaded.getvalue())

    st.image(uploaded, caption="업로드된 이미지", use_column_width=True)

    if st.button("필케어 에이전트 실행", type="primary"):
        medicines_db, dur_data, client = _load_resources()
        with st.spinner("에이전트가 추론 중입니다..."):
            result = run_agent(
                image_path=temp_path,
                medicines_db=medicines_db,
                dur_data=dur_data,
                client=client,
            )

        st.subheader("🔍 인식된 약물")
        if not result["extracted_drugs"]:
            st.warning("이미지에서 약물을 식별하지 못했습니다.")
        else:
            for drug in result["extracted_drugs"]:
                dose = f" · {drug.dose}" if drug.dose else ""
                freq = f" · {drug.frequency}" if drug.frequency else ""
                st.write(f"- **{drug.name}**{dose}{freq}")

        st.subheader("📋 에이전트 응답")
        st.markdown(result["response"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify import smoke**

Run: `uv run python -c "from pillcare import app; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/pillcare/app.py
git commit -m "feat: add Streamlit single-page demo UI"
```

---

## Task 8: End-to-End Demo + Screenshots

**Files:**
- Create: `samples/prescription_sample.jpg` (team supplies — a real or mock 약봉투 photo)
- Create: `docs/superpowers/demo-screenshots/` (screenshots captured during this task)

**Domain note**: 이 task는 실제 Claude API를 호출하는 수동 smoke test다. 예선 영상 1:05-1:55 구간과 제안서 P3 POC 스크린샷의 원본을 만든다.

- [ ] **Step 1: Team provides sample prescription image**

Place a real 약봉투/처방전 photo (JPG) at `samples/prescription_sample.jpg`. The image should contain at least 2-3 of the medicines present in `samples/dur_sample.json` so the DUR checker can demonstrate a finding. Suitable candidates (from DUR sample):
- 와파린정2밀리그람 + 아스피린프로텍트정100밀리그램
- 페라트라정2.5밀리그램 + 타목시펜정20밀리그램
- 가스디알정50밀리그램 + 테트라사이클린캡슐250밀리그램

If a real photo is not available, the team creates a mock by typing the drug names into a plain document and screenshotting it with clear white background.

- [ ] **Step 2: Set ANTHROPIC_API_KEY**

Run:
```bash
cp .env.example .env
# Edit .env and fill in the real key
```

Expected: `.env` file with a valid `ANTHROPIC_API_KEY=sk-ant-...`

- [ ] **Step 3: Run Streamlit demo**

Run: `uv run streamlit run src/pillcare/app.py`
Expected: Streamlit opens at `http://localhost:8501`.

- [ ] **Step 4: Execute full scenario manually**

In the browser:
1. Upload `samples/prescription_sample.jpg`
2. Click "필케어 에이전트 실행"
3. Wait for the spinner to complete
4. Verify:
   - Extracted drugs section lists the drugs in the image
   - Agent response includes at least one DUR finding with "의료진에게 확인" phrasing
   - Source block at the bottom lists both "식약처 의약품 낱알식별 정보" and "심평원 DUR" with clickable URLs and timestamps

If any verification fails, debug (check Claude API errors in Streamlit terminal, inspect drug_matcher scores with a temporary log line) and re-run.

- [ ] **Step 5: Capture screenshots for proposal P3 and video S4**

Create `docs/superpowers/demo-screenshots/`:
```bash
mkdir -p docs/superpowers/demo-screenshots
```

Capture 5 screenshots at 1920x1080 or native resolution:
1. `01_upload.png` — upload page with sample image visible
2. `02_extracted.png` — extracted drugs list after agent run
3. `03_response.png` — full agent response with DUR warning
4. `04_citations.png` — scrolled to source block showing 2+ citations
5. `05_composite.png` — single screenshot showing the full result page (for P3 1/4-page use)

Save all to `docs/superpowers/demo-screenshots/`.

- [ ] **Step 6: Document the demo run in a log file**

Create `docs/superpowers/demo-screenshots/demo-log.md`:

```markdown
# POC Demo Run Log

**Date:** 2026-04-11
**Input image:** samples/prescription_sample.jpg
**Extracted drugs:** (list from the run)
**DUR findings:** (list from the run)
**Claude model:** claude-sonnet-4-6
**Citations produced:** 2 (식약처 의약품 낱알식별 정보, 심평원 DUR)
**Observed latency:** ~X seconds
**Notes for video/proposal:** (any gotchas)
```

- [ ] **Step 7: Commit**

```bash
git add samples/prescription_sample.jpg docs/superpowers/demo-screenshots/
git commit -m "feat: end-to-end POC demo + screenshots for proposal P3 and video S4"
```

---

## Task 9: README + Demo Instructions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Implement `README.md`**

```markdown
# 필케어 (PillCare) POC

> **통합 약물 지식 그래프 기반 자율 복약 관리 AI 에이전트 — 예선 제출용 POC**

한국 AI 해커톤 예선 제안서의 단일 시나리오 POC. 약봉투 이미지를 입력으로 받아 식약처 낱알식별 DB와 심평원 DUR 을 조회하고, Claude 에이전트가 tool-use 로 근거 기반 응답을 생성한다.

## 시연 시나리오

1. 사용자가 약봉투 사진을 업로드
2. Claude Vision 이 약물명·용량·빈도 추출
3. 식약처 낱알식별 DB 에 fuzzy match 로 품목코드 확정
4. 심평원 DUR 샘플과 대조해 병용금기/병용주의 탐지
5. Claude tool-use 에이전트가 공공 DB 근거를 인용한 응답 생성

## 설치 및 실행

### 요구 사항
- Python 3.11 (uv 로 관리)
- Anthropic API Key

### 1. 의존성 설치

```bash
uv python install 3.11
uv sync
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 ANTHROPIC_API_KEY 를 입력
```

### 3. 테스트 실행

```bash
uv run pytest -v
```

4개 모듈(drug_matcher, dur_checker, citations, agent) 총 18 개 테스트가 통과해야 한다.

### 4. Streamlit 데모 실행

```bash
uv run streamlit run src/pillcare/app.py
```

브라우저에서 `http://localhost:8501` 접속 → 약봉투 이미지 업로드 → "필케어 에이전트 실행" 클릭.

## 프로젝트 구조

```
src/pillcare/
├── drug_matcher.py    # 식약처 낱알식별 DB fuzzy match (pure function)
├── dur_checker.py     # 심평원 DUR 병용금기 체크 (pure function)
├── citations.py       # Grounded RAG citation 포매터
├── vision.py          # Claude vision OCR 래퍼
├── agent.py           # Tool-use 에이전트 오케스트레이션
└── app.py             # Streamlit 데모 UI

samples/
├── dur_sample.json           # 하드코딩된 DUR 병용금기 샘플
└── prescription_sample.jpg   # 데모용 약봉투 이미지

tests/                # pytest 단위·통합 테스트
```

## 안전 경계 (Scope A)

필케어는 **정보 안내 + 기록 + 문서화 + 의료진 확인 경로 제공**만 수행합니다. 다음 기능은 배제되어 있습니다:

- ❌ 진단, 처방, 용량 조절
- ❌ 의료 판단
- ❌ 근거 없는 주장

모든 응답은 공공 DB 근거를 인용하며, 상호작용 발견 시 "의료진에게 확인을 요청하세요"로 귀결됩니다.

## 데이터 소스 (Zero-License-Risk Stack)

| 소스 | 라이선스 | 용도 |
|---|---|---|
| 식약처 의약품 낱알식별 정보 | 이용허락범위 제한 없음 | 약물 표준 정보 |
| 심평원 DUR (샘플) | KOGL Type 1 | 병용금기/병용주의 |
| Anthropic Claude Sonnet 4.6 | 상용 API | Vision OCR + 에이전트 추론 |

## 리서치 참조

상세한 설계·리서치는 `docs/superpowers/specs/2026-04-11-pillcare-design.md` 및 `research/track-*.md` 파일 참조.

## 라이선스

Internal POC — not yet licensed for redistribution.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with POC demo instructions"
```

---

## Self-Review

*(Performed by the plan author immediately after writing the plan.)*

### 1. Spec Coverage

Spec §8 (POC 스펙) 의 모든 요소가 task 에 매핑됨:

- [x] Python 3.11 + uv → Task 1
- [x] anthropic SDK (Claude Sonnet 4.6, tool-use) → Task 5 (vision), Task 6 (agent)
- [x] medicines.csv 로컬 로드 → Task 2 (`load_medicines`)
- [x] 심평원 DUR 샘플 파일 → Task 3 (`samples/dur_sample.json`)
- [x] Streamlit 단일 페이지 → Task 7 (`app.py`)
- [x] 5단계 시연 시나리오 (약봉투 → OCR → 매칭 → DUR → 응답+출처) → Task 8 end-to-end
- [x] 스크린샷 3-4장 → Task 8 Step 5
- [x] 언어 정책 준수 (§7.2: 복약지도·처방 제안·판단·진단 금지) → Task 6 SYSTEM_PROMPT 및 README Safety 섹션

Spec §7.3 Q&A 답변 뱅크 항목 중 "POC는 진짜 돌아가나요?" 는 Task 8 demo log로 증빙 가능.

### 2. Placeholder Scan

Red flag 검색:
- "TBD" / "TODO" / "implement later" / "fill in details" — none found
- "Add appropriate error handling" / "add validation" — none found
- "Write tests for the above" without code — none found
- "Similar to Task N" — none found
- Code steps without actual code — none found

Task 1 Step 3 (의존성 버전 검증) 는 context7 명령을 concrete 하게 기술, 버전만 환경별 dependent 로 명시. Task 8 Step 1 의 "team supplies image" 는 사람이 제공하는 입력이므로 placeholder 가 아님.

### 3. Type Consistency

모듈 간 타입·함수명 일관성 체크:

- `DrugMatch` (drug_matcher.py): Task 2 정의, Task 6 `_execute_tool` 에서 사용 ✅
- `Interaction` (dur_checker.py): Task 3 정의, Task 6 에서 iterate ✅
- `Citation` (citations.py): Task 4 정의, Task 6 `_execute_tool` 에서 append, Task 7 에서 format ✅
- `ExtractedDrug` (vision.py): Task 5 정의, Task 6 `run_agent` 에서 사용, Task 7 Streamlit 표시 ✅
- `load_medicines` / `match_drug`: Task 2 에서 정의, Task 6 테스트 및 Task 7 Streamlit 에서 사용 ✅
- `load_dur_sample` / `check_interactions`: Task 3 에서 정의, Task 6 테스트 및 Task 7 Streamlit 에서 사용 ✅
- `extract_drugs_from_image`: Task 5 에서 정의, Task 6 `run_agent` 에서 사용 ✅
- `run_agent_text` / `run_agent`: Task 6 에서 정의, Task 7 Streamlit 에서 `run_agent` 호출 ✅
- `format_citations`: Task 4 에서 정의, Task 6 `run_agent_text` 에서 호출 ✅
- Model ID `claude-sonnet-4-6`: Task 5 `vision.py` 와 Task 6 `agent.py` 에서 일관 ✅

### Issues Fixed Inline

없음 — 위 체크에서 불일치 발견되지 않음.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-11-pillcare-poc.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for disciplined TDD: each task's tests get a clean context window.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Good if you want to see every command executed in the main conversation.

**Which approach?**
