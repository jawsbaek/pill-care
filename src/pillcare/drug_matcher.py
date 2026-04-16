"""4-phase drug matcher: EDI → Exact → FTS5 → Fuzzy."""

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz


@dataclass
class DrugMatch:
    item_seq: str
    item_name: str
    main_item_ingr: str
    main_ingr_eng: str
    atc_code: str
    ingr_codes: list[str] = field(default_factory=list)
    score: int = 0


_INGR_CODE_RE = re.compile(r"\[([A-Z]\d+)\]")


def extract_ingr_codes(main_item_ingr: str | None) -> list[str]:
    if not main_item_ingr:
        return []
    return _INGR_CODE_RE.findall(main_item_ingr)


def _best_fuzzy_score(query: str, candidate: str) -> int:
    """Return the best fuzzy score across multiple strategies."""
    return int(max(
        fuzz.token_set_ratio(query, candidate),
        fuzz.partial_ratio(query, candidate),
        fuzz.ratio(query, candidate),
    ))


def _row_to_match(row: sqlite3.Row, score: int) -> DrugMatch:
    ingr = row["main_item_ingr"] or ""
    return DrugMatch(
        item_seq=row["item_seq"],
        item_name=row["item_name"],
        main_item_ingr=ingr,
        main_ingr_eng=row["main_ingr_eng"] or "",
        atc_code=row["atc_code"] or "",
        ingr_codes=extract_ingr_codes(ingr),
        score=score,
    )


def match_drug(
    db_path: Path,
    query: str,
    edi_code: str | None = None,
    min_score: int = 70,
) -> DrugMatch | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # Phase 1: EDI code match
        if edi_code:
            row = conn.execute(
                "SELECT * FROM drugs WHERE edi_code = ?", (edi_code,)
            ).fetchone()
            if row:
                return _row_to_match(row, 100)

        # Phase 2: Exact item_name match
        row = conn.execute(
            "SELECT * FROM drugs WHERE item_name = ?", (query,)
        ).fetchone()
        if row:
            return _row_to_match(row, 100)

        # Phase 3: FTS5 trigram search
        try:
            fts_rows = conn.execute(
                "SELECT d.* FROM drugs_fts f JOIN drugs d ON f.rowid = d.rowid "
                "WHERE drugs_fts MATCH ? ORDER BY rank LIMIT 5",
                (query,),
            ).fetchall()
            if fts_rows:
                best_score = 0
                best_row = None
                for r in fts_rows:
                    s = _best_fuzzy_score(query, r["item_name"])
                    if s > best_score:
                        best_score = s
                        best_row = r
                if best_row and best_score >= min_score:
                    return _row_to_match(best_row, best_score)
        except sqlite3.OperationalError:
            pass  # FTS5 table missing or query syntax error — fall through to Phase 4

        # Phase 4: Full scan with rapidfuzz
        rows = conn.execute("SELECT * FROM drugs").fetchall()
    finally:
        conn.close()

    best_score = 0
    best_row = None
    for row in rows:
        score = _best_fuzzy_score(query, row["item_name"])
        if score > best_score:
            best_score = score
            best_row = row

    if best_score < min_score:
        for row in rows:
            ingr = row["main_item_ingr"] or ""
            score = _best_fuzzy_score(query, ingr)
            if score > best_score:
                best_score = score
                best_row = row

    if best_score >= min_score and best_row is not None:
        return _row_to_match(best_row, best_score)

    return None
