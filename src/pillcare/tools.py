"""Deterministic node functions for LangGraph pipeline."""

from dataclasses import asdict
from pathlib import Path

from pillcare.drug_info import get_drug_info
from pillcare.drug_matcher import match_drug
from pillcare.dur_checker import check_dur
from pillcare.observability import observe
from pillcare.schemas import DurAlertModel, MatchedDrug


def make_match_node(db_path: str):
    """Factory: creates match_drugs node with db_path bound via closure."""

    @observe(name="match_drugs")
    def match_drugs_node(state: dict) -> dict:
        _db = Path(db_path)
        matched = []
        new_errors = []  # only new errors — reducer auto-accumulates
        for rec in state["raw_records"]:
            result = match_drug(_db, rec["drug_name"], edi_code=rec.get("drug_code"))
            if result:
                matched.append(
                    MatchedDrug(
                        item_seq=result.item_seq,
                        drug_name=rec["drug_name"],
                        item_name=result.item_name,
                        department=rec.get("department", "미지정"),
                        ingr_codes=result.ingr_codes,
                        edi_code=rec.get("drug_code"),
                        match_score=result.score,
                    ).model_dump()
                )
            else:
                new_errors.append(f"매칭 실패: {rec['drug_name']}")
        return {"matched_drugs": matched, "errors": new_errors}

    return match_drugs_node


def make_dur_node(db_path: str):
    """Factory: creates check_dur node with db_path bound via closure."""

    @observe(name="check_dur")
    def check_dur_node(state: dict) -> dict:
        drugs_for_check = [
            {
                "drug_name": d["drug_name"],
                "department": d["department"],
                "ingr_codes": d["ingr_codes"],
            }
            for d in state["matched_drugs"]
        ]
        patient_context = state.get("patient_context") or None
        alerts = check_dur(
            Path(db_path), drugs_for_check, patient_context=patient_context
        )
        return {
            "dur_alerts": [
                DurAlertModel(
                    drug_name_1=a.drug_name_1,
                    department_1=a.department_1,
                    ingr_code_1=a.ingr_code_1,
                    ingr_name_1=a.ingr_name_1,
                    drug_name_2=a.drug_name_2,
                    department_2=a.department_2,
                    ingr_code_2=a.ingr_code_2,
                    ingr_name_2=a.ingr_name_2,
                    reason=a.reason,
                    cross_clinic=a.cross_clinic,
                    rule_type=a.rule_type,
                ).model_dump()
                for a in alerts
            ]
        }

    return check_dur_node


def make_collect_node(db_path: str):
    """Factory: creates collect_info node with db_path bound via closure."""

    @observe(name="collect_info")
    def collect_info_node(state: dict) -> dict:
        infos = []
        for drug in state["matched_drugs"]:
            info = get_drug_info(Path(db_path), drug["item_seq"])
            if info:
                infos.append(asdict(info))
        return {"drug_infos": infos}

    return collect_info_node
