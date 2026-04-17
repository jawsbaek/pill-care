"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from pillcare.schemas import (
    ClaimTag,
    DurAlertModel,
    DurRuleType,
    DurWarning,
    MatchedDrug,
    DrugGuidance,
    DrugGuidanceOutput,
    DrugSectionOutput,
    GuidanceSection,
    GuidanceResult,
    SourceTier,
)


def test_dur_rule_type_covers_eight_hira_rules():
    expected = {
        "combined",
        "age",
        "pregnancy",
        "dose",
        "duplicate",
        "elderly",
        "specific_age",
        "pregnant_woman",
    }
    assert {r.value for r in DurRuleType} == expected


def test_dur_alert_model_rule_type_defaults_to_combined():
    m = DurAlertModel(
        drug_name_1="A",
        department_1="내과",
        ingr_code_1="X1",
        ingr_name_1="성분A",
        drug_name_2="B",
        department_2="내과",
        ingr_code_2="X2",
        ingr_name_2="성분B",
        reason="테스트",
        cross_clinic=False,
    )
    assert m.rule_type == DurRuleType.COMBINED


def test_dur_alert_model_allows_missing_pair_for_single_drug_rule():
    m = DurAlertModel(
        drug_name_1="A",
        department_1="내과",
        ingr_code_1="X1",
        ingr_name_1="성분A",
        reason="영유아 금기",
        rule_type=DurRuleType.AGE,
    )
    assert m.drug_name_2 is None
    assert m.rule_type == DurRuleType.AGE


def test_dur_warning_accepts_single_drug_rule():
    w = DurWarning(drug_1="A", reason="임부금기", rule_type=DurRuleType.PREGNANCY)
    assert w.drug_2 is None
    assert w.rule_type == DurRuleType.PREGNANCY


def test_claim_tag_values():
    assert ClaimTag.SUPPORTED.value == "supported"
    assert ClaimTag.MISSING.value == "missing"
    assert ClaimTag.CONTRADICTORY.value == "contradictory"


def test_guidance_section_default_claim_tag_is_supported():
    section = GuidanceSection(
        title="효능", content="...", source_tier=SourceTier.T1_PERMIT
    )
    assert section.claim_tag == ClaimTag.SUPPORTED


def test_guidance_section_accepts_missing_tag():
    section = GuidanceSection(
        title="주의",
        content="추측...",
        source_tier=SourceTier.T4_AI,
        claim_tag=ClaimTag.MISSING,
    )
    assert section.claim_tag == ClaimTag.MISSING


def test_drug_section_output_default_claim_tag_is_missing():
    """Untagged LLM output must default to MISSING (fail-safe drop)."""
    s = DrugSectionOutput(
        section_name="명칭", content="test", source_tier="T1:허가정보"
    )
    assert s.claim_tag == ClaimTag.MISSING
    assert s.claim_tag.value == "missing"


def test_drug_section_output_carries_claim_tag_through_conversion():
    output = DrugGuidanceOutput(
        drug_name="테스트",
        sections=[
            DrugSectionOutput(
                section_name="명칭",
                content="t",
                source_tier="T1:허가정보",
                claim_tag=ClaimTag.SUPPORTED,
            ),
            DrugSectionOutput(
                section_name="투여의의",
                content="추측",
                source_tier="T4:AI",
                claim_tag=ClaimTag.MISSING,
            ),
        ],
    )
    guidance = output.to_drug_guidance()
    assert guidance.sections["명칭"].claim_tag == ClaimTag.SUPPORTED
    assert guidance.sections["투여의의"].claim_tag == ClaimTag.MISSING


def test_matched_drug_from_match_result():
    drug = MatchedDrug(
        item_seq="199701416",
        drug_name="펠루비정",
        item_name="펠루비정(페루비프로펜)",
        department="가정의학과",
        ingr_codes=["M040702"],
        edi_code="671803380",
        match_score=100,
    )
    assert drug.item_seq == "199701416"
    assert len(drug.ingr_codes) == 1


def test_guidance_section_requires_source_tier():
    section = GuidanceSection(
        title="효능효과",
        content="이 약은 통증에 사용합니다.",
        source_tier=SourceTier.T1_PERMIT,
    )
    assert section.source_tier == SourceTier.T1_PERMIT


def test_drug_guidance_has_10_sections():
    sections = {
        "명칭": GuidanceSection(
            title="명칭", content="...", source_tier=SourceTier.T1_PERMIT
        ),
        "성상": GuidanceSection(
            title="성상", content="...", source_tier=SourceTier.T1_PERMIT
        ),
        "효능효과": GuidanceSection(
            title="효능효과", content="...", source_tier=SourceTier.T1_EASY
        ),
        "투여의의": GuidanceSection(
            title="투여의의", content="...", source_tier=SourceTier.T4_AI
        ),
        "용법용량": GuidanceSection(
            title="용법용량", content="...", source_tier=SourceTier.T1_EASY
        ),
        "저장방법": GuidanceSection(
            title="저장방법", content="...", source_tier=SourceTier.T1_PERMIT
        ),
        "주의사항": GuidanceSection(
            title="주의사항", content="...", source_tier=SourceTier.T1_PERMIT
        ),
        "상호작용": GuidanceSection(
            title="상호작용", content="...", source_tier=SourceTier.T1_DUR
        ),
        "투여종료후": GuidanceSection(
            title="투여종료후", content="...", source_tier=SourceTier.T4_AI
        ),
        "기타": GuidanceSection(
            title="기타", content="...", source_tier=SourceTier.T4_AI
        ),
    }
    guidance = DrugGuidance(drug_name="펠루비정", sections=sections)
    assert len(guidance.sections) == 10


def test_guidance_result_t4_ratio():
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(
                drug_name="A",
                sections={
                    "명칭": GuidanceSection(
                        title="명칭", content="...", source_tier=SourceTier.T1_PERMIT
                    ),
                    "투여의의": GuidanceSection(
                        title="투여의의", content="...", source_tier=SourceTier.T4_AI
                    ),
                },
            ),
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    assert result.t4_ratio() == 0.5


def test_drug_guidance_output_to_drug_guidance():
    output = DrugGuidanceOutput(
        drug_name="리도펜연질캡슐",
        sections=[
            DrugSectionOutput(
                section_name="명칭",
                content="리도펜연질캡슐 (이부프로펜 200mg)",
                source_tier="T1:허가정보",
            ),
            DrugSectionOutput(
                section_name="효능효과",
                content="감기 발열 통증에 사용합니다.",
                source_tier="T1:e약은요",
            ),
            DrugSectionOutput(
                section_name="투여의의",
                content="NSAIDs 계열 소염진통제입니다.",
                source_tier="T4:AI",
            ),
        ],
    )
    guidance = output.to_drug_guidance()
    assert isinstance(guidance, DrugGuidance)
    assert guidance.drug_name == "리도펜연질캡슐"
    assert "명칭" in guidance.sections
    assert "효능효과" in guidance.sections
    assert "투여의의" in guidance.sections
    assert guidance.sections["명칭"].source_tier == SourceTier.T1_PERMIT
    assert guidance.sections["효능효과"].source_tier == SourceTier.T1_EASY
    assert guidance.sections["투여의의"].source_tier == SourceTier.T4_AI


def test_drug_guidance_output_invalid_section_name():
    with pytest.raises(ValidationError):
        DrugSectionOutput(
            section_name="존재하지않는섹션", content="test", source_tier="T1:허가정보"
        )


def test_drug_guidance_output_invalid_source_tier():
    with pytest.raises(ValidationError):
        DrugSectionOutput(
            section_name="명칭", content="test", source_tier="T9:없는소스"
        )


def test_drug_guidance_output_merges_duplicate_sections():
    """Duplicate section names are merged, keeping higher-trust tier."""
    output = DrugGuidanceOutput(
        drug_name="테스트약",
        sections=[
            DrugSectionOutput(
                section_name="주의사항",
                content="첫 번째 주의.",
                source_tier="T1:허가정보",
                claim_tag=ClaimTag.SUPPORTED,
            ),
            DrugSectionOutput(
                section_name="주의사항",
                content="두 번째 주의.",
                source_tier="T4:AI",
                claim_tag=ClaimTag.SUPPORTED,
            ),
        ],
    )
    guidance = output.to_drug_guidance()
    assert "주의사항" in guidance.sections
    assert "첫 번째 주의." in guidance.sections["주의사항"].content
    assert "두 번째 주의." in guidance.sections["주의사항"].content
    # T1 should be preserved over T4
    assert guidance.sections["주의사항"].source_tier == SourceTier.T1_PERMIT


@pytest.mark.parametrize(
    "first,second,expected",
    [
        (ClaimTag.SUPPORTED, ClaimTag.MISSING, ClaimTag.MISSING),
        (ClaimTag.SUPPORTED, ClaimTag.CONTRADICTORY, ClaimTag.CONTRADICTORY),
        (ClaimTag.MISSING, ClaimTag.CONTRADICTORY, ClaimTag.MISSING),
        (ClaimTag.CONTRADICTORY, ClaimTag.MISSING, ClaimTag.CONTRADICTORY),
        (ClaimTag.MISSING, ClaimTag.MISSING, ClaimTag.MISSING),
    ],
    ids=["supp+miss", "supp+contra", "miss+contra", "contra+miss", "miss+miss"],
)
def test_to_drug_guidance_claim_tag_merge_rule(first, second, expected):
    """Merge rule: existing non-SUPPORTED dominates; first non-SUPPORTED wins on ties."""
    output = DrugGuidanceOutput(
        drug_name="테스트",
        sections=[
            DrugSectionOutput(
                section_name="효능효과",
                content="a",
                source_tier="T1:허가정보",
                claim_tag=first,
            ),
            DrugSectionOutput(
                section_name="효능효과",  # duplicate name → triggers merge
                content="b",
                source_tier="T1:허가정보",
                claim_tag=second,
            ),
        ],
    )
    guidance = output.to_drug_guidance()
    assert guidance.sections["효능효과"].claim_tag == expected


def test_drug_guidance_template_formats_without_brace_errors():
    """Template must accept evidence_tier_instruction without KeyError."""
    from pillcare.prompts import DRUG_GUIDANCE_TEMPLATE, EVIDENCE_TIER_INSTRUCTION

    rendered = DRUG_GUIDANCE_TEMPLATE.format(
        item_name="테스트약",
        main_item_ingr="이부프로펜",
        main_ingr_eng="Ibuprofen",
        entp_name="테스트제약",
        atc_code="M01AE01",
        etc_otc_code="일반의약품",
        chart="정제",
        total_content="200mg",
        storage_method="실온",
        valid_term="36개월",
        ee_text="효능",
        ud_text="용법",
        nb_sections="주의",
        easy_text="안내",
        dur_alerts="[]",
        evidence_tier_instruction=EVIDENCE_TIER_INSTRUCTION,
    )
    assert "supported" in rendered.lower()
    assert "missing" in rendered.lower()
