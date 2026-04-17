"""Tests for drug info collector."""

import json
import sqlite3
from pathlib import Path

import pytest

from pillcare.db_builder import build_db
from pillcare.xml_parser import parse_nb_doc
from pillcare.drug_info import get_drug_info


@pytest.fixture
def db_with_sections(tmp_path: Path, fixtures_dir: Path) -> Path:
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
    conn.commit()
    conn.close()
    return db_path


def test_get_drug_info_returns_all_fields(db_with_sections):
    info = get_drug_info(db_with_sections, "199701416")
    assert info is not None
    assert info.item_name == "리도펜연질캡슐(이부프로펜)"
    assert info.main_ingr_eng == "Ibuprofen"
    assert info.chart == "주황색의 장방형 연질캡슐제"
    assert "M01AE01" in info.atc_code


def test_get_drug_info_includes_sections(db_with_sections):
    info = get_drug_info(db_with_sections, "199701416")
    assert "금기" in info.sections
    assert "상호작용" in info.sections


def test_get_drug_info_includes_easy_text(db_with_sections):
    info = get_drug_info(db_with_sections, "199701416")
    assert info.easy is not None
    assert "감기" in info.easy["efcy_qesitm"]


def test_get_drug_info_returns_none_for_unknown(db_with_sections):
    info = get_drug_info(db_with_sections, "999999999")
    assert info is None
