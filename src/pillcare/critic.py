"""LLM-as-judge critic node for AMIE-style self-critique.

This module wraps a judge LLM that independently evaluates a `generate` node
output against:

- DUR coverage (all deterministic DUR alerts reflected in response)
- Citation completeness (every claim has T1/T4 source tag)
- Banned-word regression (forbidden expressions not reintroduced)
- Evidence tier correctness (Missing/Contradictory claims flagged for drop)

Samples 10% of responses to control cost.
"""

import json
import random
from typing import Any

from pillcare.schemas import CriticOutput, CriticVerdict

CRITIC_SAMPLE_RATE = 0.10


def should_sample_critic() -> bool:
    """Return True for ~10% of calls so we only invoke the judge LLM on a sample."""
    return random.random() < CRITIC_SAMPLE_RATE


def critic_node(state: dict, llm: Any) -> dict:
    """LangGraph node: run critic on sampled subset of responses.

    When the call is not sampled, returns a PASS verdict with no errors
    without invoking the LLM. When sampled, uses `with_structured_output`
    to bind the `CriticOutput` schema and invoke the judge LLM.

    Fails open: any exception from the judge LLM (network error, rate limit,
    JSON schema failure) is swallowed and a PASS verdict is returned with a
    `critic unavailable: {ErrorType}` minor_issue. Critic is an optional
    safety net; post_verify is authoritative on CRITICAL rules.
    """
    if not should_sample_critic():
        return {"critic_output": CriticOutput(verdict=CriticVerdict.PASS).model_dump()}

    prompt = _build_critic_prompt(state)
    try:
        structured = llm.with_structured_output(CriticOutput, method="json_schema")
        output: CriticOutput = structured.invoke(prompt)
    except Exception as e:  # noqa: BLE001 — fail-open on any LLM error
        output = CriticOutput(
            verdict=CriticVerdict.PASS,
            minor_issues=[f"critic unavailable: {type(e).__name__}"],
        )
    return {"critic_output": output.model_dump()}


def _build_critic_prompt(state: dict) -> str:
    result = state.get("guidance_result", {}) or {}
    dur_alerts = state.get("dur_alerts", []) or []
    return (
        "당신은 복약 정보 안내 응답의 독립 검증자입니다.\n"
        "다음 기준으로 응답을 평가하세요:\n"
        "\n"
        f"1. DUR 커버리지: 제공된 DUR 경고({len(dur_alerts)}건)가 모두 응답에 반영되었는가?\n"
        "2. 인용 완전성: 모든 claim에 T1(공공) 또는 T4(AI) 출처 태그가 있는가?\n"
        "3. 금지 표현: '진단', '처방', '복약지도' 등 금지 어휘가 없는가?\n"
        "4. Missing/Contradictory 태그: 근거가 없거나 모순되는 claim은 drop 목록에 포함하라.\n"
        "   (참고: ClaimTag 명시 tagging은 A5에서 generate 출력에 추가됨. A4 단계에서는\n"
        "    judge가 근거 여부를 독자적으로 판단한다.)\n"
        "\n"
        "CRITICAL 오류(DUR 누락·금지 표현·근거 없는 의학 판단)가 있으면 verdict=retry.\n"
        "사소한 문제(표현 부자연 등)는 minor_issues에 기록하고 verdict=pass.\n"
        "\n"
        "입력 DUR 경고:\n"
        f"{json.dumps(dur_alerts, ensure_ascii=False, indent=2)}\n"
        "\n"
        "응답:\n"
        f"{json.dumps(result, ensure_ascii=False, indent=2)}\n"
    )
