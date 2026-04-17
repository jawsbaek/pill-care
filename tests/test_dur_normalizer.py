"""Tests for DUR CSV normalizer."""

from pathlib import Path
import pytest
from pillcare.dur_normalizer import (
    normalize_age_prohibition,
    normalize_dose_warning,
    normalize_dur,
    normalize_duplicate_therapy,
    normalize_elderly_warning,
    normalize_pregnancy_prohibition,
    normalize_pregnant_woman,
    normalize_specific_age,
)


@pytest.fixture
def hira_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "hira_dur_v2026"


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
        p
        for p in pairs
        if "메트포르민" in p.ingr_name_1 or "메트포르민" in p.ingr_name_2
    )
    assert "유산" in met_pair.reason
    assert met_pair.reason.count("유산") == 1


def test_normalize_dur_pair_fields(small_dur_path):
    pairs = normalize_dur(small_dur_path, encoding="utf-8")
    ibu_warf = next(
        p for p in pairs if "이부프로펜" in p.ingr_name_1 and "와파린" in p.ingr_name_2
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


# --- HIRA DUR 8-rule v2026 normalizers ---


def test_normalize_age_prohibition(hira_dir: Path):
    rows = normalize_age_prohibition(hira_dir / "age_prohibition.csv")
    assert len(rows) == 2
    r0 = rows[0]
    assert r0["ingredient_code"] == "R06AX02"
    assert r0["ingredient_name"] == "사이프로헵타딘"
    assert r0["age_min"] == 0
    assert r0["age_max"] == 2
    assert r0["age_unit"] == "year"
    assert "영유아" in r0["reason"]


def test_normalize_pregnancy_prohibition(hira_dir: Path):
    rows = normalize_pregnancy_prohibition(hira_dir / "pregnancy_prohibition.csv")
    assert len(rows) == 2
    codes = {r["ingredient_code"] for r in rows}
    assert "B01AA03" in codes
    warf = next(r for r in rows if r["ingredient_code"] == "B01AA03")
    assert warf["week_min"] == 0
    assert warf["week_max"] == 40


def test_normalize_dose_warning(hira_dir: Path):
    rows = normalize_dose_warning(hira_dir / "dose_warning.csv")
    assert len(rows) == 2
    apap = next(r for r in rows if r["ingredient_code"] == "N02BE01")
    assert apap["daily_max"] == 4000.0
    assert apap["dose_unit"] == "mg"
    assert "간독성" in apap["reason"]


def test_normalize_duplicate_therapy(hira_dir: Path):
    rows = normalize_duplicate_therapy(hira_dir / "duplicate_therapy.csv")
    assert len(rows) == 4
    m01a = [r for r in rows if r["class_code"] == "M01A"]
    assert len(m01a) == 2
    assert {r["ingredient_code"] for r in m01a} == {"M040702", "N02BE01"}


def test_normalize_elderly_warning(hira_dir: Path):
    rows = normalize_elderly_warning(hira_dir / "elderly_warning.csv")
    assert len(rows) == 2
    dia = next(r for r in rows if r["ingredient_code"] == "N05BA01")
    assert dia["target_age"] == 65
    assert "낙상" in dia["reason"]


def test_normalize_specific_age(hira_dir: Path):
    rows = normalize_specific_age(hira_dir / "specific_age.csv")
    assert len(rows) == 2
    bro = next(r for r in rows if r["ingredient_code"] == "R05CB02")
    assert bro["age_min"] == 12
    assert bro["age_max"] == 18


def test_normalize_pregnant_woman(hira_dir: Path):
    rows = normalize_pregnant_woman(hira_dir / "pregnant_woman.csv")
    assert len(rows) == 2
    eta = next(r for r in rows if r["ingredient_code"] == "L04AB01")
    assert eta["week_min"] == 0
    assert eta["week_max"] == 40
    assert "모유수유" in eta["reason"]
