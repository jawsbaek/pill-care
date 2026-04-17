"""4-phase drug matcher: EDI → Exact → FTS5 → Fuzzy.

A3 additions:
    - ``expand_query_with_synonyms`` uses ``src/pillcare/_data/ingredient_synonyms.json`` to
      rewrite cross-language queries (KOR ↔ ENG) before matching. This lets
      "acetaminophen 500mg" also hit "아세트아미노펜" products and vice versa.
    - ``_dose_matches`` enforces that a query-specified dose is present in the
      candidate name, preventing confusion like "500mg" query matching a 160mg
      product.
    - ``match_drug`` default ``min_score`` raised from 70 → 85 for precision.
"""

import json
import re
import sqlite3
from dataclasses import dataclass, field
from functools import lru_cache
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

_FTS5_UNSAFE = re.compile(r'["\(\)\*\-\+\:\^]')

_DOSE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|ml|iu|g)\b", re.IGNORECASE)

# Canonical mg conversion factors. ``None`` means the unit is not
# mass-convertible (volume / activity units), so those candidates must
# match by raw ``(number, unit)`` identity instead.
_UNIT_TO_MG: dict[str, float | None] = {
    "mg": 1.0,
    "mcg": 0.001,
    "g": 1000.0,
    "ml": None,  # volume, not mass-convertible
    "iu": None,  # activity unit, not mass-convertible
}


def _canonical_mg(number: str, unit: str) -> float | None:
    """Return mass in mg, or None if unit is not mass-convertible."""
    factor = _UNIT_TO_MG.get(unit.lower())
    if factor is None:
        return None
    return float(number) * factor


# Synonym dict ships as a package asset under src/pillcare/_data/.
_SYNONYMS_PATH = Path(__file__).resolve().parent / "_data" / "ingredient_synonyms.json"


@lru_cache(maxsize=1)
def _load_synonyms() -> dict[str, list[str]]:
    """Load the synonym dict, caching at module level. Returns {} if missing."""
    if not _SYNONYMS_PATH.exists():
        return {}
    with open(_SYNONYMS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data


def expand_query_with_synonyms(query: str) -> list[str]:
    """Return ``[query] + substring-substituted variants`` using the synonym dict.

    For every synonym-dict key that appears as a case-insensitive substring in
    ``query``, produce a rewritten query where that substring is replaced by
    each known synonym. Dose / form suffix (e.g. ``500mg``) is preserved
    because we only substitute the matched substring.

    The original query is always included as the first element so callers can
    fall back to unexpanded matching.
    """
    synonyms = _load_synonyms()
    results: list[str] = [query]
    seen: set[str] = {query}
    q_lower = query.lower()
    for key, vals in synonyms.items():
        key_lower = key.lower()
        if not key_lower:
            continue
        if key_lower in q_lower:
            # Case-insensitive replacement of the first occurrence. We use
            # re.sub with a compiled IGNORECASE pattern so the replacement
            # preserves the rest of the original string verbatim.
            pat = re.compile(re.escape(key), re.IGNORECASE)
            for val in vals:
                rewritten = pat.sub(val, query, count=1)
                if rewritten not in seen:
                    seen.add(rewritten)
                    results.append(rewritten)
    return results


def _dose_matches(query: str, candidate: str) -> bool:
    """Return True iff query's dose constraints (if any) are satisfied by candidate.

    - No dose in query → always True (caller didn't constrain).
    - Dose in query, no dose in candidate → False (ambiguous, fail-closed).
    - Both have doses → True iff at least one dose overlaps after unit
      normalization. Mass units (mg/mcg/g) are compared by canonical mg
      value so ``0.5g`` matches ``500mg``. Non-mass units (ml/IU) are
      compared by raw ``(number, unit)`` identity.
    """
    q_doses = _DOSE_PATTERN.findall(query)
    if not q_doses:
        return True
    c_doses = _DOSE_PATTERN.findall(candidate)
    if not c_doses:
        return False
    q_mass = {
        _canonical_mg(n, u) for n, u in q_doses if _canonical_mg(n, u) is not None
    }
    c_mass = {
        _canonical_mg(n, u) for n, u in c_doses if _canonical_mg(n, u) is not None
    }
    q_nonmass = {(n, u.lower()) for n, u in q_doses if _canonical_mg(n, u) is None}
    c_nonmass = {(n, u.lower()) for n, u in c_doses if _canonical_mg(n, u) is None}
    return bool(q_mass & c_mass) or bool(q_nonmass & c_nonmass)


def _sanitize_fts5(query: str) -> str:
    """Remove FTS5 special characters to prevent syntax errors."""
    return _FTS5_UNSAFE.sub(" ", query).strip()


def extract_ingr_codes(main_item_ingr: str | None) -> list[str]:
    if not main_item_ingr:
        return []
    return _INGR_CODE_RE.findall(main_item_ingr)


def _best_fuzzy_score(query: str, candidate: str) -> int:
    """Return the best fuzzy score across multiple strategies."""
    return int(
        max(
            fuzz.token_set_ratio(query, candidate),
            fuzz.partial_ratio(query, candidate),
            fuzz.ratio(query, candidate),
        )
    )


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
    min_score: int = 85,
) -> DrugMatch | None:
    """Match a drug query (natural-language name) against the SQLite DB.

    Phases: EDI → Exact → FTS5 → Fuzzy full-scan. ``min_score`` gates the
    fuzzy phases (raised from 70 → 85 in A3 for precision). When the query
    contains a dose (e.g. ``500mg``), candidates whose names do not also
    contain that dose are rejected to avoid cross-strength confusion.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = []
    # Queries to try: original + synonym-expanded. We use the original for
    # exact / EDI matches, and the expanded set for FTS5 / fuzzy scoring so
    # that cross-language ingredient queries can still land a candidate.
    expanded_queries = expand_query_with_synonyms(query)
    try:
        # Phase 1: EDI code match
        if edi_code:
            row = conn.execute(
                "SELECT * FROM drugs WHERE edi_code = ?", (edi_code,)
            ).fetchone()
            if row:
                return _row_to_match(row, 100)

        # Phase 2: Exact item_name match (original query only — exact match
        # on the raw user input is the highest-precision signal we have).
        row = conn.execute(
            "SELECT * FROM drugs WHERE item_name = ?", (query,)
        ).fetchone()
        if row and _dose_matches(query, row["item_name"]):
            return _row_to_match(row, 100)

        # Phase 3: FTS5 trigram search across original + expanded queries.
        try:
            fts_rows: list[sqlite3.Row] = []
            seen_rowids: set[int] = set()
            for q in expanded_queries:
                sanitized = _sanitize_fts5(q)
                if not sanitized:
                    continue
                for r in conn.execute(
                    "SELECT d.*, d.rowid AS _rid FROM drugs_fts f "
                    "JOIN drugs d ON f.rowid = d.rowid "
                    "WHERE drugs_fts MATCH ? ORDER BY rank LIMIT 5",
                    (sanitized,),
                ).fetchall():
                    rid = r["_rid"]
                    if rid not in seen_rowids:
                        seen_rowids.add(rid)
                        fts_rows.append(r)
            if fts_rows:
                best_score = 0
                best_row = None
                for r in fts_rows:
                    if not _dose_matches(query, r["item_name"]):
                        continue
                    for q in expanded_queries:
                        s = _best_fuzzy_score(q, r["item_name"])
                        if s > best_score:
                            best_score = s
                            best_row = r
                if best_row and best_score >= min_score:
                    return _row_to_match(best_row, best_score)
        except sqlite3.OperationalError:
            pass  # FTS5 table missing or query syntax error — fall through to Phase 4

        # Phase 4: Full scan with rapidfuzz
        rows = conn.execute(
            "SELECT item_seq, item_name, main_item_ingr, main_ingr_eng, atc_code, edi_code FROM drugs"
        ).fetchall()
    finally:
        conn.close()

    best_score = 0
    best_row = None
    for row in rows:
        if not _dose_matches(query, row["item_name"]):
            continue
        for q in expanded_queries:
            score = _best_fuzzy_score(q, row["item_name"])
            if score > best_score:
                best_score = score
                best_row = row

    if best_score < min_score:
        for row in rows:
            ingr = row["main_item_ingr"] or ""
            if not _dose_matches(query, row["item_name"]):
                # dose guard also applies when falling back to ingredient scoring
                continue
            for q in expanded_queries:
                score = _best_fuzzy_score(q, ingr)
                if score > best_score:
                    best_score = score
                    best_row = row

    if best_score >= min_score and best_row is not None:
        return _row_to_match(best_row, best_score)

    return None
