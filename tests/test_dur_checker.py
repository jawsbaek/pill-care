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
    return [
        {"drug_name": "펠루비정", "department": "가정의학과", "ingr_codes": ["M040702"]},
        {"drug_name": "쿠마딘정", "department": "내과", "ingr_codes": ["M04790101"]},
        {"drug_name": "코대원정", "department": "가정의학과", "ingr_codes": ["M175201", "M146801"]},
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
    assert len(alerts) == 2
