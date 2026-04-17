"""Tests for multi-ingredient N×N DUR cross-check."""

import sqlite3
from pathlib import Path

import pytest

from pillcare.db_builder import build_db, build_dur_v2026_tables
from pillcare.dur_checker import check_dur
from pillcare.schemas import DurRuleType


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
        (
            "M040702",
            "이부프로펜",
            "M04790101",
            "와파린나트륨",
            "출혈 위험 증가",
            "20200101",
        ),
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
    return [
        {
            "drug_name": "펠루비정",
            "department": "가정의학과",
            "ingr_codes": ["M040702"],
        },
        {"drug_name": "쿠마딘정", "department": "내과", "ingr_codes": ["M04790101"]},
        {
            "drug_name": "코대원정",
            "department": "가정의학과",
            "ingr_codes": ["M175201", "M146801"],
        },
        {"drug_name": "MAO약", "department": "정신과", "ingr_codes": ["M999901"]},
    ]


def test_check_dur_finds_single_ingr_pair(db_with_dur, drug_list_multi_ingr):
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    reasons = {a.reason for a in alerts}
    assert "출혈 위험 증가" in reasons


def test_check_dur_finds_multi_ingr_pair(db_with_dur, drug_list_multi_ingr):
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    reasons = {a.reason for a in alerts}
    assert "혈압 위기" in reasons


def test_check_dur_detects_cross_clinic(db_with_dur, drug_list_multi_ingr):
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    ibu_warf = next(a for a in alerts if "출혈" in a.reason)
    assert ibu_warf.cross_clinic is True


def test_check_dur_multi_ingr_alert_shows_correct_names(
    db_with_dur, drug_list_multi_ingr
):
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    mao_alert = next(a for a in alerts if "혈압" in a.reason)
    assert mao_alert.drug_name_1 == "코대원정"
    assert mao_alert.drug_name_2 == "MAO약"
    assert mao_alert.ingr_code_1 == "M175201"


def test_check_dur_no_alerts_for_safe_drugs(db_with_dur):
    safe_drugs = [
        {
            "drug_name": "알게텍정",
            "department": "가정의학과",
            "ingr_codes": ["M254901"],
        },
        {"drug_name": "안전한약", "department": "내과", "ingr_codes": ["M999999"]},
    ]
    alerts = check_dur(db_with_dur, safe_drugs)
    assert len(alerts) == 0


def test_check_dur_total_count(db_with_dur, drug_list_multi_ingr):
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    assert len(alerts) == 2


# --- HIRA DUR 8-rule dispatcher tests ---


@pytest.fixture
def db_with_all_rules(tmp_path: Path, fixtures_dir: Path) -> Path:
    """SQLite DB loaded with fixture 병용금기 + 7 HIRA v2026 fixtures."""
    db_path = tmp_path / "dur8.db"
    # Minimal permit_data to satisfy build_db's drugs table.
    build_db(db_path, permit_data=[], easy_data=[])
    # Seed dur_pairs from the combined fixture (manual insert — this CSV
    # has a different schema than the legacy 병용금기 normalizer expects).
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO dur_pairs VALUES (?,?,?,?,?,?)",
        (
            "M040702",
            "이부프로펜",
            "M04790101",
            "와파린나트륨",
            "출혈 위험 증가",
            "20200101",
        ),
    )
    conn.commit()
    conn.close()
    build_dur_v2026_tables(
        db_path, fixtures_dir / "hira_dur_v2026", encoding="utf-8-sig"
    )
    return db_path


def test_check_dur_detects_age_contraindication(db_with_all_rules):
    drugs = [
        {
            "drug_name": "페리악틴정",
            "department": "소아과",
            "ingr_codes": ["R06AX02"],  # 사이프로헵타딘
        }
    ]
    alerts = check_dur(db_with_all_rules, drugs, patient_context={"age_years": 1})
    age_alerts = [a for a in alerts if a.rule_type == DurRuleType.AGE]
    assert len(age_alerts) == 1
    assert "영유아" in age_alerts[0].reason


def test_check_dur_skips_age_when_outside_range(db_with_all_rules):
    drugs = [
        {
            "drug_name": "페리악틴정",
            "department": "소아과",
            "ingr_codes": ["R06AX02"],
        }
    ]
    # age 5 is outside 0–2 year range for cyproheptadine
    alerts = check_dur(db_with_all_rules, drugs, patient_context={"age_years": 5})
    assert not [a for a in alerts if a.rule_type == DurRuleType.AGE]


def test_check_dur_detects_pregnancy_contraindication(db_with_all_rules):
    drugs = [
        {
            "drug_name": "지스로맥스",
            "department": "산부인과",
            "ingr_codes": ["J01FA10"],  # 아지트로마이신
        }
    ]
    alerts = check_dur(
        db_with_all_rules,
        drugs,
        patient_context={"is_pregnant": True, "pregnancy_week": 10},
    )
    preg = [a for a in alerts if a.rule_type == DurRuleType.PREGNANCY]
    assert len(preg) == 1


def test_check_dur_skips_pregnancy_when_not_pregnant(db_with_all_rules):
    drugs = [
        {
            "drug_name": "지스로맥스",
            "department": "내과",
            "ingr_codes": ["J01FA10"],
        }
    ]
    alerts = check_dur(db_with_all_rules, drugs, patient_context={})
    assert not [a for a in alerts if a.rule_type == DurRuleType.PREGNANCY]


def test_check_dur_detects_dose_warning(db_with_all_rules):
    drugs = [
        {
            "drug_name": "타이레놀",
            "department": "내과",
            "ingr_codes": ["N02BE01"],  # 아세트아미노펜
            "daily_dose": 5000,  # exceeds 4000 mg/day
        }
    ]
    alerts = check_dur(db_with_all_rules, drugs)
    dose = [a for a in alerts if a.rule_type == DurRuleType.DOSE]
    assert len(dose) == 1
    assert "간독성" in dose[0].reason


def test_check_dur_skips_dose_when_below_max(db_with_all_rules):
    drugs = [
        {
            "drug_name": "타이레놀",
            "department": "내과",
            "ingr_codes": ["N02BE01"],
            "daily_dose": 1000,  # below max
        }
    ]
    alerts = check_dur(db_with_all_rules, drugs)
    assert not [a for a in alerts if a.rule_type == DurRuleType.DOSE]


def test_check_dur_detects_therapeutic_duplication(db_with_all_rules):
    drugs = [
        {
            "drug_name": "이부프로펜정",
            "department": "내과",
            "ingr_codes": ["M040702"],  # M01A NSAID (duplicate fixture)
        },
        {
            "drug_name": "타이레놀",
            "department": "가정의학과",
            "ingr_codes": ["N02BE01"],  # also M01A in fixture
        },
    ]
    alerts = check_dur(db_with_all_rules, drugs)
    dup = [a for a in alerts if a.rule_type == DurRuleType.DUPLICATE]
    assert len(dup) == 1
    assert "효능군" in dup[0].reason
    assert dup[0].cross_clinic is True


def test_check_dur_detects_elderly_warning(db_with_all_rules):
    drugs = [
        {
            "drug_name": "디아제팜정",
            "department": "정신건강의학과",
            "ingr_codes": ["N05BA01"],  # 디아제팜
        }
    ]
    alerts = check_dur(db_with_all_rules, drugs, patient_context={"age_years": 70})
    eld = [a for a in alerts if a.rule_type == DurRuleType.ELDERLY]
    assert len(eld) == 1
    assert "낙상" in eld[0].reason


def test_check_dur_skips_elderly_when_young(db_with_all_rules):
    drugs = [
        {
            "drug_name": "디아제팜정",
            "department": "정신건강의학과",
            "ingr_codes": ["N05BA01"],
        }
    ]
    alerts = check_dur(db_with_all_rules, drugs, patient_context={"age_years": 40})
    assert not [a for a in alerts if a.rule_type == DurRuleType.ELDERLY]


def test_check_dur_detects_specific_age(db_with_all_rules):
    drugs = [
        {
            "drug_name": "브롬헥신정",
            "department": "소아청소년과",
            "ingr_codes": ["R05CB02"],  # 브롬헥신 12–18 warning
        }
    ]
    alerts = check_dur(db_with_all_rules, drugs, patient_context={"age_years": 14})
    spec = [a for a in alerts if a.rule_type == DurRuleType.SPECIFIC_AGE]
    assert len(spec) == 1


def test_check_dur_detects_pregnant_woman_warning(db_with_all_rules):
    drugs = [
        {
            "drug_name": "엔브렐",
            "department": "류마티스내과",
            "ingr_codes": ["L04AB01"],  # 에타너셉트
        }
    ]
    alerts = check_dur(
        db_with_all_rules,
        drugs,
        patient_context={"is_pregnant": True, "pregnancy_week": 20},
    )
    pw = [a for a in alerts if a.rule_type == DurRuleType.PREGNANT_WOMAN]
    assert len(pw) == 1
    assert "모유수유" in pw[0].reason


def test_check_dur_without_patient_context_is_backward_compatible(
    db_with_dur, drug_list_multi_ingr
):
    """No patient_context → only combined/dose/duplicate (context-free) run."""
    alerts = check_dur(db_with_dur, drug_list_multi_ingr)
    # db_with_dur only has dur_pairs table, so all alerts should be COMBINED
    assert all(a.rule_type == DurRuleType.COMBINED for a in alerts)
