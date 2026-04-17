"""Build SQLite DB from crawled 식약처 API data."""

import sqlite3
from pathlib import Path


_DRUGS_DDL = """
CREATE TABLE IF NOT EXISTS drugs (
    item_seq        TEXT PRIMARY KEY,
    item_name       TEXT NOT NULL,
    item_eng_name   TEXT,
    entp_name       TEXT NOT NULL,
    etc_otc_code    TEXT,
    material_name   TEXT,
    main_item_ingr  TEXT,
    main_ingr_eng   TEXT,
    chart           TEXT,
    atc_code        TEXT,
    storage_method  TEXT,
    valid_term      TEXT,
    edi_code        TEXT,
    ee_doc_data     TEXT,
    ud_doc_data     TEXT,
    nb_doc_data     TEXT,
    total_content   TEXT,
    updated_at      TEXT
)
"""

_DRUGS_EASY_DDL = """
CREATE TABLE IF NOT EXISTS drugs_easy (
    item_seq                TEXT PRIMARY KEY REFERENCES drugs(item_seq),
    efcy_qesitm             TEXT,
    use_method_qesitm       TEXT,
    atpn_warn_qesitm        TEXT,
    atpn_qesitm             TEXT,
    intrc_qesitm            TEXT,
    se_qesitm               TEXT,
    deposit_method_qesitm   TEXT
)
"""

_DRUG_SECTIONS_DDL = """
CREATE TABLE IF NOT EXISTS drug_sections (
    item_seq      TEXT REFERENCES drugs(item_seq),
    section_type  TEXT NOT NULL,
    section_title TEXT,
    section_text  TEXT NOT NULL,
    section_order INTEGER,
    PRIMARY KEY (item_seq, section_type, section_order)
)
"""

_DUR_PAIRS_DDL = """
CREATE TABLE IF NOT EXISTS dur_pairs (
    ingr_code_1   TEXT NOT NULL,
    ingr_name_1   TEXT NOT NULL,
    ingr_code_2   TEXT NOT NULL,
    ingr_name_2   TEXT NOT NULL,
    reason        TEXT NOT NULL,
    notice_date   TEXT,
    PRIMARY KEY (ingr_code_1, ingr_code_2)
)
"""

# --- HIRA DUR 7 additional rule-type tables ---
# Each indexed on ingredient_code for O(1) lookup per matched drug.

_DUR_AGE_DDL = """
CREATE TABLE IF NOT EXISTS dur_age (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_code TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    age_min INTEGER NOT NULL,
    age_max INTEGER NOT NULL,
    age_unit TEXT NOT NULL,
    reason TEXT NOT NULL
)
"""
_DUR_AGE_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_dur_age_ingredient ON dur_age(ingredient_code)"
)

_DUR_PREGNANCY_DDL = """
CREATE TABLE IF NOT EXISTS dur_pregnancy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_code TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    week_min INTEGER NOT NULL,
    week_max INTEGER NOT NULL,
    reason TEXT NOT NULL
)
"""
_DUR_PREGNANCY_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_dur_pregnancy_ingredient "
    "ON dur_pregnancy(ingredient_code)"
)

_DUR_DOSE_DDL = """
CREATE TABLE IF NOT EXISTS dur_dose (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_code TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    daily_max REAL NOT NULL,
    dose_unit TEXT NOT NULL,
    reason TEXT NOT NULL
)
"""
_DUR_DOSE_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_dur_dose_ingredient ON dur_dose(ingredient_code)"
)

_DUR_DUPLICATE_DDL = """
CREATE TABLE IF NOT EXISTS dur_duplicate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_code TEXT NOT NULL,
    class_name TEXT NOT NULL,
    ingredient_code TEXT NOT NULL,
    ingredient_name TEXT NOT NULL
)
"""
_DUR_DUPLICATE_IDX_ING = (
    "CREATE INDEX IF NOT EXISTS idx_dur_duplicate_ingredient "
    "ON dur_duplicate(ingredient_code)"
)
_DUR_DUPLICATE_IDX_CLS = (
    "CREATE INDEX IF NOT EXISTS idx_dur_duplicate_class ON dur_duplicate(class_code)"
)

_DUR_ELDERLY_DDL = """
CREATE TABLE IF NOT EXISTS dur_elderly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_code TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    target_age INTEGER NOT NULL,
    reason TEXT NOT NULL
)
"""
_DUR_ELDERLY_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_dur_elderly_ingredient "
    "ON dur_elderly(ingredient_code)"
)

_DUR_SPECIFIC_AGE_DDL = """
CREATE TABLE IF NOT EXISTS dur_specific_age (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_code TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    age_min INTEGER NOT NULL,
    age_max INTEGER NOT NULL,
    reason TEXT NOT NULL
)
"""
_DUR_SPECIFIC_AGE_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_dur_specific_age_ingredient "
    "ON dur_specific_age(ingredient_code)"
)

_DUR_PREGNANT_WOMAN_DDL = """
CREATE TABLE IF NOT EXISTS dur_pregnant_woman (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_code TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    week_min INTEGER NOT NULL,
    week_max INTEGER NOT NULL,
    reason TEXT NOT NULL
)
"""
_DUR_PREGNANT_WOMAN_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_dur_pregnant_woman_ingredient "
    "ON dur_pregnant_woman(ingredient_code)"
)

_BUNDLE_ATC_DDL = """
CREATE TABLE IF NOT EXISTS bundle_atc (
    trust_item_name          TEXT,
    trust_mainingr           TEXT,
    trust_atc_code           TEXT,
    trust_hira_mainingr_code TEXT,
    trust_hira_product_code  TEXT
)
"""

_MEDICATION_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS medication_history (
    profile_id      TEXT NOT NULL,
    seq             INTEGER,
    drug_name       TEXT NOT NULL,
    drug_class      TEXT,
    ingredient      TEXT,
    drug_code       TEXT,
    unit            TEXT,
    dose_per_time   REAL,
    times_per_day   INTEGER,
    duration_days   INTEGER,
    safety_letter   TEXT,
    antithrombotic  TEXT,
    department      TEXT,
    item_seq        TEXT REFERENCES drugs(item_seq),
    ingr_codes      TEXT
)
"""

_FTS5_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS drugs_fts USING fts5(
    item_name, item_eng_name, main_item_ingr, main_ingr_eng,
    content=drugs, content_rowid=rowid,
    tokenize='trigram'
)
"""

_FTS5_POPULATE = """
INSERT INTO drugs_fts(drugs_fts) VALUES('rebuild')
"""

_EDI_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_drugs_edi_code ON drugs(edi_code)
"""

_ITEM_NAME_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_drugs_item_name ON drugs(item_name)
"""


def build_db(
    db_path: Path,
    permit_data: list[dict],
    easy_data: list[dict] | None = None,
) -> Path:
    """Create or rebuild the SQLite DB from crawled data.

    Args:
        db_path: Where to create the DB file.
        permit_data: List of dicts from drug_permit_detail.json.
        easy_data: List of dicts from easy_drug_info.json (optional).

    Returns:
        The db_path for chaining.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    for ddl in [
        _DRUGS_DDL,
        _DRUGS_EASY_DDL,
        _DRUG_SECTIONS_DDL,
        _DUR_PAIRS_DDL,
        _DUR_AGE_DDL,
        _DUR_PREGNANCY_DDL,
        _DUR_DOSE_DDL,
        _DUR_DUPLICATE_DDL,
        _DUR_ELDERLY_DDL,
        _DUR_SPECIFIC_AGE_DDL,
        _DUR_PREGNANT_WOMAN_DDL,
        _BUNDLE_ATC_DDL,
        _MEDICATION_HISTORY_DDL,
    ]:
        conn.execute(ddl)

    for idx in [
        _DUR_AGE_IDX,
        _DUR_PREGNANCY_IDX,
        _DUR_DOSE_IDX,
        _DUR_DUPLICATE_IDX_ING,
        _DUR_DUPLICATE_IDX_CLS,
        _DUR_ELDERLY_IDX,
        _DUR_SPECIFIC_AGE_IDX,
        _DUR_PREGNANT_WOMAN_IDX,
    ]:
        conn.execute(idx)

    # Upsert drugs
    conn.execute("DELETE FROM drugs")
    for item in permit_data:
        conn.execute(
            """INSERT OR REPLACE INTO drugs
            (item_seq, item_name, item_eng_name, entp_name, etc_otc_code,
             material_name, main_item_ingr, main_ingr_eng, chart, atc_code,
             storage_method, valid_term, edi_code, ee_doc_data, ud_doc_data,
             nb_doc_data, total_content)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.get("ITEM_SEQ"),
                item.get("ITEM_NAME"),
                item.get("ITEM_ENG_NAME"),
                item.get("ENTP_NAME"),
                item.get("ETC_OTC_CODE"),
                item.get("MATERIAL_NAME"),
                item.get("MAIN_ITEM_INGR"),
                item.get("MAIN_INGR_ENG"),
                item.get("CHART"),
                item.get("ATC_CODE"),
                item.get("STORAGE_METHOD"),
                item.get("VALID_TERM"),
                item.get("EDI_CODE"),
                item.get("EE_DOC_DATA"),
                item.get("UD_DOC_DATA"),
                item.get("NB_DOC_DATA"),
                item.get("TOTAL_CONTENT"),
            ),
        )

    # Create indexes
    conn.execute(_EDI_INDEX_DDL)
    conn.execute(_ITEM_NAME_INDEX_DDL)

    # Build FTS5 trigram index
    conn.execute("DROP TABLE IF EXISTS drugs_fts")
    conn.execute(_FTS5_DDL)
    conn.execute(_FTS5_POPULATE)

    # Upsert drugs_easy — always clear to avoid stale data on rebuild
    conn.execute("DELETE FROM drugs_easy")
    if easy_data:
        for item in easy_data:
            conn.execute(
                """INSERT OR REPLACE INTO drugs_easy
                (item_seq, efcy_qesitm, use_method_qesitm, atpn_warn_qesitm,
                 atpn_qesitm, intrc_qesitm, se_qesitm, deposit_method_qesitm)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    item.get("itemSeq"),
                    item.get("efcyQesitm"),
                    item.get("useMethodQesitm"),
                    item.get("atpnWarnQesitm"),
                    item.get("atpnQesitm"),
                    item.get("intrcQesitm"),
                    item.get("seQesitm"),
                    item.get("depositMethodQesitm"),
                ),
            )

    conn.commit()
    conn.close()
    return db_path


def build_dur_v2026_tables(
    db_path: Path,
    hira_dir: Path,
    encoding: str = "utf-8-sig",
) -> dict[str, int]:
    """Load HIRA DUR 8-rule v2026 CSVs from ``hira_dir`` into SQLite.

    Expects files named per tests/fixtures/hira_dur_v2026/README.md. Missing
    files are silently skipped (conditional load). Returns per-table row
    counts so callers can log / assert.

    The base tables are assumed to already exist (e.g. via a preceding
    ``build_db`` call). This function re-runs the DDL defensively so it can
    be invoked standalone in tests.
    """
    from pillcare.dur_normalizer import (
        normalize_age_prohibition,
        normalize_dose_warning,
        normalize_duplicate_therapy,
        normalize_elderly_warning,
        normalize_pregnancy_prohibition,
        normalize_pregnant_woman,
        normalize_specific_age,
    )

    conn = sqlite3.connect(db_path)
    try:
        # Defensive: ensure tables exist even if called without build_db first.
        for ddl in [
            _DUR_AGE_DDL,
            _DUR_PREGNANCY_DDL,
            _DUR_DOSE_DDL,
            _DUR_DUPLICATE_DDL,
            _DUR_ELDERLY_DDL,
            _DUR_SPECIFIC_AGE_DDL,
            _DUR_PREGNANT_WOMAN_DDL,
        ]:
            conn.execute(ddl)
        for idx in [
            _DUR_AGE_IDX,
            _DUR_PREGNANCY_IDX,
            _DUR_DOSE_IDX,
            _DUR_DUPLICATE_IDX_ING,
            _DUR_DUPLICATE_IDX_CLS,
            _DUR_ELDERLY_IDX,
            _DUR_SPECIFIC_AGE_IDX,
            _DUR_PREGNANT_WOMAN_IDX,
        ]:
            conn.execute(idx)

        counts: dict[str, int] = {}

        # Age
        age_csv = hira_dir / "age_prohibition.csv"
        if age_csv.exists():
            conn.execute("DELETE FROM dur_age")
            rows = normalize_age_prohibition(age_csv, encoding=encoding)
            conn.executemany(
                "INSERT INTO dur_age "
                "(ingredient_code, ingredient_name, age_min, age_max, age_unit, reason)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        r["ingredient_code"],
                        r["ingredient_name"],
                        r["age_min"],
                        r["age_max"],
                        r["age_unit"],
                        r["reason"],
                    )
                    for r in rows
                ],
            )
            counts["dur_age"] = len(rows)

        # Pregnancy (absolute)
        preg_csv = hira_dir / "pregnancy_prohibition.csv"
        if preg_csv.exists():
            conn.execute("DELETE FROM dur_pregnancy")
            rows = normalize_pregnancy_prohibition(preg_csv, encoding=encoding)
            conn.executemany(
                "INSERT INTO dur_pregnancy "
                "(ingredient_code, ingredient_name, week_min, week_max, reason)"
                " VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        r["ingredient_code"],
                        r["ingredient_name"],
                        r["week_min"],
                        r["week_max"],
                        r["reason"],
                    )
                    for r in rows
                ],
            )
            counts["dur_pregnancy"] = len(rows)

        # Dose
        dose_csv = hira_dir / "dose_warning.csv"
        if dose_csv.exists():
            conn.execute("DELETE FROM dur_dose")
            rows = normalize_dose_warning(dose_csv, encoding=encoding)
            conn.executemany(
                "INSERT INTO dur_dose "
                "(ingredient_code, ingredient_name, daily_max, dose_unit, reason)"
                " VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        r["ingredient_code"],
                        r["ingredient_name"],
                        r["daily_max"],
                        r["dose_unit"],
                        r["reason"],
                    )
                    for r in rows
                ],
            )
            counts["dur_dose"] = len(rows)

        # Duplicate
        dup_csv = hira_dir / "duplicate_therapy.csv"
        if dup_csv.exists():
            conn.execute("DELETE FROM dur_duplicate")
            rows = normalize_duplicate_therapy(dup_csv, encoding=encoding)
            conn.executemany(
                "INSERT INTO dur_duplicate "
                "(class_code, class_name, ingredient_code, ingredient_name)"
                " VALUES (?, ?, ?, ?)",
                [
                    (
                        r["class_code"],
                        r["class_name"],
                        r["ingredient_code"],
                        r["ingredient_name"],
                    )
                    for r in rows
                ],
            )
            counts["dur_duplicate"] = len(rows)

        # Elderly
        eld_csv = hira_dir / "elderly_warning.csv"
        if eld_csv.exists():
            conn.execute("DELETE FROM dur_elderly")
            rows = normalize_elderly_warning(eld_csv, encoding=encoding)
            conn.executemany(
                "INSERT INTO dur_elderly "
                "(ingredient_code, ingredient_name, target_age, reason)"
                " VALUES (?, ?, ?, ?)",
                [
                    (
                        r["ingredient_code"],
                        r["ingredient_name"],
                        r["target_age"],
                        r["reason"],
                    )
                    for r in rows
                ],
            )
            counts["dur_elderly"] = len(rows)

        # Specific age
        spec_csv = hira_dir / "specific_age.csv"
        if spec_csv.exists():
            conn.execute("DELETE FROM dur_specific_age")
            rows = normalize_specific_age(spec_csv, encoding=encoding)
            conn.executemany(
                "INSERT INTO dur_specific_age "
                "(ingredient_code, ingredient_name, age_min, age_max, reason)"
                " VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        r["ingredient_code"],
                        r["ingredient_name"],
                        r["age_min"],
                        r["age_max"],
                        r["reason"],
                    )
                    for r in rows
                ],
            )
            counts["dur_specific_age"] = len(rows)

        # Pregnant woman
        pw_csv = hira_dir / "pregnant_woman.csv"
        if pw_csv.exists():
            conn.execute("DELETE FROM dur_pregnant_woman")
            rows = normalize_pregnant_woman(pw_csv, encoding=encoding)
            conn.executemany(
                "INSERT INTO dur_pregnant_woman "
                "(ingredient_code, ingredient_name, week_min, week_max, reason)"
                " VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        r["ingredient_code"],
                        r["ingredient_name"],
                        r["week_min"],
                        r["week_max"],
                        r["reason"],
                    )
                    for r in rows
                ],
            )
            counts["dur_pregnant_woman"] = len(rows)

        conn.commit()
        return counts
    finally:
        conn.close()


def build_full_db(data_dir: Path, db_path: Path) -> Path:
    """Build the complete DB from all crawled data files."""
    import json
    from pillcare.xml_parser import parse_nb_doc
    from pillcare.dur_normalizer import normalize_dur

    print("Loading drug_permit_detail.json...")
    with open(data_dir / "drug_permit_detail.json", encoding="utf-8") as f:
        permit_data = json.load(f)
    print(f"  {len(permit_data)} items")

    print("Loading easy_drug_info.json...")
    with open(data_dir / "easy_drug_info.json", encoding="utf-8") as f:
        easy_data = json.load(f)
    print(f"  {len(easy_data)} items")

    print("Building base tables and FTS5 index...")
    build_db(db_path, permit_data=permit_data, easy_data=easy_data)

    print("Parsing NB_DOC_DATA XML into sections...")
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM drug_sections")
    count = 0
    parse_errors = 0
    for item in permit_data:
        nb = item.get("NB_DOC_DATA", "")
        if not nb:
            continue
        sections = parse_nb_doc(nb)
        if not sections and nb.strip():
            parse_errors += 1
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
            count += 1
    conn.commit()
    print(f"  {count} sections inserted ({parse_errors} parse failures)")

    dur_csv = data_dir / "한국의약품안전관리원_병용금기약물_20240625.csv"
    if dur_csv.exists():
        print("Normalizing DUR pairs...")
        pairs = normalize_dur(dur_csv, encoding="cp949")
        conn.execute("DELETE FROM dur_pairs")
        for p in pairs:
            conn.execute(
                "INSERT OR REPLACE INTO dur_pairs VALUES (?,?,?,?,?,?)",
                (
                    p.ingr_code_1,
                    p.ingr_name_1,
                    p.ingr_code_2,
                    p.ingr_name_2,
                    p.reason,
                    p.notice_date,
                ),
            )
        conn.commit()
        print(f"  {len(pairs)} pairs inserted")

    # HIRA DUR v2026 8-rule tables — load if directory present.
    # Team downloads HIRA CSVs (공공데이터포털 인증 필요) to
    # data/hira-dur-v2026/; gitignored. CI uses the synthetic fixtures in
    # tests/fixtures/hira_dur_v2026/ via a dedicated test.
    hira_dir = data_dir / "hira-dur-v2026"
    if hira_dir.exists() and hira_dir.is_dir():
        print("Loading HIRA DUR v2026 8-rule tables...")
        # Production HIRA CSVs are typically CP949; override here if needed.
        counts = build_dur_v2026_tables(db_path, hira_dir, encoding="cp949")
        for table, n in counts.items():
            print(f"  {table}: {n} rows")

    bundle_path = data_dir / "bundle_drug_info.json"
    if bundle_path.exists():
        print("Loading bundle ATC data...")
        with open(bundle_path, encoding="utf-8") as f:
            bundle_data = json.load(f)
        conn.execute("DELETE FROM bundle_atc")
        for item in bundle_data:
            conn.execute(
                "INSERT INTO bundle_atc VALUES (?,?,?,?,?)",
                (
                    item.get("trustItemName"),
                    item.get("trustMainingr"),
                    item.get("trustAtcCode"),
                    item.get("trustHiraMainingrCode"),
                    item.get("trustHiraPrductCode"),
                ),
            )
        conn.commit()
        print(f"  {len(bundle_data)} bundle records inserted")

    conn.close()
    print(f"DB built: {db_path} ({db_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return db_path


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    db_path = data_dir / "pillcare.db"
    build_full_db(data_dir, db_path)
