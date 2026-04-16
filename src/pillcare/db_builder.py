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
        _DRUGS_DDL, _DRUGS_EASY_DDL, _DRUG_SECTIONS_DDL,
        _DUR_PAIRS_DDL, _BUNDLE_ATC_DDL, _MEDICATION_HISTORY_DDL,
    ]:
        conn.execute(ddl)

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
                item.get("ITEM_SEQ"), item.get("ITEM_NAME"),
                item.get("ITEM_ENG_NAME"), item.get("ENTP_NAME"),
                item.get("ETC_OTC_CODE"), item.get("MATERIAL_NAME"),
                item.get("MAIN_ITEM_INGR"), item.get("MAIN_INGR_ENG"),
                item.get("CHART"), item.get("ATC_CODE"),
                item.get("STORAGE_METHOD"), item.get("VALID_TERM"),
                item.get("EDI_CODE"), item.get("EE_DOC_DATA"),
                item.get("UD_DOC_DATA"), item.get("NB_DOC_DATA"),
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

    # Upsert drugs_easy
    if easy_data:
        conn.execute("DELETE FROM drugs_easy")
        for item in easy_data:
            conn.execute(
                """INSERT OR REPLACE INTO drugs_easy
                (item_seq, efcy_qesitm, use_method_qesitm, atpn_warn_qesitm,
                 atpn_qesitm, intrc_qesitm, se_qesitm, deposit_method_qesitm)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    item.get("itemSeq"), item.get("efcyQesitm"),
                    item.get("useMethodQesitm"), item.get("atpnWarnQesitm"),
                    item.get("atpnQesitm"), item.get("intrcQesitm"),
                    item.get("seQesitm"), item.get("depositMethodQesitm"),
                ),
            )

    conn.commit()
    conn.close()
    return db_path
