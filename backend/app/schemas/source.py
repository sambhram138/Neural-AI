from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ResearchChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    chunk_text: str
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    created_at: datetime

class ResearchSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lesson_id: str
    source_type: str
    title: str
    author_publisher: Optional[str] = None
    url_or_identifier: Optional[str] = None
    published_date: Optional[str] = None
    retrieved_at: datetime
    relevance_score: float
    source_metadata: Optional[Dict[str, Any]] = None
    status: str
    chunks: List[ResearchChunkResponse] = Field(default_factory=list)

class ResearchSourceListResponse(BaseModel):
    items: List[ResearchSourceResponse]
    total: int

class ResearchPackage(BaseModel):
    lesson_id: str
    lesson_title: str
    learning_objective: str
    sources: List[ResearchSourceResponse] = Field(default_factory=list)
    web_excerpts: List[Dict[str, Any]] = Field(default_factory=list)
    book_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    youtube_videos: List[Dict[str, Any]] = Field(default_factory=list)
    retrieval_notes: Optional[str] = None
    identified_gaps: List[str] = Field(default_factory=list)
