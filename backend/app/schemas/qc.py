from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

SeverityLevel = Literal["critical", "high", "medium", "low"]
VerificationState = Literal["supported", "contradicted", "insufficient_evidence", "not_applicable"]
QCStatus = Literal["passed", "passed_with_warnings", "needs_revision", "pending", "failed"]

class QCIssue(BaseModel):
    issue_id: str
    category: str
    severity: SeverityLevel
    section_title: Optional[str] = None
    claim_text: Optional[str] = None
    evidence_considered: Optional[str] = None
    explanation: str
    recommendation: str
    source_ids: List[str] = Field(default_factory=list)
    verification_state: VerificationState = "not_applicable"
    accepted: Optional[bool] = None

class FactualQCReport(BaseModel):
    qc_type: Literal["factual_accuracy"] = "factual_accuracy"
    status: QCStatus
    overall_score: float = Field(..., ge=0.0, le=100.0)
    summary: str
    claims_verified_count: int
    strengths: List[str] = Field(default_factory=list)
    issues: List[QCIssue] = Field(default_factory=list)
    missing_facts_or_gaps: List[str] = Field(default_factory=list)
    source_reliability_assessment: str
    limitations: Optional[str] = None

class InstructionalQCReport(BaseModel):
    qc_type: Literal["instructional_quality"] = "instructional_quality"
    status: QCStatus
    overall_score: float = Field(..., ge=0.0, le=100.0)
    summary: str
    objective_alignment_assessment: str
    time_budget_assessment: str
    calculated_total_minutes: int
    strengths: List[str] = Field(default_factory=list)
    issues: List[QCIssue] = Field(default_factory=list)
    pedagogical_gaps: List[str] = Field(default_factory=list)
    actionable_recommendations: List[str] = Field(default_factory=list)

class QCReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lesson_version_id: str
    qc_type: str
    status: str
    overall_score: Optional[float] = None
    report: dict
    created_at: datetime

class CombinedQCResponse(BaseModel):
    lesson_version_id: str
    factual_qc: Optional[QCReportResponse] = None
    instructional_qc: Optional[QCReportResponse] = None
    all_issues: List[QCIssue] = Field(default_factory=list)
