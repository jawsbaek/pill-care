"""Tests for SQLite DB builder."""

import json
import sqlite3
from pathlib import Path

import pytest

from pillcare.db_builder import build_db, build_dur_v2026_tables


@pytest.fixture
def small_permit(fixtures_dir: Path) -> list[dict]:
    with open(fixtures_dir / "small_permit.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def small_easy(fixtures_dir: Path) -> list[dict]:
    with open(fixtures_dir / "small_easy.json", encoding="utf-8") as f:
        return json.load(f)


def test_build_db_creates_drugs_table(tmp_path: Path, small_permit, small_easy):
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM drugs")
    assert cursor.fetchone()[0] == 3

    cursor = conn.execute(
        "SELECT item_name, atc_code, main_item_ingr FROM drugs WHERE item_seq = '199701416'"
    )
    row = cursor.fetchone()
    assert row[0] == "리도펜연질캡슐(이부프로펜)"
    assert row[1] == "M01AE01"
    assert "[M040702]이부프로펜" in row[2]
    conn.close()


def test_build_db_creates_drugs_easy_table(tmp_path: Path, small_permit, small_easy):
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM drugs_easy")
    assert cursor.fetchone()[0] == 1

    cursor = conn.execute(
        "SELECT efcy_qesitm FROM drugs_easy WHERE item_seq = '199701416'"
    )
    row = cursor.fetchone()
    assert "감기" in row[0]
    conn.close()


def test_build_db_creates_fts5_index(tmp_path: Path, small_permit, small_easy):
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    # FTS5 trigram search for Korean substring
    cursor = conn.execute(
        "SELECT item_name FROM drugs_fts WHERE drugs_fts MATCH '리도펜'"
    )
    rows = cursor.fetchall()
    assert len(rows) >= 1
    assert "리도펜" in rows[0][0]

    # FTS5 search for English ingredient
    cursor = conn.execute(
        "SELECT item_name FROM drugs_fts WHERE drugs_fts MATCH 'Ibuprofen'"
    )
    rows = cursor.fetchall()
    assert len(rows) >= 1
    conn.close()


def test_build_db_is_idempotent(tmp_path: Path, small_permit, small_easy):
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM drugs")
    assert cursor.fetchone()[0] == 3
    conn.close()


def test_build_db_creates_all_eight_dur_tables(
    tmp_path: Path, small_permit, small_easy
):
    """build_db creates dur_pairs + the 7 HIRA DUR v2026 tables."""
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)

    conn = sqlite3.connect(db_path)
    try:
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()

    expected = {
        "dur_pairs",
        "dur_age",
        "dur_pregnancy",
        "dur_dose",
        "dur_duplicate",
        "dur_elderly",
        "dur_specific_age",
        "dur_pregnant_woman",
    }
    assert expected.issubset(tables), f"missing: {expected - tables}"


def test_build_dur_v2026_tables_loads_fixtures(
    tmp_path: Path, fixtures_dir: Path, small_permit, small_easy
):
    """build_dur_v2026_tables loads rows from hira_dur_v2026/ fixtures."""
    db_path = tmp_path / "pillcare.db"
    build_db(db_path, permit_data=small_permit, easy_data=small_easy)
    counts = build_dur_v2026_tables(
        db_path, fixtures_dir / "hira_dur_v2026", encoding="utf-8-sig"
    )
    assert counts == {
        "dur_age": 2,
        "dur_pregnancy": 2,
        "dur_dose": 2,
        "dur_duplicate": 4,
        "dur_elderly": 2,
        "dur_specific_age": 2,
        "dur_pregnant_woman": 2,
    }

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM dur_age").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM dur_duplicate").fetchone()[0] == 4
    finally:
        conn.close()
