"""Gold set CSV loaders for 600-case Korean medication eval harness.

Schema per file defined in data/gold_set/v1/README.md:
- dur_pairs.csv: drug_1, drug_2, expected_alert, rule_type, notes, reviewed_by
- guidance_text.csv: drug_name, context, expected_content_keywords, forbidden_keywords
- red_team.csv: injection_prompt, attack_type, expected_refusal
- naturalness.csv: drug_name, response_variant, rating_1_5, notes
- symptom_mapping.csv: symptom, current_medications, expected_linked_drugs

Gold set files are NOT required to exist; loaders return [] when missing
so CI can run pipeline tests without the full eval dataset present.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

GOLD_SET_ROOT = Path(__file__).resolve().parents[3] / "data" / "gold_set" / "v1"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_dur_pairs(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or GOLD_SET_ROOT / "dur_pairs.csv"
    rows = _read_csv(path)
    parsed = []
    for r in rows:
        parsed.append(
            {
                "drug_1": r.get("drug_1", "").strip(),
                "drug_2": r.get("drug_2", "").strip(),
                "expected_alert": r.get("expected_alert", "").lower() == "true",
                "rule_type": r.get("rule_type", "").strip(),
                "notes": r.get("notes", "").strip(),
                "reviewed_by": r.get("reviewed_by", "").strip(),
            }
        )
    return parsed


def load_guidance_gold(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or GOLD_SET_ROOT / "guidance_text.csv"
    rows = _read_csv(path)
    parsed = []
    for r in rows:
        parsed.append(
            {
                "drug_name": r.get("drug_name", "").strip(),
                "context": r.get("context", "").strip(),
                "expected_content_keywords": [
                    k.strip()
                    for k in r.get("expected_content_keywords", "").split("|")
                    if k.strip()
                ],
                "forbidden_keywords": [
                    k.strip()
                    for k in r.get("forbidden_keywords", "").split("|")
                    if k.strip()
                ],
            }
        )
    return parsed


def load_red_team(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or GOLD_SET_ROOT / "red_team.csv"
    rows = _read_csv(path)
    parsed = []
    for r in rows:
        parsed.append(
            {
                "injection_prompt": r.get("injection_prompt", "").strip(),
                "attack_type": r.get("attack_type", "").strip(),
                "expected_refusal": r.get("expected_refusal", "").lower() == "true",
            }
        )
    return parsed
