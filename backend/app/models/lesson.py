import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    learning_objective = Column(Text, nullable=False)
    audience = Column(String(100), default="General / Undergraduate")
    teaching_mode = Column(String(50), default="self-learning")  # "self-learning", "instructor-led", "hybrid"
    additional_instructions = Column(Text, nullable=True)
    status = Column(String(50), default="draft")  # draft, researching, generated, qc_completed, approved, failed
    current_version_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    versions = relationship("LessonVersion", back_populates="lesson", cascade="all, delete-orphan", order_by="LessonVersion.version_number")
    sources = relationship("ResearchSource", back_populates="lesson", cascade="all, delete-orphan")
    workflow_jobs = relationship("WorkflowJob", back_populates="lesson", cascade="all, delete-orphan")


class LessonVersion(Base):
    __tablename__ = "lesson_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    learning_objective = Column(Text, nullable=False)
    content_json = Column(JSON, nullable=False)  # Structured lesson schema
    total_duration_minutes = Column(Integer, default=45, nullable=False)
    created_by = Column(String(50), default="system")  # "system", "instructor"
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    lesson = relationship("Lesson", back_populates="versions")
    qc_reports = relationship("QCReport", back_populates="lesson_version", cascade="all, delete-orphan")
