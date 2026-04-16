"""Tests for LangGraph pipeline with mocked LLM."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pillcare.db_builder import build_db
from pillcare.xml_parser import parse_nb_doc
from pillcare.pipeline import build_pipeline, run_pipeline, _parse_drug_guidance, GraphState
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


def test_build_pipeline_compiles(full_db):
    """Pipeline compiles without error."""
    graph = build_pipeline(db_path=str(full_db), llm=MagicMock())
    assert graph is not None


def test_parse_drug_guidance():
    """Parser extracts sections and detects source tiers correctly."""
    text = (
        "### 1. 명칭\n[T1:허가정보] 리도펜연질캡슐 (이부프로펜 200mg)\n\n"
        "### 3. 효능효과\n[T1:e약은요] 감기 발열 통증에 사용합니다.\n\n"
        "### 7. 주의사항\n[T1:허가정보] 위장출혈 주의. 의사 또는 약사와 상담하십시오.\n"
    )
    guidance = _parse_drug_guidance("리도펜연질캡슐", text)
    assert "명칭" in guidance.sections
    assert "효능효과" in guidance.sections
    assert "주의사항" in guidance.sections
    assert guidance.sections["효능효과"].source_tier.value == "T1:e약은요"


def test_generate_with_mock_llm(full_db, sample_records):
    """Generate node produces guidance with mocked LLM response."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = (
        "### 1. 명칭\n[T1:허가정보] 리도펜연질캡슐 (이부프로펜 200mg)\n\n"
        "### 3. 효능효과\n[T1:e약은요] 감기 발열 통증에 사용합니다.\n\n"
        "### 7. 주의사항\n[T1:허가정보] 위장출혈. 의사 또는 약사와 상담하십시오.\n\n"
        "### 8. 상호작용\n[T1:DUR] 이부프로펜과 클로르페니라민 병용 시 중추신경 억제 증강. 의사 또는 약사와 상담하십시오.\n"
    )
    mock_llm.invoke.return_value = mock_response

    # Test the generate node directly (verify node depends on guardrails -- Task 11)
    from pillcare.pipeline import _make_generate_node

    state = {"raw_records": sample_records, "errors": [], "_retry_count": 0}
    state.update(make_match_node(str(full_db))(state))
    state.update(make_dur_node(str(full_db))(state))
    state.update(make_collect_node(str(full_db))(state))

    gen_node = _make_generate_node(mock_llm)
    result = gen_node(state)

    assert result["guidance_result"] is not None
    assert mock_llm.invoke.call_count >= 1


def test_full_pipeline_with_mock_llm(full_db, sample_records):
    """Full pipeline runs end-to-end with mocked LLM (verify gracefully handles missing guardrails)."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = (
        "### 1. 명칭\n[T1:허가정보] 테스트 약물\n\n"
        "### 3. 효능효과\n[T1:e약은요] 테스트 효능.\n"
    )
    mock_llm.invoke.return_value = mock_response

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
