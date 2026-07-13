from pydantic import BaseModel, Field


class RTIComponent(BaseModel):
    key: str
    label: str
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    weighted_score: float = Field(ge=0, le=100)
    explanation: str
    recommendations: list[str] = Field(default_factory=list)


class ResearchTrustIndexRead(BaseModel):
    project_id: int
    overall_score: float = Field(ge=0, le=100)
    confidence_level: str
    evidence_count: int
    supporting_count: int
    contradicting_count: int
    approved_count: int
    conflict_count: int
    components: list[RTIComponent]
    strengths: list[str]
    limitations: list[str]
    recommended_actions: list[str]
    methodology_version: str = "rti-v1"
