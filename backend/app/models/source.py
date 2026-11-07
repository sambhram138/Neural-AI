import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class ResearchSource(Base):
    __tablename__ = "research_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=False)
    source_type = Column(String(50), nullable=False)  # "website", "book_pdf", "youtube"
    title = Column(String(255), nullable=False)
    author_publisher = Column(String(255), nullable=True)
    url_or_identifier = Column(String(500), nullable=True)
    published_date = Column(String(100), nullable=True)
    retrieved_at = Column(DateTime, default=utc_now)
    relevance_score = Column(Float, default=1.0)
    source_metadata = Column(JSON, nullable=True)  # channel name, page count, raw info, etc.
    status = Column(String(50), default="active")  # "active", "failed", "skipped"

    # Relationships
    lesson = relationship("Lesson", back_populates="sources")
    chunks = relationship("ResearchChunk", back_populates="source", cascade="all, delete-orphan")


class ResearchChunk(Base):
    __tablename__ = "research_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("research_sources.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_heading = Column(String(255), nullable=True)
    embedding_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    source = relationship("ResearchSource", back_populates="chunks")
