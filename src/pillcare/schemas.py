"""Pydantic models for pipeline state and structured output."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SourceTier(str, Enum):
    T1_PERMIT = "T1:허가정보"
    T1_EASY = "T1:e약은요"
    T1_DUR = "T1:DUR"
    T4_AI = "T4:AI"


class ClaimTag(str, Enum):
    """MedConf-style evidence tier for LLM-generated claims.

    Per Ren et al. 2026 (arXiv:2601.15645), each generated section is
    self-tagged as Supported/Missing/Contradictory relative to authoritative
    source data. Missing/Contradictory are dropped before downstream verify.
    """

    SUPPORTED = "supported"
    MISSING = "missing"
    CONTRADICTORY = "contradictory"


class MatchedDrug(BaseModel):
    item_seq: str
    drug_name: str
    item_name: str
    department: str
    ingr_codes: list[str] = Field(default_factory=list)
    edi_code: str | None = None
    match_score: int = 0


class DurAlertModel(BaseModel):
    drug_name_1: str
    department_1: str
    ingr_code_1: str
    ingr_name_1: str
    drug_name_2: str
    department_2: str
    ingr_code_2: str
    ingr_name_2: str
    reason: str
    cross_clinic: bool


class GuidanceSection(BaseModel):
    title: str
    content: str
    source_tier: SourceTier
    claim_tag: ClaimTag = ClaimTag.SUPPORTED  # internal default for non-LLM paths
    # NOTE: default differs from DrugSectionOutput (MISSING) intentionally.
    # - DrugSectionOutput is LLM structured output: untagged should drop.
    # - GuidanceSection is internal model: legacy T1-only paths default SUPPORTED.


class DrugGuidance(BaseModel):
    drug_name: str
    sections: dict[str, GuidanceSection] = Field(default_factory=dict)


SECTION_NAMES = Literal[
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

SOURCE_TIER_LABELS = Literal["T1:허가정보", "T1:e약은요", "T1:DUR", "T4:AI"]

_TIER_LABEL_MAP: dict[str, SourceTier] = {
    "T1:허가정보": SourceTier.T1_PERMIT,
    "T1:e약은요": SourceTier.T1_EASY,
    "T1:DUR": SourceTier.T1_DUR,
    "T4:AI": SourceTier.T4_AI,
}


class DrugSectionOutput(BaseModel):
    """LLM structured output schema for a single drug section."""

    section_name: SECTION_NAMES
    content: str
    source_tier: SOURCE_TIER_LABELS
    claim_tag: ClaimTag = ClaimTag.MISSING  # fail-safe: untagged LLM output → drop
    # NOTE: default differs from GuidanceSection (SUPPORTED) intentionally.
    # - DrugSectionOutput is LLM structured output: untagged should drop.
    # - GuidanceSection is internal model: legacy T1-only paths default SUPPORTED.


class DrugGuidanceOutput(BaseModel):
    """LLM structured output schema for complete drug guidance."""

    drug_name: str
    sections: list[DrugSectionOutput]

    def to_drug_guidance(self) -> DrugGuidance:
        """Convert LLM structured output to internal DrugGuidance model."""
        sections_dict: dict[str, GuidanceSection] = {}
        for s in self.sections:
            tier = _TIER_LABEL_MAP[s.source_tier]
            if s.section_name in sections_dict:
                existing = sections_dict[s.section_name]
                merged_content = existing.content + "\n" + s.content
                keep_tier = (
                    existing.source_tier
                    if existing.source_tier != SourceTier.T4_AI
                    else tier
                )
                # Downgrade claim_tag if merging with non-SUPPORTED: Missing
                # and Contradictory dominate so unsupported claims still get
                # dropped downstream.
                keep_claim_tag = (
                    existing.claim_tag
                    if existing.claim_tag != ClaimTag.SUPPORTED
                    else s.claim_tag
                )
                sections_dict[s.section_name] = GuidanceSection(
                    title=s.section_name,
                    content=merged_content,
                    source_tier=keep_tier,
                    claim_tag=keep_claim_tag,
                )
            else:
                sections_dict[s.section_name] = GuidanceSection(
                    title=s.section_name,
                    content=s.content,
                    source_tier=tier,
                    claim_tag=s.claim_tag,
                )
        return DrugGuidance(drug_name=self.drug_name, sections=sections_dict)


class DurWarning(BaseModel):
    drug_1: str
    drug_2: str
    reason: str
    cross_clinic: bool


class GuidanceResult(BaseModel):
    drug_guidances: list[DrugGuidance] = Field(default_factory=list)
    dur_warnings: list[DurWarning] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
    warning_labels: list[str] = Field(default_factory=list)

    def t4_ratio(self) -> float:
        total = 0
        t4_count = 0
        for dg in self.drug_guidances:
            for section in dg.sections.values():
                total += 1
                if section.source_tier == SourceTier.T4_AI:
                    t4_count += 1
        return t4_count / total if total > 0 else 0.0


class CriticVerdict(str, Enum):
    """Critic node verdict for AMIE-style LLM-as-judge self-critique."""

    PASS = "pass"
    RETRY = "retry"
    ESCALATE = "escalate"


class CriticOutput(BaseModel):
    """Structured output from critic (judge) LLM.

    Populated by `critic_node` when sampled. Consumed by verify's
    `_should_retry` to gate the CRITICAL retry loop alongside deterministic
    rule-check errors.
    """

    verdict: CriticVerdict
    critical_errors: list[str] = Field(default_factory=list)
    minor_issues: list[str] = Field(default_factory=list)
    dropped_claims: list[str] = Field(default_factory=list)
