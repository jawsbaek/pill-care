"""Multi-ingredient N×N DUR cross-check."""

import sqlite3
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path


@dataclass
class DurAlert:
    drug_name_1: str
    department_1: str
    ingr_code_1: str
    ingr_name_1: str
    drug_name_2: str
    department_2: str
    ingr_code_2: str
    ingr_name_2: str
    reason: str
    cross_clinic: bool


def check_dur(db_path: Path, drugs: list[dict]) -> list[DurAlert]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    dur_rows = conn.execute("SELECT * FROM dur_pairs").fetchall()
    conn.close()

    dur_lookup: dict[tuple[str, str], dict] = {}
    for row in dur_rows:
        entry = dict(row)
        dur_lookup[(row["ingr_code_1"], row["ingr_code_2"])] = entry
        dur_lookup[(row["ingr_code_2"], row["ingr_code_1"])] = entry

    alerts = []
    seen: set[tuple[str, str, str, str]] = set()

    for d1, d2 in combinations(drugs, 2):
        for code_a in d1["ingr_codes"]:
            for code_b in d2["ingr_codes"]:
                key = (code_a, code_b)
                if key not in dur_lookup:
                    continue

                dedup_key = (d1["drug_name"], d2["drug_name"], code_a, code_b)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                row = dur_lookup[key]
                if row["ingr_code_1"] == code_a:
                    name_a, name_b = row["ingr_name_1"], row["ingr_name_2"]
                else:
                    name_a, name_b = row["ingr_name_2"], row["ingr_name_1"]

                alerts.append(DurAlert(
                    drug_name_1=d1["drug_name"],
                    department_1=d1["department"],
                    ingr_code_1=code_a,
                    ingr_name_1=name_a,
                    drug_name_2=d2["drug_name"],
                    department_2=d2["department"],
                    ingr_code_2=code_b,
                    ingr_name_2=name_b,
                    reason=row["reason"],
                    cross_clinic=(d1["department"] != d2["department"]),
                ))

    return alerts
