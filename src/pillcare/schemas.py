"""Pydantic models for pipeline state and structured output."""

from enum import Enum

from pydantic import BaseModel, Field


class SourceTier(str, Enum):
    T1_PERMIT = "T1:허가정보"
    T1_EASY = "T1:e약은요"
    T1_DUR = "T1:DUR"
    T4_AI = "T4:AI"


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


class DrugGuidance(BaseModel):
    drug_name: str
    sections: dict[str, GuidanceSection] = Field(default_factory=dict)


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


# Note: LangGraph uses GraphState (TypedDict) in pipeline.py as runtime container.
# This is the serializable subset (no _llm, no _retry_count).
class PipelineState(BaseModel):
    profile_id: str
    raw_records: list[dict] = Field(default_factory=list)
    matched_drugs: list[MatchedDrug] = Field(default_factory=list)
    dur_alerts: list[DurAlertModel] = Field(default_factory=list)
    drug_infos: list[dict] = Field(default_factory=list)
    guidance_result: GuidanceResult | None = None
    errors: list[str] = Field(default_factory=list)
    db_path: str = ""
