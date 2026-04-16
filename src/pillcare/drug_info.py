"""Collect all medication guidance data for a single drug."""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DrugInfo:
    item_seq: str
    item_name: str
    item_eng_name: str
    entp_name: str
    etc_otc_code: str
    material_name: str
    main_item_ingr: str
    main_ingr_eng: str
    chart: str
    atc_code: str
    storage_method: str
    valid_term: str
    total_content: str
    ee_doc_data: str = ""
    ud_doc_data: str = ""
    sections: dict[str, str] = field(default_factory=dict)
    easy: dict[str, str] | None = None


def get_drug_info(db_path: Path, item_seq: str) -> DrugInfo | None:
    """Load all medication guidance data for a single drug by item_seq.

    Joins drugs + drug_sections + drugs_easy tables to build a complete
    DrugInfo object.

    Args:
        db_path: Path to the SQLite database.
        item_seq: The drug's unique identifier (품목기준코드).

    Returns:
        DrugInfo with all fields populated, or None if the drug is not found.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        "SELECT * FROM drugs WHERE item_seq = ?", (item_seq,)
    ).fetchone()
    if row is None:
        conn.close()
        return None

    info = DrugInfo(
        item_seq=row["item_seq"],
        item_name=row["item_name"] or "",
        item_eng_name=row["item_eng_name"] or "",
        entp_name=row["entp_name"] or "",
        etc_otc_code=row["etc_otc_code"] or "",
        material_name=row["material_name"] or "",
        main_item_ingr=row["main_item_ingr"] or "",
        main_ingr_eng=row["main_ingr_eng"] or "",
        chart=row["chart"] or "",
        atc_code=row["atc_code"] or "",
        storage_method=row["storage_method"] or "",
        valid_term=row["valid_term"] or "",
        total_content=row["total_content"] or "",
        ee_doc_data=row["ee_doc_data"] or "",
        ud_doc_data=row["ud_doc_data"] or "",
    )

    # Load sections
    sec_rows = conn.execute(
        "SELECT section_type, section_text FROM drug_sections WHERE item_seq = ? ORDER BY section_order",
        (item_seq,),
    ).fetchall()
    for sr in sec_rows:
        stype = sr["section_type"]
        if stype in info.sections:
            info.sections[stype] += "\n\n" + sr["section_text"]
        else:
            info.sections[stype] = sr["section_text"]

    # Load easy text
    easy_row = conn.execute(
        "SELECT * FROM drugs_easy WHERE item_seq = ?", (item_seq,)
    ).fetchone()
    if easy_row:
        info.easy = {
            "efcy_qesitm": easy_row["efcy_qesitm"] or "",
            "use_method_qesitm": easy_row["use_method_qesitm"] or "",
            "atpn_warn_qesitm": easy_row["atpn_warn_qesitm"] or "",
            "atpn_qesitm": easy_row["atpn_qesitm"] or "",
            "intrc_qesitm": easy_row["intrc_qesitm"] or "",
            "se_qesitm": easy_row["se_qesitm"] or "",
            "deposit_method_qesitm": easy_row["deposit_method_qesitm"] or "",
        }

    conn.close()
    return info
