"""One-time script: build ingredient synonym dict from 식약처 drug permit data.

Source priority:
    1. SQLite ``pillcare.db`` ``drugs`` table (columns ``main_item_ingr`` +
       ``main_ingr_eng``) if the DB exists.
    2. Otherwise ``data/drug_permit_detail.csv`` (raw MFDS crawl, not
       tracked in git — must be downloaded locally before running).

The ``main_item_ingr`` column stores the Korean ingredient name prefixed with
an MFDS code in square brackets (e.g. ``[M040702]이부프로펜``). Multi-component
products delimit ingredients with ``|`` on the Korean side and ``/`` on the
English side. We align by index and emit bidirectional KOR <-> ENG pairs.

After running, the curated salt-form / brand-name supplement at
``src/pillcare/_data/ingredient_synonyms_manual.json`` is merged automatically.

Usage:
    uv run python scripts/build_ingredient_synonyms.py

Output:
    src/pillcare/_data/ingredient_synonyms.json
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path

_INGR_CODE_RE = re.compile(r"\[[A-Z]\d+\]")

_WS_RE = re.compile(r"\s+")
_TRAILING_PUNCT = " ([{.,;:·"


def _normalize_name(raw: str) -> str:
    """Collapse whitespace, strip trailing/leading punctuation + whitespace.

    Also removes ``[Mxxxxxx]`` MFDS code prefixes. Applied to both KOR and
    ENG sides before dict insertion so that synonym keys/values don't carry
    noise like trailing ``)`` or BOM-adjacent whitespace, which otherwise
    leaks into ``expand_query_with_synonyms`` and generates unmatchable
    rewritten queries.
    """
    s = _INGR_CODE_RE.sub("", raw)  # existing bracket-code stripping
    s = _WS_RE.sub(" ", s).strip()
    s = s.strip(_TRAILING_PUNCT)
    return s


def _strip_code(kor_ingr: str) -> str:
    """Remove the ``[Mxxxxxx]`` code prefix, keeping the Korean ingredient name."""
    return _normalize_name(kor_ingr)


def _split_pair(kor_raw: str, eng_raw: str) -> list[tuple[str, str]]:
    """Split a (kor, eng) cell into per-ingredient pairs.

    We ONLY emit pairs from single-ingredient rows. Multi-ingredient rows
    cannot be trusted for alignment because the Korean side is delimited by
    ``|`` and the English side by ``/``, and their ordering often differs
    between the two columns — zipping would produce wrong cross-pairings
    (e.g. ``이부프로펜`` ↔ ``caffeine``). Single-ingredient rows are still
    plentiful (thousands across MFDS) and give us a clean high-precision
    seed set for synonym expansion.
    """
    kor_parts = [_strip_code(p) for p in kor_raw.split("|") if p.strip()]
    eng_parts = [_normalize_name(p) for p in re.split(r"[/,]", eng_raw) if p.strip()]
    # Drop pairs where either side became empty after normalization.
    kor_parts = [p for p in kor_parts if p]
    eng_parts = [p for p in eng_parts if p]
    if len(kor_parts) == 1 and len(eng_parts) == 1:
        return [(kor_parts[0], eng_parts[0])]
    return []


def _rows_from_db(db_path: Path) -> list[tuple[str, str]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT main_item_ingr, main_ingr_eng
            FROM drugs
            WHERE main_item_ingr IS NOT NULL
              AND main_ingr_eng IS NOT NULL
            """
        ).fetchall()
    finally:
        conn.close()
    return [(k or "", e or "") for k, e in rows]


def _rows_from_csv(csv_path: Path) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            kor = (row.get("MAIN_ITEM_INGR") or "").strip()
            eng = (row.get("MAIN_INGR_ENG") or "").strip()
            if kor and eng:
                seen.add((kor, eng))
    return sorted(seen)


def build_synonyms(
    out_path: Path,
    db_path: Path | None = None,
    csv_path: Path | None = None,
    manual_path: Path | None = None,
) -> dict[str, list[str]]:
    """Build bidirectional ingredient synonym dict and write it to ``out_path``.

    Returns the in-memory dict for ease of unit testing.
    """
    if db_path and db_path.exists():
        raw_rows = _rows_from_db(db_path)
        source = f"db:{db_path}"
    elif csv_path and csv_path.exists():
        raw_rows = _rows_from_csv(csv_path)
        source = f"csv:{csv_path}"
    else:
        raise FileNotFoundError(
            f"Neither DB ({db_path}) nor CSV ({csv_path}) source exists."
        )

    synonyms: dict[str, set[str]] = {}
    for kor_raw, eng_raw in raw_rows:
        for kor, eng in _split_pair(kor_raw, eng_raw):
            # ``_split_pair`` already normalized whitespace / punctuation via
            # ``_normalize_name``; we just lowercase ENG here and guard
            # against empties one more time.
            kor_n = _normalize_name(kor)
            eng_n = _normalize_name(eng).lower()
            if not kor_n or not eng_n:
                continue
            synonyms.setdefault(kor_n, set()).add(eng_n)
            synonyms.setdefault(eng_n, set()).add(kor_n)

    # Merge manual supplement (priority additions the extractor may miss —
    # salt forms, brand↔generic, common abbreviations).
    if manual_path and manual_path.exists():
        with open(manual_path, encoding="utf-8") as f:
            manual: dict[str, list[str]] = json.load(f)
        for key, values in manual.items():
            synonyms.setdefault(key, set()).update(v.lower() for v in values)
            for v in values:
                synonyms.setdefault(v.lower(), set()).add(key)

    final = {k: sorted(v) for k, v in synonyms.items()}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(final, ensure_ascii=False, indent=2))
    print(f"Saved {len(final)} synonym entries to {out_path} (source={source})")
    return final


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    pkg_data = root / "src" / "pillcare" / "_data"
    build_synonyms(
        out_path=pkg_data / "ingredient_synonyms.json",
        db_path=root / "pillcare.db",
        csv_path=root / "data" / "drug_permit_detail.csv",  # local-only, not in git
        manual_path=pkg_data / "ingredient_synonyms_manual.json",
    )
