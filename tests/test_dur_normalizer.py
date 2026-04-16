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
    assert "유산" in met_pair.reason
    assert met_pair.reason.count("유산") == 1


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
    codes = set()
    for p in pairs:
        codes.add((p.ingr_code_1, p.ingr_code_2))
        codes.add((p.ingr_code_2, p.ingr_code_1))
    assert ("M040702", "M04790101") in codes
    assert ("M04790101", "M040702") in codes
