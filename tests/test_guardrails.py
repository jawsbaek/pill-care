"""Tests for enhanced post-verification guardrails."""

from pillcare.guardrails import (
    drop_unsupported_claims,
    verify_dur_coverage,
    filter_banned_words,
    verify_source_tags,
    verify_t4_ratio,
    verify_closing_phrase,
    verify_min_sections,
)
from pillcare.prompts import BANNED_WORDS
from pillcare.schemas import (
    ClaimTag,
    DrugGuidance,
    GuidanceResult,
    GuidanceSection,
    DurWarning,
    SourceTier,
)


def test_verify_dur_coverage_detects_missing():
    dur_alerts = [
        {"drug_name_1": "펠루비정", "drug_name_2": "록스펜정", "reason": "NSAIDs"},
        {"drug_name_1": "이부프로펜", "drug_name_2": "와파린", "reason": "출혈"},
    ]
    result = GuidanceResult(
        drug_guidances=[],
        dur_warnings=[
            DurWarning(
                drug_1="펠루비정",
                drug_2="록스펜정",
                reason="NSAIDs",
                cross_clinic=False,
            )
        ],
        summary=[],
        warning_labels=[],
    )
    missing = verify_dur_coverage(result, dur_alerts)
    assert len(missing) == 1
    assert "와파린" in missing[0]["drug_name_2"]


def test_verify_dur_coverage_all_present():
    dur_alerts = [
        {"drug_name_1": "펠루비정", "drug_name_2": "록스펜정", "reason": "NSAIDs"}
    ]
    result = GuidanceResult(
        drug_guidances=[],
        dur_warnings=[
            DurWarning(
                drug_1="펠루비정",
                drug_2="록스펜정",
                reason="NSAIDs",
                cross_clinic=False,
            )
        ],
        summary=[],
        warning_labels=[],
    )
    assert verify_dur_coverage(result, dur_alerts) == []


def test_filter_banned_words_removes():
    text = "이 약을 진단합니다. 복약지도를 시행합니다."
    cleaned = filter_banned_words(text)
    for word in BANNED_WORDS:
        assert word not in cleaned


def test_filter_banned_words_preserves_clean():
    text = "이 약은 감기에 사용합니다. 의사 또는 약사와 상담하십시오."
    assert filter_banned_words(text) == text


def test_verify_source_tags_detects_all_t4():
    """verify_source_tags flags when all sections are T4."""
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(
                drug_name="A",
                sections={
                    "명칭": GuidanceSection(
                        title="명칭",
                        content="리도펜연질캡슐입니다.",
                        source_tier=SourceTier.T4_AI,
                    ),
                    "효능효과": GuidanceSection(
                        title="효능효과",
                        content="감기에 사용합니다.",
                        source_tier=SourceTier.T4_AI,
                    ),
                },
            )
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    errors = verify_source_tags(result)
    assert len(errors) >= 1


def test_verify_source_tags_passes_with_t1():
    """verify_source_tags passes when at least one section has T1 source."""
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(
                drug_name="A",
                sections={
                    "명칭": GuidanceSection(
                        title="명칭",
                        content="리도펜연질캡슐",
                        source_tier=SourceTier.T1_PERMIT,
                    ),
                    "투여의의": GuidanceSection(
                        title="투여의의",
                        content="소염진통제입니다.",
                        source_tier=SourceTier.T4_AI,
                    ),
                },
            )
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    assert verify_source_tags(result) == []


def test_verify_t4_ratio_fails():
    sections = {}
    for i, name in enumerate(
        [
            "명칭",
            "성상",
            "효능효과",
            "투여의의",
            "용법용량",
            "저장방법",
            "주의사항",
            "상호작용",
            "투여종료후",
            "기타",
        ]
    ):
        tier = SourceTier.T4_AI if i >= 5 else SourceTier.T1_PERMIT
        sections[name] = GuidanceSection(
            title=name, content=f"[{tier.value}] ...", source_tier=tier
        )
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections=sections)],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    errors = verify_t4_ratio(result, max_ratio=0.3)
    assert len(errors) >= 1


def test_verify_min_sections_flags_insufficient():
    """verify_min_sections flags drugs with too few sections."""
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(
                drug_name="A",
                sections={
                    "명칭": GuidanceSection(
                        title="명칭", content="테스트", source_tier=SourceTier.T1_PERMIT
                    ),
                },
            )
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    errors = verify_min_sections(result)
    assert len(errors) == 1
    assert "[CRITICAL]" in errors[0]


def test_verify_min_sections_passes():
    """verify_min_sections passes with sufficient sections."""
    sections = {}
    for name in ["명칭", "성상", "효능효과", "투여의의", "용법용량"]:
        sections[name] = GuidanceSection(
            title=name, content="내용", source_tier=SourceTier.T1_PERMIT
        )
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections=sections)],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    assert verify_min_sections(result) == []


def test_drop_unsupported_claims_removes_missing():
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(
                drug_name="아스피린",
                sections={
                    "효능": GuidanceSection(
                        title="효능",
                        content="진통",
                        source_tier=SourceTier.T1_PERMIT,
                        claim_tag=ClaimTag.SUPPORTED,
                    ),
                    "주의": GuidanceSection(
                        title="주의",
                        content="추측",
                        source_tier=SourceTier.T4_AI,
                        claim_tag=ClaimTag.MISSING,
                    ),
                },
            )
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    cleaned = drop_unsupported_claims(result)
    assert "효능" in cleaned.drug_guidances[0].sections
    assert "주의" not in cleaned.drug_guidances[0].sections


def test_drop_unsupported_claims_removes_contradictory():
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(
                drug_name="아스피린",
                sections={
                    "효능": GuidanceSection(
                        title="효능",
                        content="유효",
                        source_tier=SourceTier.T1_PERMIT,
                        claim_tag=ClaimTag.CONTRADICTORY,
                    ),
                },
            )
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    cleaned = drop_unsupported_claims(result)
    assert "효능" not in cleaned.drug_guidances[0].sections


def test_drop_unsupported_claims_preserves_all_supported():
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(
                drug_name="아스피린",
                sections={
                    "효능": GuidanceSection(
                        title="효능",
                        content="a",
                        source_tier=SourceTier.T1_PERMIT,
                        claim_tag=ClaimTag.SUPPORTED,
                    ),
                    "주의": GuidanceSection(
                        title="주의",
                        content="b",
                        source_tier=SourceTier.T1_PERMIT,
                        claim_tag=ClaimTag.SUPPORTED,
                    ),
                },
            )
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    cleaned = drop_unsupported_claims(result)
    assert len(cleaned.drug_guidances[0].sections) == 2


def test_verify_closing_phrase_detects_missing():
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(
                drug_name="A",
                sections={
                    "주의사항": GuidanceSection(
                        title="주의사항",
                        content="[T1:허가정보] 위장출혈.",
                        source_tier=SourceTier.T1_PERMIT,
                    ),
                },
            )
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    errors = verify_closing_phrase(result)
    assert len(errors) >= 1
