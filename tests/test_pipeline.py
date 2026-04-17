"""Tests for LangGraph pipeline with mocked LLM."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pillcare.db_builder import build_db
from pillcare.schemas import DrugGuidanceOutput, DrugSectionOutput
from pillcare.xml_parser import parse_nb_doc
from pillcare.pipeline import build_pipeline, run_pipeline
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
                (
                    item["ITEM_SEQ"],
                    s.section_type,
                    s.section_title,
                    s.section_text,
                    s.section_order,
                ),
            )
    conn.execute(
        "INSERT INTO dur_pairs VALUES (?,?,?,?,?,?)",
        (
            "M040702",
            "이부프로펜",
            "M175201",
            "클로르페니라민말레산염",
            "중추신경 억제 증강",
            "20200101",
        ),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_records():
    return [
        {
            "drug_name": "리도펜연질캡슐(이부프로펜)",
            "drug_code": "649301290",
            "department": "가정의학과",
        },
        {"drug_name": "코대원정", "drug_code": None, "department": "내과"},
    ]


@pytest.fixture
def mock_guidance_output():
    return DrugGuidanceOutput(
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
                section_name="용법용량",
                content="1회 1캡슐, 1일 3회 식후 복용하십시오.",
                source_tier="T1:허가정보",
            ),
            DrugSectionOutput(
                section_name="주의사항",
                content="위장출혈 주의. 의사 또는 약사와 상담하십시오.",
                source_tier="T1:허가정보",
            ),
            DrugSectionOutput(
                section_name="상호작용",
                content="이부프로펜과 클로르페니라민 병용 시 중추신경 억제 증강. 의사 또는 약사와 상담하십시오.",
                source_tier="T1:DUR",
            ),
        ],
    )


def _make_mock_llm(guidance_output: DrugGuidanceOutput):
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = guidance_output
    return mock_llm


def _make_mock_critic_llm():
    """Mock critic LLM that always returns PASS verdict.

    Used by pipeline tests so they don't need to instantiate the real
    Claude Haiku client (which requires ANTHROPIC_API_KEY).
    """
    from pillcare.schemas import CriticOutput, CriticVerdict

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = CriticOutput(verdict=CriticVerdict.PASS)
    return mock_llm


def test_deterministic_nodes(full_db, sample_records):
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
    state = {"raw_records": sample_records, "errors": []}
    state.update(make_match_node(str(full_db))(state))
    result = make_dur_node(str(full_db))(state)
    cross = [a for a in result["dur_alerts"] if a["cross_clinic"]]
    assert len(cross) >= 1


def test_build_pipeline_compiles(full_db, mock_guidance_output):
    mock_llm = _make_mock_llm(mock_guidance_output)
    graph = build_pipeline(
        db_path=str(full_db), llm=mock_llm, critic_llm=_make_mock_critic_llm()
    )
    assert graph is not None


def test_structured_output_conversion(mock_guidance_output):
    guidance = mock_guidance_output.to_drug_guidance()
    assert "명칭" in guidance.sections
    assert "효능효과" in guidance.sections
    assert "주의사항" in guidance.sections
    assert guidance.sections["효능효과"].source_tier.value == "T1:e약은요"


def test_generate_with_mock_llm(full_db, sample_records, mock_guidance_output):
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
    mock_llm = _make_mock_llm(mock_guidance_output)
    result = run_pipeline(
        db_path=str(full_db),
        llm=mock_llm,
        records=sample_records,
        profile_id="test-user",
        critic_llm=_make_mock_critic_llm(),
    )
    assert result["guidance_result"] is not None
    assert result["profile_id"] == "test-user"
    assert len(result["matched_drugs"]) == 2
    assert len(result["dur_alerts"]) >= 1
    # Happy path should not have critical errors
    critical_errors = [
        e for e in result.get("errors", []) if e.startswith("[CRITICAL]")
    ]
    assert len(critical_errors) == 0


def test_should_retry_on_critical():
    from pillcare.pipeline import _should_retry

    assert _should_retry({"_last_verify_errors": [], "_retry_count": 0}) == "done"
    assert (
        _should_retry(
            {"_last_verify_errors": ["[CRITICAL] T4 비율 초과"], "_retry_count": 0}
        )
        == "generate"
    )
    assert (
        _should_retry(
            {"_last_verify_errors": ["[CRITICAL] T4 비율 초과"], "_retry_count": 1}
        )
        == "generate"
    )
    assert (
        _should_retry(
            {"_last_verify_errors": ["[CRITICAL] T4 비율 초과"], "_retry_count": 2}
        )
        == "done"
    )
    assert (
        _should_retry(
            {"_last_verify_errors": ["출처 태그 누락: A / 명칭"], "_retry_count": 0}
        )
        == "done"
    )
    # Critic retry verdict should trigger retry even without CRITICAL errors
    assert (
        _should_retry(
            {
                "_last_verify_errors": [],
                "_retry_count": 0,
                "critic_output": {"verdict": "retry", "critical_errors": ["..."]},
            }
        )
        == "generate"
    )
    # Critic PASS verdict keeps retry gated by _MAX_RETRIES
    assert (
        _should_retry(
            {
                "_last_verify_errors": [],
                "_retry_count": 0,
                "critic_output": {"verdict": "pass"},
            }
        )
        == "done"
    )


def test_generate_fallback_on_llm_error(full_db, sample_records):
    """Generate node creates minimal fallback guidance when LLM fails."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_structured.invoke.side_effect = Exception("LLM timeout")

    from pillcare.pipeline import _make_generate_node

    state = {"raw_records": sample_records, "errors": [], "_retry_count": 0}
    state.update(make_match_node(str(full_db))(state))
    state.update(make_dur_node(str(full_db))(state))
    state.update(make_collect_node(str(full_db))(state))

    gen_node = _make_generate_node(mock_llm)
    result = gen_node(state)

    assert result["guidance_result"] is not None
    assert any("[ERROR]" in e for e in result["errors"])


def test_verify_node_with_no_result():
    """Verify node handles missing guidance_result."""
    from pillcare.pipeline import _verify_node

    result = _verify_node({"guidance_result": None, "_retry_count": 0})
    assert "[CRITICAL] 생성 결과 없음" in result["errors"]
    assert "[CRITICAL] 생성 결과 없음" in result["_last_verify_errors"]
    assert result["_retry_count"] == 1
