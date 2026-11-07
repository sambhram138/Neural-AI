import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class QCReport(Base):
    __tablename__ = "qc_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_version_id = Column(String(36), ForeignKey("lesson_versions.id"), nullable=False)
    qc_type = Column(String(50), nullable=False)  # "factual_accuracy" or "instructional_quality"
    status = Column(String(50), default="completed")  # "completed", "failed", "pending"
    overall_score = Column(Float, nullable=True)  # e.g., 0 - 100
    report_json = Column(JSON, nullable=False)  # Full structured audit report
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    lesson_version = relationship("LessonVersion", back_populates="qc_reports")
