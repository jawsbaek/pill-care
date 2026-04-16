"""LangGraph StateGraph pipeline for medication guidance generation."""

import operator
import re
from typing import Annotated, Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from pillcare.prompts import DRUG_GUIDANCE_TEMPLATE, SYSTEM_PROMPT
from pillcare.schemas import (
    DrugGuidance, DurWarning, GuidanceResult, GuidanceSection, SourceTier,
)
from pillcare.tools import make_collect_node, make_dur_node, make_match_node


# --- State schemas ---
# Public state: visible in graph input/output
class PublicState(TypedDict, total=False):
    profile_id: str
    raw_records: list[dict]
    matched_drugs: list[dict]
    dur_alerts: list[dict]
    drug_infos: list[dict]
    guidance_result: dict | None
    errors: Annotated[list[str], operator.add]  # reducer: auto-accumulate


# Internal state: includes private keys not exposed in input/output
class GraphState(PublicState, total=False):
    _retry_count: int             # private — retry cap
    _last_verify_errors: list[str]  # private — latest verify pass only (not accumulated)


# --- Section names for parsing ---
_SECTION_NAMES = [
    "명칭", "성상", "효능효과", "투여의의", "용법용량",
    "저장방법", "주의사항", "상호작용", "투여종료후", "기타",
]

_HEADER_RE = re.compile(
    r"^(?:#{1,3}\s*)?(?:\d+[\.\)]\s*)?"
    r"(" + "|".join(re.escape(s) for s in _SECTION_NAMES) + r")"
)


def _detect_source_tier(content: str) -> SourceTier:
    if "[T1:DUR]" in content:
        return SourceTier.T1_DUR
    if "[T1:허가정보]" in content:
        return SourceTier.T1_PERMIT
    if "[T1:e약은요]" in content:
        return SourceTier.T1_EASY
    return SourceTier.T4_AI


def _parse_drug_guidance(drug_name: str, response_text: str) -> DrugGuidance:
    """Parse LLM response into structured DrugGuidance."""
    sections: dict[str, GuidanceSection] = {}
    current_section = None
    current_lines: list[str] = []

    for line in response_text.split("\n"):
        m = _HEADER_RE.match(line.strip())
        if m:
            if current_section and current_lines:
                content = "\n".join(current_lines).strip()
                sections[current_section] = GuidanceSection(
                    title=current_section, content=content,
                    source_tier=_detect_source_tier(content),
                )
            current_section = m.group(1)
            current_lines = []
        elif current_section:
            current_lines.append(line)

    if current_section and current_lines:
        content = "\n".join(current_lines).strip()
        sections[current_section] = GuidanceSection(
            title=current_section, content=content,
            source_tier=_detect_source_tier(content),
        )

    return DrugGuidance(drug_name=drug_name, sections=sections)


def _make_generate_node(llm: Any):
    """Factory: creates generate node with LLM bound via closure."""
    def generate_node(state: dict) -> dict:
        drug_infos = state.get("drug_infos", [])
        dur_alerts = state.get("dur_alerts", [])

        drug_guidances = []
        dur_warnings = []
        warning_labels = []

        # Extract warning labels from data -- deterministic
        for info in drug_infos:
            sections = info.get("sections", {})
            if "경고" in sections:
                warning_labels.append(f"{info.get('item_name', '')}: {sections['경고'][:100]}")
            easy = info.get("easy") or {}
            if easy.get("atpn_warn_qesitm"):
                warning_labels.append(f"{info.get('item_name', '')}: {easy['atpn_warn_qesitm'][:100]}")

        # Build DUR warnings
        for alert in dur_alerts:
            dur_warnings.append(DurWarning(
                drug_1=alert["drug_name_1"], drug_2=alert["drug_name_2"],
                reason=alert["reason"], cross_clinic=alert["cross_clinic"],
            ))
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
                lines.append(f"- {a['drug_name_1']} x {a['drug_name_2']}: {a['reason']}{cross}")
            dur_text = "\n".join(lines)

        # Generate per-drug guidance
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
                messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
                response = llm.invoke(messages)
                response_text = response.content if isinstance(response.content, str) else str(response.content)
            except Exception as e:
                response_text = f"### 1. 명칭\n[T1:허가정보] {info.get('item_name', '')}\n\n(LLM 오류: {e})"

            guidance = _parse_drug_guidance(info.get("item_name", ""), response_text)
            drug_guidances.append(guidance.model_dump())

            for a in dur_alerts:
                if a["drug_name_1"] == info.get("item_name") or a["drug_name_2"] == info.get("item_name"):
                    summary_points.append(
                        f"{a['drug_name_1']}과 {a['drug_name_2']}: {a['reason']} [T1:DUR]"
                    )

        result = GuidanceResult(
            drug_guidances=[DrugGuidance(**g) for g in drug_guidances],
            dur_warnings=dur_warnings,
            summary=list(set(summary_points)),
            warning_labels=warning_labels,
        )
        return {"guidance_result": result.model_dump()}

    return generate_node


def _verify_node(state: dict) -> dict:
    """Post-verification node. Returns only NEW errors (reducer handles accumulation)."""
    from pillcare.guardrails import post_verify

    result_data = state.get("guidance_result")
    retry_count = state.get("_retry_count", 0)

    if not result_data:
        return {"errors": ["생성 결과 없음"], "_retry_count": retry_count + 1}

    result = GuidanceResult(**result_data) if isinstance(result_data, dict) else result_data
    dur_alerts = state.get("dur_alerts", [])

    new_errors = post_verify(result, dur_alerts)
    return {
        "errors": new_errors,                # accumulated via reducer
        "_last_verify_errors": new_errors,   # latest pass only (for retry decision)
        "_retry_count": retry_count + 1,
    }


def _should_retry(state: dict) -> str:
    # Use latest verify pass only — not accumulated errors
    errors = state.get("_last_verify_errors", [])
    critical = [e for e in errors if e.startswith("[CRITICAL]")]
    retry_count = state.get("_retry_count", 0)
    if critical and retry_count < 2:
        return "generate"
    return "done"


def build_pipeline(db_path: str, llm: Any):
    """Build the LangGraph StateGraph.

    LLM and db_path are injected via closures — NOT in state.
    Uses input=PublicState, output=PublicState to hide _retry_count from callers.
    """
    builder = StateGraph(GraphState, input_schema=PublicState, output_schema=PublicState)

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
    builder.add_conditional_edges("verify", _should_retry, {"generate": "generate", "done": END})

    return builder.compile(checkpointer=False)  # batch pipeline, no persistence


def run_pipeline(db_path: str, llm: Any, records: list[dict], profile_id: str = "default") -> dict:
    """Run the full pipeline.

    Returns PublicState dict (no internal keys like _retry_count).
    """
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
