"""Tests for medication history parser."""
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
    rec = MedRecord(
        seq=1, drug_name="알게텍정", drug_class="제산제",
        ingredient="almagate", drug_code="057600010", unit="1정",
        dose_per_time=1.0, times_per_day=3, duration_days=3,
        safety_letter="N", antithrombotic="N", department="가정의학과",
    )
    assert rec.drug_name == "알게텍정"
    assert rec.times_per_day == 3
