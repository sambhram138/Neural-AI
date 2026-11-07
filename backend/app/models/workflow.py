import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class WorkflowJob(Base):
    __tablename__ = "workflow_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=False)
    stage = Column(String(50), nullable=False)  # "research", "generation", "qc_factual", "qc_instructional", "export"
    status = Column(String(50), default="pending")  # "pending", "in_progress", "completed", "failed"
    attempts = Column(Integer, default=1)
    error_message = Column(Text, nullable=True)
    payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    lesson = relationship("Lesson", back_populates="workflow_jobs")
