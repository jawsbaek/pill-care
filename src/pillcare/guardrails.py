"""Enhanced post-verification guardrails."""

import re
from pillcare.prompts import BANNED_WORDS
from pillcare.schemas import GuidanceResult, SourceTier

_WARNING_SECTIONS = {"주의사항", "상호작용", "투여종료후"}
_CLOSING_PHRASE = "의사 또는 약사와 상담하십시오"
_SOURCE_TAG_RE = re.compile(r"\[T[14]:(허가정보|e약은요|DUR|AI)\]")


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
    """Check that every section's content contains a source tier tag."""
    errors = []
    for dg in result.drug_guidances:
        for name, section in dg.sections.items():
            if not _SOURCE_TAG_RE.search(section.content):
                errors.append(f"출처 태그 누락: {dg.drug_name} / {name}")
    return errors


def verify_t4_ratio(result: GuidanceResult, max_ratio: float = 0.3) -> list[str]:
    """Verify that the ratio of T4 (AI-generated) sections is within limits."""
    ratio = result.t4_ratio()
    if ratio > max_ratio:
        return [f"[CRITICAL] T4 비율 초과: {ratio:.1%} (한도: {max_ratio:.0%})"]
    return []


def verify_closing_phrase(result: GuidanceResult) -> list[str]:
    """Ensure warning sections end with the mandatory closing phrase."""
    errors = []
    for dg in result.drug_guidances:
        for name, section in dg.sections.items():
            if name in _WARNING_SECTIONS and _CLOSING_PHRASE not in section.content:
                errors.append(f"필수 종결 문구 누락: {dg.drug_name} / {name}")
    return errors


def post_verify(result: GuidanceResult, dur_alerts: list[dict]) -> list[str]:
    """Run all 5 post-verification guardrail checks and return collected errors."""
    errors = []
    missing = verify_dur_coverage(result, dur_alerts)
    for m in missing:
        errors.append(f"[CRITICAL] DUR 누락: {m['drug_name_1']} × {m['drug_name_2']}")
    errors.extend(verify_source_tags(result))
    errors.extend(verify_t4_ratio(result))
    errors.extend(verify_closing_phrase(result))
    return errors
