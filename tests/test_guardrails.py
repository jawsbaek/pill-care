"""Tests for enhanced post-verification guardrails."""
import pytest
from pillcare.guardrails import (
    verify_dur_coverage, filter_banned_words, verify_source_tags,
    verify_t4_ratio, verify_closing_phrase, post_verify,
)
from pillcare.prompts import BANNED_WORDS
from pillcare.schemas import (
    DrugGuidance, GuidanceResult, GuidanceSection, DurWarning, SourceTier,
)


def test_verify_dur_coverage_detects_missing():
    dur_alerts = [
        {"drug_name_1": "펠루비정", "drug_name_2": "록스펜정", "reason": "NSAIDs"},
        {"drug_name_1": "이부프로펜", "drug_name_2": "와파린", "reason": "출혈"},
    ]
    result = GuidanceResult(
        drug_guidances=[],
        dur_warnings=[DurWarning(drug_1="펠루비정", drug_2="록스펜정", reason="NSAIDs", cross_clinic=False)],
        summary=[], warning_labels=[],
    )
    missing = verify_dur_coverage(result, dur_alerts)
    assert len(missing) == 1
    assert "와파린" in missing[0]["drug_name_2"]


def test_verify_dur_coverage_all_present():
    dur_alerts = [{"drug_name_1": "펠루비정", "drug_name_2": "록스펜정", "reason": "NSAIDs"}]
    result = GuidanceResult(
        drug_guidances=[],
        dur_warnings=[DurWarning(drug_1="펠루비정", drug_2="록스펜정", reason="NSAIDs", cross_clinic=False)],
        summary=[], warning_labels=[],
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


def test_verify_source_tags_detects_untagged():
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections={
            "명칭": GuidanceSection(title="명칭", content="리도펜연질캡슐입니다.", source_tier=SourceTier.T1_PERMIT),
        })],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_source_tags(result)
    assert len(errors) >= 1


def test_verify_source_tags_passes():
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections={
            "명칭": GuidanceSection(title="명칭", content="[T1:허가정보] 리도펜연질캡슐", source_tier=SourceTier.T1_PERMIT),
        })],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    assert verify_source_tags(result) == []


def test_verify_t4_ratio_fails():
    sections = {}
    for i, name in enumerate(["명칭","성상","효능효과","투여의의","용법용량","저장방법","주의사항","상호작용","투여종료후","기타"]):
        tier = SourceTier.T4_AI if i >= 5 else SourceTier.T1_PERMIT
        sections[name] = GuidanceSection(title=name, content=f"[{tier.value}] ...", source_tier=tier)
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections=sections)],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_t4_ratio(result, max_ratio=0.3)
    assert len(errors) >= 1


def test_verify_closing_phrase_detects_missing():
    result = GuidanceResult(
        drug_guidances=[DrugGuidance(drug_name="A", sections={
            "주의사항": GuidanceSection(title="주의사항", content="[T1:허가정보] 위장출혈.", source_tier=SourceTier.T1_PERMIT),
        })],
        dur_warnings=[], summary=[], warning_labels=[],
    )
    errors = verify_closing_phrase(result)
    assert len(errors) >= 1
