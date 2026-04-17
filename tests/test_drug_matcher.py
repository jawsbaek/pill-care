"""Tests for 4-phase drug matcher."""

import json
from pathlib import Path

import pytest

from pillcare.db_builder import build_db
from pillcare.drug_matcher import match_drug, extract_ingr_codes


@pytest.fixture
def db_path(tmp_path: Path, fixtures_dir: Path) -> Path:
    with open(fixtures_dir / "small_permit.json", encoding="utf-8") as f:
        permit = json.load(f)
    with open(fixtures_dir / "small_easy.json", encoding="utf-8") as f:
        easy = json.load(f)
    return build_db(tmp_path / "test.db", permit_data=permit, easy_data=easy)


def test_match_by_edi_code(db_path):
    result = match_drug(db_path, "아무약이름", edi_code="649301290")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score == 100


def test_match_exact_name(db_path):
    result = match_drug(db_path, "리도펜연질캡슐(이부프로펜)")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score == 100


def test_match_fts5_substring(db_path):
    result = match_drug(db_path, "리도펜")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score >= 80


def test_match_fuzzy_partial(db_path):
    result = match_drug(db_path, "리도펜연질캡슐")
    assert result is not None
    assert result.item_seq == "199701416"
    assert result.score >= 70


def test_match_returns_none_for_unknown(db_path):
    result = match_drug(db_path, "존재하지않는약물XYZ")
    assert result is None


def test_extract_ingr_codes_single():
    codes = extract_ingr_codes("[M040702]이부프로펜")
    assert codes == ["M040702"]


def test_extract_ingr_codes_multi():
    codes = extract_ingr_codes(
        "[M175201]클로르페니라민말레산염|[M146801]디히드로코데인타르타르산염"
    )
    assert codes == ["M175201", "M146801"]


def test_extract_ingr_codes_empty():
    assert extract_ingr_codes("") == []
    assert extract_ingr_codes(None) == []


def test_match_returns_ingr_codes(db_path):
    result = match_drug(db_path, "코대원정")
    assert result is not None
    assert result.item_seq == "200500001"
    assert len(result.ingr_codes) == 2
    assert "M175201" in result.ingr_codes
    assert "M146801" in result.ingr_codes
