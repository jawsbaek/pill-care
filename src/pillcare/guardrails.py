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


def verify_nli_entailment(
    result: GuidanceResult, evidence_chunks: list[str]
) -> list[str]:
    """Layer 5: NLI entailment gate for T4:AI sections.

    Every AI-generated (T4) section's content is checked against the
    concatenated evidence text. If entailment probability falls below
    ``ENTAILMENT_THRESHOLD`` (0.75), emits ``[CRITICAL]`` so the retry
    loop fires. T1 sections are already deterministically grounded by
    ``collect_info`` and are skipped.

    Imported lazily so modules that don't call ``post_verify(...,
    evidence_chunks=...)`` never trigger the multi-hundred-MB model
    load.
    """
    if not evidence_chunks:
        return []
    evidence_text = "\n".join(chunk for chunk in evidence_chunks if chunk)
    if not evidence_text.strip():
        return []

    from pillcare.nli_gate import passes_nli_gate

    errors: list[str] = []
    for guidance in result.drug_guidances:
        for name, section in guidance.sections.items():
            if section.source_tier != SourceTier.T4_AI:
                continue
            # Cap claim length to keep inference bounded and focus on
            # the core assertion of the section.
            claim = section.content[:300]
            if not passes_nli_gate(claim, evidence_text):
                errors.append(
                    f"[CRITICAL] NLI entailment 실패: {guidance.drug_name} - {name}"
                )
    return errors


def verify_intent(result: GuidanceResult) -> list[str]:
    """Layer 6: embedding-similarity intent classifier.

    Defends against paraphrase-bypass of the banned-words regex filter
    by comparing each section's content against a pool of exemplar
    clinician-only intents (diagnosis / prescription / dose change /
    treatment recommendation).  Imported lazily.
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
    evidence_chunks: list[str] | None = None,
) -> list[str]:
    """Run all post-verification guardrail checks and return collected errors.

    6-layer guardrail:
        L1 금칙어 regex       — applied upstream in ``generate``
        L2 출처 계층 강제     — ``verify_source_tags`` / ``verify_t4_ratio``
        L3 DUR 커버리지       — ``verify_dur_coverage``
        L4 필수 종결 문구     — ``verify_closing_phrase`` (+ min sections)
        L5 NLI entailment    — ``verify_nli_entailment`` (if evidence given)
        L6 의도 분류기        — ``verify_intent``

    ``evidence_chunks`` is optional to preserve backward compatibility
    with existing tests / call sites; when omitted, L5 is skipped.
    """
    errors = []
    missing = verify_dur_coverage(result, dur_alerts)
    for m in missing:
        errors.append(
            f"[ERROR] DUR 누락: {m['drug_name_1']} × {m['drug_name_2']} (deterministic 구성 — 재시도 불가, 코드 버그 확인 필요)"
        )
    errors.extend(verify_source_tags(result))
    errors.extend(verify_min_sections(result))
    errors.extend(verify_t4_ratio(result))
    errors.extend(verify_closing_phrase(result))
    if evidence_chunks:
        errors.extend(verify_nli_entailment(result, evidence_chunks))
    errors.extend(verify_intent(result))
    return errors
