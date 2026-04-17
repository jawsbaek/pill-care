"""LangGraph StateGraph pipeline for medication guidance generation."""

import logging
import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from pillcare.prompts import DRUG_GUIDANCE_TEMPLATE, SYSTEM_PROMPT
from pillcare.schemas import (
    DrugGuidance,
    DrugGuidanceOutput,
    DurWarning,
    GuidanceResult,
    GuidanceSection,
    SourceTier,
)
from pillcare.guardrails import filter_banned_words, post_verify
from pillcare.tools import make_collect_node, make_dur_node, make_match_node

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2


# --- State schemas ---
class PublicState(TypedDict, total=False):
    profile_id: str
    raw_records: list[dict]
    matched_drugs: list[dict]
    dur_alerts: list[dict]
    drug_infos: list[dict]
    guidance_result: dict | None
    errors: Annotated[list[str], operator.add]


# Internal state: includes private keys not exposed in input/output
class GraphState(PublicState, total=False):
    _retry_count: int
    _last_verify_errors: list[str]


def _make_generate_node(llm: Any):
    """Factory: creates generate node with LLM bound via closure."""

    def generate_node(state: dict) -> dict:
        drug_infos = state.get("drug_infos", [])
        dur_alerts = state.get("dur_alerts", [])

        drug_guidances = []
        dur_warnings = []
        warning_labels = []
        generation_errors: list[str] = []

        structured_llm = llm.with_structured_output(
            DrugGuidanceOutput, method="json_schema"
        )

        # Extract warning labels from data -- deterministic
        for info in drug_infos:
            sections = info.get("sections", {})
            if "경고" in sections:
                warning_labels.append(
                    f"{info.get('item_name', '')}: {sections['경고'][:100]}"
                )
            easy = info.get("easy") or {}
            if easy.get("atpn_warn_qesitm"):
                warning_labels.append(
                    f"{info.get('item_name', '')}: {easy['atpn_warn_qesitm'][:100]}"
                )

        # Build DUR warnings
        for alert in dur_alerts:
            dur_warnings.append(
                DurWarning(
                    drug_1=alert["drug_name_1"],
                    drug_2=alert["drug_name_2"],
                    reason=alert["reason"],
                    cross_clinic=alert["cross_clinic"],
                )
            )
            cross = " [다기관]" if alert["cross_clinic"] else ""
            warning_labels.append(
                f"[병용금기] {alert['drug_name_1']} x {alert['drug_name_2']}: {alert['reason']}{cross}"
            )

        # Format DUR text for prompts
        dur_text = ""
        if dur_alerts:
            lines = []
            for a in dur_alerts:
                cross = " [다기관 교차 처방]" if a["cross_clinic"] else ""
                lines.append(
                    f"- {a['drug_name_1']} x {a['drug_name_2']}: {a['reason']}{cross}"
                )
            dur_text = "\n".join(lines)

        # Generate per-drug guidance via structured output
        summary_points = []
        for info in drug_infos:
            sections_text = ""
            if info.get("sections"):
                for stype, stext in info["sections"].items():
                    sections_text += f"\n### {stype}\n{stext}\n"

            easy_text = ""
            if info.get("easy"):
                for key, val in info["easy"].items():
                    if val:
                        easy_text += f"{key}: {val}\n"

            prompt = DRUG_GUIDANCE_TEMPLATE.format(
                item_name=info.get("item_name", ""),
                main_item_ingr=info.get("main_item_ingr", ""),
                main_ingr_eng=info.get("main_ingr_eng", ""),
                entp_name=info.get("entp_name", ""),
                atc_code=info.get("atc_code", ""),
                etc_otc_code=info.get("etc_otc_code", ""),
                chart=info.get("chart", ""),
                total_content=info.get("total_content", ""),
                storage_method=info.get("storage_method", ""),
                valid_term=info.get("valid_term", ""),
                ee_text=info.get("ee_doc_data", "") or "(없음)",
                ud_text=info.get("ud_doc_data", "") or "(없음)",
                nb_sections=sections_text or "(없음)",
                easy_text=easy_text or "(없음)",
                dur_alerts=dur_text or "(없음)",
            )

            try:
                messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
                output: DrugGuidanceOutput = structured_llm.invoke(messages)
                guidance = output.to_drug_guidance()
            except Exception:
                # Fallback: create minimal guidance on LLM failure
                logger.error(
                    "LLM call failed for %s", info.get("item_name", ""), exc_info=True
                )
                guidance = DrugGuidance(
                    drug_name=info.get("item_name", ""),
                    sections={
                        "명칭": GuidanceSection(
                            title="명칭",
                            content=info.get("item_name", ""),
                            source_tier=SourceTier.T1_PERMIT,
                        ),
                    },
                )
                generation_errors.append(
                    f"[ERROR] LLM 호출 실패: {info.get('item_name', '')} — 서비스 오류"
                )

            # Apply banned word filter
            for section in guidance.sections.values():
                section.content = filter_banned_words(section.content)

            drug_guidances.append(guidance)

            for a in dur_alerts:
                if a["drug_name_1"] == info.get("item_name") or a[
                    "drug_name_2"
                ] == info.get("item_name"):
                    summary_points.append(
                        f"{a['drug_name_1']}과 {a['drug_name_2']}: {a['reason']}"
                    )

        # Apply banned word filter to summary and warning labels
        summary_points = [filter_banned_words(p) for p in summary_points]
        warning_labels = [filter_banned_words(label) for label in warning_labels]

        result = GuidanceResult(
            drug_guidances=drug_guidances,
            dur_warnings=dur_warnings,
            summary=list(dict.fromkeys(summary_points)),
            warning_labels=warning_labels,
        )
        return {
            "guidance_result": result.model_dump(mode="json"),
            "errors": generation_errors,
        }

    return generate_node


def _verify_node(state: dict) -> dict:
    """Post-verification node."""
    result_data = state.get("guidance_result")
    retry_count = state.get("_retry_count", 0)

    if not result_data:
        critical_err = ["[CRITICAL] 생성 결과 없음"]
        return {
            "errors": critical_err,
            "_last_verify_errors": critical_err,
            "_retry_count": retry_count + 1,
        }

    result = (
        GuidanceResult(**result_data) if isinstance(result_data, dict) else result_data
    )
    dur_alerts = state.get("dur_alerts", [])

    new_errors = post_verify(result, dur_alerts)
    return {
        "errors": new_errors,
        "_last_verify_errors": new_errors,
        "_retry_count": retry_count + 1,
    }


def _should_retry(state: dict) -> str:
    errors = state.get("_last_verify_errors", [])
    critical = [e for e in errors if e.startswith("[CRITICAL]")]
    retry_count = state.get("_retry_count", 0)
    if critical and retry_count < _MAX_RETRIES:
        return "generate"
    return "done"


def build_pipeline(db_path: str, llm: Any):
    """Build the LangGraph StateGraph."""
    builder = StateGraph(
        GraphState, input_schema=PublicState, output_schema=PublicState
    )

    builder.add_node("match_drugs", make_match_node(db_path))
    builder.add_node("check_dur", make_dur_node(db_path))
    builder.add_node("collect_info", make_collect_node(db_path))
    builder.add_node("generate", _make_generate_node(llm))
    builder.add_node("verify", _verify_node)

    builder.add_edge(START, "match_drugs")
    builder.add_edge("match_drugs", "check_dur")
    builder.add_edge("check_dur", "collect_info")
    builder.add_edge("collect_info", "generate")
    builder.add_edge("generate", "verify")
    builder.add_conditional_edges(
        "verify", _should_retry, {"generate": "generate", "done": END}
    )

    return builder.compile()


def run_pipeline(
    db_path: str, llm: Any, records: list[dict], profile_id: str = "default"
) -> dict:
    """Run the full pipeline."""
    graph = build_pipeline(db_path, llm)
    initial_state: PublicState = {
        "profile_id": profile_id,
        "raw_records": records,
        "matched_drugs": [],
        "dur_alerts": [],
        "drug_infos": [],
        "guidance_result": None,
        "errors": [],
    }
    return graph.invoke(initial_state)
