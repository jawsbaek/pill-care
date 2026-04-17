"""Tests for 4-phase drug matcher."""

import inspect
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


# --- A3: Ingredient synonym expansion + dose-exact guard -------------------


def test_expand_query_with_synonyms_english_to_korean():
    from pillcare.drug_matcher import expand_query_with_synonyms

    queries = expand_query_with_synonyms("acetaminophen 500mg")
    joined = " ".join(queries)
    assert any("아세트아미노펜" in q for q in queries), (
        f"expected Korean synonym in {queries!r}"
    )
    # Dose suffix must be preserved in the rewritten query
    assert "500mg" in joined


def test_expand_query_with_synonyms_korean_to_english():
    from pillcare.drug_matcher import expand_query_with_synonyms

    queries = expand_query_with_synonyms("아세트아미노펜 500mg")
    joined = " ".join(queries).lower()
    assert "acetaminophen" in joined or "paracetamol" in joined


def test_expand_query_returns_original_when_no_synonym():
    from pillcare.drug_matcher import expand_query_with_synonyms

    queries = expand_query_with_synonyms("some-unknown-drug-xyz-123")
    assert "some-unknown-drug-xyz-123" in queries


def test_match_drug_default_min_score_is_85():
    sig = inspect.signature(match_drug)
    assert sig.parameters["min_score"].default == 85


def test_dose_exact_guard_rejects_mismatched_dose():
    """When query has '500mg', candidate with '160mg' must not pass."""
    from pillcare.drug_matcher import _dose_matches

    assert _dose_matches("타이레놀 500mg", "타이레놀정 500mg") is True
    assert _dose_matches("타이레놀 500mg", "타이레놀정 160mg") is False
    # no dose in query → pass regardless of candidate
    assert _dose_matches("아스피린", "아스피린장용정 100mg") is True
    # query has dose but candidate has none → must not pass
    assert _dose_matches("타이레놀 500mg", "타이레놀정") is False
    # handle decimals and different units
    assert _dose_matches("약 0.5g", "약 0.5g 정") is True


def test_dose_matches_unit_normalization_g_to_mg():
    from pillcare.drug_matcher import _dose_matches

    assert _dose_matches("타이레놀 500mg", "타이레놀 0.5g") is True
    assert _dose_matches("메트포르민 1g", "메트포르민 1000mg") is True


def test_dose_matches_mcg_to_mg():
    from pillcare.drug_matcher import _dose_matches

    # 500mcg = 0.5mg
    assert _dose_matches("약 500mcg", "약 0.5mg") is True


def test_dose_matches_ml_unit_unchanged():
    from pillcare.drug_matcher import _dose_matches

    # volume unit: no mg conversion, but same (n, u) matches
    assert _dose_matches("시럽 5ml", "시럽 5ml") is True
    assert _dose_matches("시럽 5ml", "시럽 10ml") is False


def test_dose_matches_iu_unit_unchanged():
    from pillcare.drug_matcher import _dose_matches

    assert _dose_matches("비타민D 1000IU", "비타민D 1000IU") is True
    assert _dose_matches("비타민D 1000IU", "비타민D 500IU") is False
