"""Normalize DUR CSV (product-level 542K rows) to ingredient-pair level."""

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
        r"기능[적성]\s*신부전에\s*의한?\s*유산\s*산성증",
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
    return list(pair_map.values())
