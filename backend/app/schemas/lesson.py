from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

class LessonSection(BaseModel):
    title: str = Field(..., description="Title of this section")
    content: str = Field(..., description="Detailed explanatory text and concepts")
    duration_minutes: int = Field(..., ge=1, description="Estimated duration in minutes for this section")
    order: int = Field(..., ge=1, description="Sequential order in the lesson")
    key_points: List[str] = Field(default_factory=list, description="Key takeaways or summary bullet points")
    citations: List[str] = Field(default_factory=list, description="Source IDs referenced in this section")

class WorkedExample(BaseModel):
    title: str = Field(..., description="Example title")
    scenario: str = Field(..., description="Scenario or problem statement")
    step_by_step_solution: str = Field(..., description="Step by step demonstration")
    explanation: str = Field(..., description="Why this works and common pitfalls to avoid")

class PracticalApplication(BaseModel):
    domain: str = Field(..., description="Industry or engineering domain")
    use_case: str = Field(..., description="Real-world application scenario")
    best_practices: List[str] = Field(default_factory=list, description="Industry best practices")

class InteractiveActivity(BaseModel):
    title: str = Field(..., description="Title of the activity")
    instructions: str = Field(..., description="Clear instructions for the learner")
    duration_minutes: int = Field(default=5, ge=1, description="Allocated time for activity")
    deliverable: str = Field(..., description="Expected output or verification")

class KnowledgeCheckItem(BaseModel):
    question: str = Field(..., description="Assessment question")
    options: Optional[List[str]] = Field(default=None, description="Multiple choice options if applicable")
    correct_answer: str = Field(..., description="Correct answer")
    explanation: str = Field(..., description="Why this answer is correct and guidance")

class SupplementaryVideo(BaseModel):
    title: str
    url: str
    channel: Optional[str] = None
    duration: Optional[str] = None
    relevance_note: Optional[str] = None

class ReferenceLink(BaseModel):
    source_id: str
    title: str
    url_or_identifier: Optional[str] = None
    source_type: str = "website"  # "website", "book_pdf", "youtube"
    citation: Optional[str] = None

class LessonContent(BaseModel):
    title: str
    learning_objective: str
    target_audience: str = "General / Undergraduate"
    prerequisites: List[str] = Field(default_factory=list)
    introduction: str
    sections: List[LessonSection]
    worked_examples: List[WorkedExample] = Field(default_factory=list)
    practical_applications: List[PracticalApplication] = Field(default_factory=list)
    interactive_activity: InteractiveActivity
    knowledge_checks: List[KnowledgeCheckItem] = Field(default_factory=list)
    summary: str
    supplementary_videos: List[SupplementaryVideo] = Field(default_factory=list)
    references: List[ReferenceLink] = Field(default_factory=list)
    total_duration_minutes: int = 45

    @field_validator("total_duration_minutes")
    @classmethod
    def validate_duration(cls, v: int, info) -> int:
        if v != 45:
            raise ValueError(f"Total duration must be exactly 45 minutes, got {v} minutes.")
        return v

# API Request & Response Schemas
class LessonCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Title of the lesson")
    learning_objective: str = Field(..., min_length=10, max_length=1000, description="Specific learning objective")
    audience: Optional[str] = Field("General / Undergraduate", max_length=100)
    teaching_mode: Optional[str] = Field("self-learning", description="self-learning, instructor-led, or hybrid")
    additional_instructions: Optional[str] = Field(None, max_length=2000)

    @field_validator("title", "learning_objective")
    @classmethod
    def not_empty_or_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only.")
        return v.strip()

class LessonUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    learning_objective: Optional[str] = Field(None, min_length=10, max_length=1000)
    audience: Optional[str] = None
    teaching_mode: Optional[str] = None
    additional_instructions: Optional[str] = None
    status: Optional[str] = None

class LessonVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lesson_id: str
    version_number: int
    title: str
    learning_objective: str
    content: LessonContent
    total_duration_minutes: int
    created_by: str
    created_at: datetime

class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    learning_objective: str
    audience: str
    teaching_mode: str
    additional_instructions: Optional[str] = None
    status: str
    current_version_id: Optional[str] = None
    current_version: Optional[LessonVersionResponse] = None
    created_at: datetime
    updated_at: datetime

class LessonListResponse(BaseModel):
    items: List[LessonResponse]
    total: int
