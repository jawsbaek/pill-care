"""Enhanced post-verification guardrails."""

from pillcare.prompts import BANNED_WORDS
from pillcare.schemas import ClaimTag, GuidanceResult, SourceTier


def drop_unsupported_claims(result: GuidanceResult) -> GuidanceResult:
    """Remove Missing/Contradictory-tagged sections from all drug guidances.

    Implements MedConf (Ren et al. 2026, arXiv:2601.15645) 3-way evidence
    tier filtering: only SUPPORTED claims survive into downstream verify.
    Mutates `result` in place and returns it for fluent chaining.
    """
    for guidance in result.drug_guidances:
        guidance.sections = {
            name: sec
            for name, sec in guidance.sections.items()
            if sec.claim_tag == ClaimTag.SUPPORTED
        }
    return result


_WARNING_SECTIONS = {"주의사항", "상호작용", "투여종료후"}
_CLOSING_PHRASE = "의사 또는 약사와 상담하십시오"


def verify_dur_coverage(result: GuidanceResult, dur_alerts: list[dict]) -> list[dict]:
    """Structured matching: check dur_warnings contains all alert pairs."""
    warned_pairs = set()
    for w in result.dur_warnings:
        warned_pairs.add((w.drug_1, w.drug_2))
        warned_pairs.add((w.drug_2, w.drug_1))
    missing = []
    for alert in dur_alerts:
        if (alert["drug_name_1"], alert["drug_name_2"]) not in warned_pairs:
            missing.append(alert)
    return missing


def filter_banned_words(text: str) -> str:
    """Remove banned words from text and clean up extra whitespace."""
    result = text
    for word in BANNED_WORDS:
        result = result.replace(word, "")
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip()


def verify_source_tags(result: GuidanceResult) -> list[str]:
    """Check that each drug has at least one T1-sourced section."""
    errors = []
    for dg in result.drug_guidances:
        has_t1 = any(
            s.source_tier
            in (SourceTier.T1_PERMIT, SourceTier.T1_EASY, SourceTier.T1_DUR)
            for s in dg.sections.values()
        )
        if not has_t1:
            errors.append(
                f"[CRITICAL] T1 출처 없음: {dg.drug_name} (모든 섹션이 AI 생성)"
            )
    return errors


def verify_t4_ratio(result: GuidanceResult, max_ratio: float = 0.3) -> list[str]:
    """Verify that the ratio of T4 (AI-generated) sections is within limits."""
    ratio = result.t4_ratio()
    if ratio > max_ratio:
        return [f"[CRITICAL] T4 비율 초과: {ratio:.1%} (한도: {max_ratio:.0%})"]
    return []


_MIN_SECTIONS = 5


def verify_min_sections(result: GuidanceResult) -> list[str]:
    """Check that each drug has a minimum number of sections."""
    errors = []
    for dg in result.drug_guidances:
        if len(dg.sections) < _MIN_SECTIONS:
            errors.append(
                f"[CRITICAL] 섹션 수 부족: {dg.drug_name} ({len(dg.sections)}/{_MIN_SECTIONS} 미만)"
            )
    return errors


def verify_closing_phrase(result: GuidanceResult) -> list[str]:
    """Ensure warning sections end with the mandatory closing phrase."""
    errors = []
    for dg in result.drug_guidances:
        for name, section in dg.sections.items():
            if name in _WARNING_SECTIONS and _CLOSING_PHRASE not in section.content:
                errors.append(f"필수 종결 문구 누락: {dg.drug_name} / {name}")
    return errors


def verify_intent(result: GuidanceResult) -> list[str]:
    """Layer 5: embedding-similarity intent classifier.

    Defends against paraphrase-bypass of the banned-words regex filter
    by comparing each section's content against a pool of exemplar
    clinician-only intents (diagnosis / prescription / dose change /
    treatment recommendation).  Imported lazily; the classifier itself
    fails open (returns ``'allowed'``) when the KURE-v1 model cannot be
    loaded, so a missing model never blocks the pipeline.
    """
    from pillcare.intent_classifier import classify_intent

    errors: list[str] = []
    for guidance in result.drug_guidances:
        for name, section in guidance.sections.items():
            if classify_intent(section.content) == "forbidden":
                errors.append(
                    f"[CRITICAL] 금지 의도 감지: {guidance.drug_name} - {name}"
                )
    return errors


def post_verify(
    result: GuidanceResult,
    dur_alerts: list[dict],
) -> list[str]:
    """Run all post-verification guardrail checks and return collected errors.

    5-layer guardrail:
        L1 금칙어 regex       — applied upstream in ``generate``
        L2 출처 계층 강제     — ``verify_source_tags`` / ``verify_t4_ratio``
        L3 DUR 커버리지       — ``verify_dur_coverage`` ([CRITICAL] on miss)
        L4 필수 종결 문구     — ``verify_closing_phrase`` (+ min sections)
        L5 의도 분류기        — ``verify_intent``

    DUR coverage misses are emitted as ``[CRITICAL]`` so the
    ``_should_retry`` gate triggers regeneration even when the LLM drops
    a DUR-related section via ``drop_unsupported_claims`` upstream
    (P1-1 review fix).
    """
    errors = []
    missing = verify_dur_coverage(result, dur_alerts)
    for m in missing:
        errors.append(
            f"[CRITICAL] DUR 누락: {m['drug_name_1']} × {m['drug_name_2']} "
            "(재생성 필요 — LLM이 DUR 관련 섹션을 드롭했거나 생성 실패)"
        )
    errors.extend(verify_source_tags(result))
    errors.extend(verify_min_sections(result))
    errors.extend(verify_t4_ratio(result))
    errors.extend(verify_closing_phrase(result))
    errors.extend(verify_intent(result))
    return errors
