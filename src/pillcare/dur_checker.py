"""Multi-ingredient N×N DUR cross-check.

Dispatches to 8 HIRA DUR rule types. Combined (병용금기) runs unconditionally;
the 7 patient-context rules (age/pregnancy/dose/duplicate/elderly/specific_age/
pregnant_woman) run only when the relevant context fields are provided.

The public entrypoint ``check_dur`` preserves its legacy positional signature
``check_dur(db_path, drugs)`` for backwards compatibility with existing pipeline
code, and adds an optional ``patient_context`` kwarg.
"""

import sqlite3
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

from pillcare.schemas import DurRuleType


@dataclass
class DurAlert:
    # Required — always populated.
    drug_name_1: str
    department_1: str
    ingr_code_1: str
    ingr_name_1: str
    reason: str
    # Optional — only populated for pair rules (COMBINED, DUPLICATE).
    drug_name_2: str | None = None
    department_2: str | None = None
    ingr_code_2: str | None = None
    ingr_name_2: str | None = None
    cross_clinic: bool = False
    rule_type: DurRuleType = DurRuleType.COMBINED
    extra: dict = field(default_factory=dict)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _check_combined(conn: sqlite3.Connection, drugs: list[dict]) -> list[DurAlert]:
    alerts: list[DurAlert] = []
    if not _table_exists(conn, "dur_pairs"):
        return alerts
    dur_rows = conn.execute("SELECT * FROM dur_pairs").fetchall()
    dur_lookup: dict[tuple[str, str], dict] = {}
    for row in dur_rows:
        entry = dict(row)
        dur_lookup[(row["ingr_code_1"], row["ingr_code_2"])] = entry
        dur_lookup[(row["ingr_code_2"], row["ingr_code_1"])] = entry

    seen: set[tuple] = set()
    for d1, d2 in combinations(drugs, 2):
        for code_a in d1["ingr_codes"]:
            for code_b in d2["ingr_codes"]:
                key = (code_a, code_b)
                if key not in dur_lookup:
                    continue
                dedup_key = (
                    d1["drug_name"],
                    d1["department"],
                    d2["drug_name"],
                    d2["department"],
                    code_a,
                    code_b,
                )
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                row = dur_lookup[key]
                if row["ingr_code_1"] == code_a:
                    name_a, name_b = row["ingr_name_1"], row["ingr_name_2"]
                else:
                    name_a, name_b = row["ingr_name_2"], row["ingr_name_1"]
                alerts.append(
                    DurAlert(
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
                        rule_type=DurRuleType.COMBINED,
                    )
                )
    return alerts


def _single_drug_alerts(
    conn: sqlite3.Connection,
    drugs: list[dict],
    rule_type: DurRuleType,
    sql: str,
    predicate,  # callable(row, context) -> bool
    context: dict,
) -> list[DurAlert]:
    alerts: list[DurAlert] = []
    seen: set[tuple] = set()
    for d in drugs:
        for code in d["ingr_codes"]:
            rows = conn.execute(sql, (code,)).fetchall()
            for row in rows:
                if not predicate(row, context):
                    continue
                dedup = (d["drug_name"], d["department"], code, rule_type)
                if dedup in seen:
                    continue
                seen.add(dedup)
                alerts.append(
                    DurAlert(
                        drug_name_1=d["drug_name"],
                        department_1=d["department"],
                        ingr_code_1=code,
                        ingr_name_1=row["ingredient_name"],
                        reason=row["reason"],
                        rule_type=rule_type,
                    )
                )
    return alerts


def _check_age(
    conn: sqlite3.Connection, drugs: list[dict], age_years: float
) -> list[DurAlert]:
    if not _table_exists(conn, "dur_age"):
        return []

    def predicate(row, ctx) -> bool:
        unit = (row["age_unit"] or "year").lower()
        age = ctx["age_years"]
        if unit.startswith("month"):
            age = age * 12
        return row["age_min"] <= age <= row["age_max"]

    return _single_drug_alerts(
        conn,
        drugs,
        DurRuleType.AGE,
        "SELECT ingredient_name, age_min, age_max, age_unit, reason "
        "FROM dur_age WHERE ingredient_code = ?",
        predicate,
        {"age_years": age_years},
    )


def _check_pregnancy(
    conn: sqlite3.Connection, drugs: list[dict], pregnancy_week: int | None
) -> list[DurAlert]:
    if not _table_exists(conn, "dur_pregnancy"):
        return []

    def predicate(row, ctx) -> bool:
        week = ctx.get("pregnancy_week")
        if week is None:
            # Missing week → assume full-term window; alert if rule covers any week.
            return True
        return row["week_min"] <= week <= row["week_max"]

    return _single_drug_alerts(
        conn,
        drugs,
        DurRuleType.PREGNANCY,
        "SELECT ingredient_name, week_min, week_max, reason "
        "FROM dur_pregnancy WHERE ingredient_code = ?",
        predicate,
        {"pregnancy_week": pregnancy_week},
    )


def _check_dose(conn: sqlite3.Connection, drugs: list[dict]) -> list[DurAlert]:
    """Dose warning: alert if daily_dose (if provided per drug) exceeds max.

    Each drug dict MAY carry a ``daily_dose`` numeric field (in the same unit
    as the rule's ``dose_unit``). If absent we emit an informational alert
    whenever a matching rule exists, because the clinician should be aware of
    the ceiling even without an explicit dose.
    """
    if not _table_exists(conn, "dur_dose"):
        return []
    alerts: list[DurAlert] = []
    seen: set[tuple] = set()
    sql = (
        "SELECT ingredient_name, daily_max, dose_unit, reason "
        "FROM dur_dose WHERE ingredient_code = ?"
    )
    for d in drugs:
        daily_dose = d.get("daily_dose")
        for code in d["ingr_codes"]:
            for row in conn.execute(sql, (code,)).fetchall():
                if daily_dose is not None and daily_dose <= row["daily_max"]:
                    continue
                dedup = (d["drug_name"], d["department"], code, DurRuleType.DOSE)
                if dedup in seen:
                    continue
                seen.add(dedup)
                alerts.append(
                    DurAlert(
                        drug_name_1=d["drug_name"],
                        department_1=d["department"],
                        ingr_code_1=code,
                        ingr_name_1=row["ingredient_name"],
                        reason=(
                            f"{row['reason']} (1일 최대 {row['daily_max']:g}"
                            f"{row['dose_unit']})"
                        ),
                        rule_type=DurRuleType.DOSE,
                    )
                )
    return alerts


def _check_duplicate(conn: sqlite3.Connection, drugs: list[dict]) -> list[DurAlert]:
    """Therapeutic duplication — two different drugs share the same 효능군."""
    if not _table_exists(conn, "dur_duplicate"):
        return []
    alerts: list[DurAlert] = []
    sql = (
        "SELECT class_code, class_name, ingredient_name "
        "FROM dur_duplicate WHERE ingredient_code = ?"
    )
    # Map each (drug, ingr_code) → list of classes.
    drug_classes: list[tuple[dict, str, list[sqlite3.Row]]] = []
    for d in drugs:
        for code in d["ingr_codes"]:
            rows = conn.execute(sql, (code,)).fetchall()
            if rows:
                drug_classes.append((d, code, rows))

    seen: set[tuple] = set()
    for (d1, code_a, rows_a), (d2, code_b, rows_b) in combinations(drug_classes, 2):
        if d1["drug_name"] == d2["drug_name"]:
            continue
        classes_a = {r["class_code"]: r for r in rows_a}
        for rb in rows_b:
            if rb["class_code"] not in classes_a:
                continue
            ra = classes_a[rb["class_code"]]
            dedup = tuple(
                sorted(
                    [
                        (d1["drug_name"], d1["department"], code_a),
                        (d2["drug_name"], d2["department"], code_b),
                    ]
                )
                + [rb["class_code"]]
            )
            if dedup in seen:
                continue
            seen.add(dedup)
            alerts.append(
                DurAlert(
                    drug_name_1=d1["drug_name"],
                    department_1=d1["department"],
                    ingr_code_1=code_a,
                    ingr_name_1=ra["ingredient_name"],
                    drug_name_2=d2["drug_name"],
                    department_2=d2["department"],
                    ingr_code_2=code_b,
                    ingr_name_2=rb["ingredient_name"],
                    reason=f"효능군 중복: {rb['class_name']} ({rb['class_code']})",
                    cross_clinic=(d1["department"] != d2["department"]),
                    rule_type=DurRuleType.DUPLICATE,
                )
            )
    return alerts


def _check_elderly(
    conn: sqlite3.Connection, drugs: list[dict], age_years: float
) -> list[DurAlert]:
    if not _table_exists(conn, "dur_elderly"):
        return []

    def predicate(row, ctx) -> bool:
        return ctx["age_years"] >= row["target_age"]

    return _single_drug_alerts(
        conn,
        drugs,
        DurRuleType.ELDERLY,
        "SELECT ingredient_name, target_age, reason "
        "FROM dur_elderly WHERE ingredient_code = ?",
        predicate,
        {"age_years": age_years},
    )


def _check_specific_age(
    conn: sqlite3.Connection, drugs: list[dict], age_years: float
) -> list[DurAlert]:
    if not _table_exists(conn, "dur_specific_age"):
        return []

    def predicate(row, ctx) -> bool:
        return row["age_min"] <= ctx["age_years"] <= row["age_max"]

    return _single_drug_alerts(
        conn,
        drugs,
        DurRuleType.SPECIFIC_AGE,
        "SELECT ingredient_name, age_min, age_max, reason "
        "FROM dur_specific_age WHERE ingredient_code = ?",
        predicate,
        {"age_years": age_years},
    )


def _check_pregnant_woman(
    conn: sqlite3.Connection, drugs: list[dict], pregnancy_week: int | None
) -> list[DurAlert]:
    if not _table_exists(conn, "dur_pregnant_woman"):
        return []

    def predicate(row, ctx) -> bool:
        week = ctx.get("pregnancy_week")
        if week is None:
            return True
        return row["week_min"] <= week <= row["week_max"]

    return _single_drug_alerts(
        conn,
        drugs,
        DurRuleType.PREGNANT_WOMAN,
        "SELECT ingredient_name, week_min, week_max, reason "
        "FROM dur_pregnant_woman WHERE ingredient_code = ?",
        predicate,
        {"pregnancy_week": pregnancy_week},
    )


def check_dur(
    db_path: Path | str,
    drugs: list[dict],
    patient_context: dict | None = None,
) -> list[DurAlert]:
    """Run the 8-rule HIRA DUR dispatch.

    Args:
        db_path: SQLite DB path.
        drugs: list of {drug_name, department, ingr_codes[, daily_dose]}.
        patient_context: optional dict with any of:
            - age_years (float): patient age in years
            - is_pregnant (bool)
            - pregnancy_week (int): gestational week 0–40
            If None, only COMBINED and DOSE/DUPLICATE (context-free) rules run.

    Returns:
        list[DurAlert] across all applicable rule types. Empty list if no
        violations.
    """
    patient_context = patient_context or {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        alerts: list[DurAlert] = []

        # 1. COMBINED — always
        alerts.extend(_check_combined(conn, drugs))

        # 2. AGE
        if "age_years" in patient_context:
            alerts.extend(_check_age(conn, drugs, patient_context["age_years"]))

        # 3. PREGNANCY (absolute contraindication)
        if patient_context.get("is_pregnant"):
            alerts.extend(
                _check_pregnancy(conn, drugs, patient_context.get("pregnancy_week"))
            )

        # 4. DOSE — context-free (uses per-drug daily_dose if provided)
        alerts.extend(_check_dose(conn, drugs))

        # 5. DUPLICATE — context-free
        alerts.extend(_check_duplicate(conn, drugs))

        # 6. ELDERLY
        if patient_context.get("age_years", 0) >= 65:
            alerts.extend(_check_elderly(conn, drugs, patient_context["age_years"]))

        # 7. SPECIFIC_AGE
        if "age_years" in patient_context:
            alerts.extend(
                _check_specific_age(conn, drugs, patient_context["age_years"])
            )

        # 8. PREGNANT_WOMAN (beyond absolute 임부금기)
        if patient_context.get("is_pregnant"):
            alerts.extend(
                _check_pregnant_woman(
                    conn, drugs, patient_context.get("pregnancy_week")
                )
            )

        return alerts
    finally:
        conn.close()
