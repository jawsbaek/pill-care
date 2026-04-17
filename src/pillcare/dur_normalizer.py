"""Normalize DUR CSV (product-level 542K rows) to ingredient-pair level.

Also provides normalize_* helpers for the 7 additional HIRA DUR rule types
(age / pregnancy / dose / duplicate / elderly / specific_age /
pregnant_woman). The column-name literals follow the pattern of the existing
병용금기 CSV; if the real HIRA CSV headers differ, only the literal strings
here need to change (callers and DB schemas are column-agnostic).
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DurPair:
    ingr_code_1: str
    ingr_name_1: str
    ingr_code_2: str
    ingr_name_2: str
    reason: str
    notice_date: str


def _normalize_reason(reason: str) -> str:
    text = reason.strip()
    text = re.sub(
        r"기능[적성]\s*신부전에\s*의(?:해|한)?\s*유산\s*산성증",
        "기능적 신부전에 의한 유산산성증",
        text,
    )
    text = re.sub(r"\s+", " ", text)
    return text


def _make_key(code_1: str, code_2: str) -> tuple[str, str]:
    return (min(code_1, code_2), max(code_1, code_2))


def normalize_dur(csv_path: Path, encoding: str = "cp949") -> list[DurPair]:
    """Read DUR CSV and normalize to ingredient-pair level."""
    pair_map: dict[tuple[str, str], DurPair] = {}

    with open(csv_path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_1 = row["성분코드1"].strip()
            code_2 = row["성분코드2"].strip()
            if not code_1 or not code_2:
                continue
            key = _make_key(code_1, code_2)
            reason = _normalize_reason(row.get("금기사유", ""))
            if key not in pair_map:
                if key[0] == code_1:
                    pair_map[key] = DurPair(
                        ingr_code_1=code_1,
                        ingr_name_1=row["성분명1"].strip(),
                        ingr_code_2=code_2,
                        ingr_name_2=row["성분명2"].strip(),
                        reason=reason,
                        notice_date=row.get("공고일자", "").strip(),
                    )
                else:
                    pair_map[key] = DurPair(
                        ingr_code_1=code_2,
                        ingr_name_1=row["성분명2"].strip(),
                        ingr_code_2=code_1,
                        ingr_name_2=row["성분명1"].strip(),
                        reason=reason,
                        notice_date=row.get("공고일자", "").strip(),
                    )
            else:
                # Preserve multiple distinct reasons per pair (spec §4-2)
                existing = pair_map[key]
                if reason and reason not in existing.reason:
                    existing.reason = f"{existing.reason}; {reason}"
    return list(pair_map.values())


# --- HIRA DUR 7 additional rule types ---
#
# Each normalize_* returns a list[dict] with stable keys consumed by
# db_builder. Encoding defaults to utf-8-sig (fixtures) but real HIRA CSVs
# may be CP949; callers can pass ``encoding="cp949"`` explicitly.


def _open_csv(csv_path: str | Path, encoding: str = "utf-8-sig"):
    return open(csv_path, encoding=encoding, newline="")


def normalize_age_prohibition(
    csv_path: str | Path, encoding: str = "utf-8-sig"
) -> list[dict]:
    """연령금기 — absolute age contraindication (e.g. 영유아 2세 미만)."""
    rows: list[dict] = []
    with _open_csv(csv_path, encoding) as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = (r.get("성분코드") or "").strip()
            if not code:
                continue
            rows.append(
                {
                    "ingredient_code": code,
                    "ingredient_name": (r.get("성분명") or "").strip(),
                    "age_min": int((r.get("금지연령하한") or "0").strip() or 0),
                    "age_max": int((r.get("금지연령상한") or "0").strip() or 0),
                    "age_unit": (r.get("단위") or "year").strip() or "year",
                    "reason": _normalize_reason(r.get("사유", "")),
                }
            )
    return rows


def normalize_pregnancy_prohibition(
    csv_path: str | Path, encoding: str = "utf-8-sig"
) -> list[dict]:
    """임부금기 — absolute pregnancy contraindication."""
    rows: list[dict] = []
    with _open_csv(csv_path, encoding) as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = (r.get("성분코드") or "").strip()
            if not code:
                continue
            rows.append(
                {
                    "ingredient_code": code,
                    "ingredient_name": (r.get("성분명") or "").strip(),
                    "week_min": int((r.get("임신주차하한") or "0").strip() or 0),
                    "week_max": int((r.get("임신주차상한") or "40").strip() or 40),
                    "reason": _normalize_reason(r.get("사유", "")),
                }
            )
    return rows


def normalize_dose_warning(
    csv_path: str | Path, encoding: str = "utf-8-sig"
) -> list[dict]:
    """용량주의 — daily maximum dose warning."""
    rows: list[dict] = []
    with _open_csv(csv_path, encoding) as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = (r.get("성분코드") or "").strip()
            if not code:
                continue
            rows.append(
                {
                    "ingredient_code": code,
                    "ingredient_name": (r.get("성분명") or "").strip(),
                    "daily_max": float((r.get("1일최대용량") or "0").strip() or 0),
                    "dose_unit": (r.get("용량단위") or "mg").strip() or "mg",
                    "reason": _normalize_reason(r.get("사유", "")),
                }
            )
    return rows


def normalize_duplicate_therapy(
    csv_path: str | Path, encoding: str = "utf-8-sig"
) -> list[dict]:
    """효능군중복 — therapeutic duplication by 효능군 (ATC-like grouping)."""
    rows: list[dict] = []
    with _open_csv(csv_path, encoding) as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = (r.get("성분코드") or "").strip()
            class_code = (r.get("효능군코드") or "").strip()
            if not code or not class_code:
                continue
            rows.append(
                {
                    "class_code": class_code,
                    "class_name": (r.get("효능군명") or "").strip(),
                    "ingredient_code": code,
                    "ingredient_name": (r.get("성분명") or "").strip(),
                }
            )
    return rows


def normalize_elderly_warning(
    csv_path: str | Path, encoding: str = "utf-8-sig"
) -> list[dict]:
    """노인주의 — elderly (>=대상연령) warning, Beers-list style."""
    rows: list[dict] = []
    with _open_csv(csv_path, encoding) as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = (r.get("성분코드") or "").strip()
            if not code:
                continue
            rows.append(
                {
                    "ingredient_code": code,
                    "ingredient_name": (r.get("성분명") or "").strip(),
                    "target_age": int((r.get("대상연령") or "65").strip() or 65),
                    "reason": _normalize_reason(r.get("사유", "")),
                }
            )
    return rows


def normalize_specific_age(
    csv_path: str | Path, encoding: str = "utf-8-sig"
) -> list[dict]:
    """특정연령 — bounded age-range warning (e.g. 청소년 12–18세)."""
    rows: list[dict] = []
    with _open_csv(csv_path, encoding) as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = (r.get("성분코드") or "").strip()
            if not code:
                continue
            rows.append(
                {
                    "ingredient_code": code,
                    "ingredient_name": (r.get("성분명") or "").strip(),
                    "age_min": int((r.get("대상연령하한") or "0").strip() or 0),
                    "age_max": int((r.get("대상연령상한") or "0").strip() or 0),
                    "reason": _normalize_reason(r.get("사유", "")),
                }
            )
    return rows


def normalize_pregnant_woman(
    csv_path: str | Path, encoding: str = "utf-8-sig"
) -> list[dict]:
    """임산부주의 — pregnancy warning (beyond absolute 임부금기)."""
    rows: list[dict] = []
    with _open_csv(csv_path, encoding) as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = (r.get("성분코드") or "").strip()
            if not code:
                continue
            rows.append(
                {
                    "ingredient_code": code,
                    "ingredient_name": (r.get("성분명") or "").strip(),
                    "week_min": int((r.get("임신주차하한") or "0").strip() or 0),
                    "week_max": int((r.get("임신주차상한") or "40").strip() or 40),
                    "reason": _normalize_reason(r.get("사유", "")),
                }
            )
    return rows
