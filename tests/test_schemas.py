"""Tests for Pydantic schemas."""

import pytest

from pillcare.schemas import (
    PipelineState,
    MatchedDrug,
    DurAlertModel,
    DrugGuidance,
    GuidanceSection,
    GuidanceResult,
    DurWarning,
    SourceTier,
)


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
        "명칭": GuidanceSection(title="명칭", content="...", source_tier=SourceTier.T1_PERMIT),
        "성상": GuidanceSection(title="성상", content="...", source_tier=SourceTier.T1_PERMIT),
        "효능효과": GuidanceSection(title="효능효과", content="...", source_tier=SourceTier.T1_EASY),
        "투여의의": GuidanceSection(title="투여의의", content="...", source_tier=SourceTier.T4_AI),
        "용법용량": GuidanceSection(title="용법용량", content="...", source_tier=SourceTier.T1_EASY),
        "저장방법": GuidanceSection(title="저장방법", content="...", source_tier=SourceTier.T1_PERMIT),
        "주의사항": GuidanceSection(title="주의사항", content="...", source_tier=SourceTier.T1_PERMIT),
        "상호작용": GuidanceSection(title="상호작용", content="...", source_tier=SourceTier.T1_DUR),
        "투여종료후": GuidanceSection(title="투여종료후", content="...", source_tier=SourceTier.T4_AI),
        "기타": GuidanceSection(title="기타", content="...", source_tier=SourceTier.T4_AI),
    }
    guidance = DrugGuidance(drug_name="펠루비정", sections=sections)
    assert len(guidance.sections) == 10


def test_pipeline_state_initial():
    state = PipelineState(profile_id="test-user")
    assert state.matched_drugs == []
    assert state.dur_alerts == []
    assert state.errors == []


def test_guidance_result_t4_ratio():
    result = GuidanceResult(
        drug_guidances=[
            DrugGuidance(drug_name="A", sections={
                "명칭": GuidanceSection(title="명칭", content="...", source_tier=SourceTier.T1_PERMIT),
                "투여의의": GuidanceSection(title="투여의의", content="...", source_tier=SourceTier.T4_AI),
            }),
        ],
        dur_warnings=[],
        summary=[],
        warning_labels=[],
    )
    assert result.t4_ratio() == 0.5
