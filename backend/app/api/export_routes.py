from typing import List, Optional
import uuid
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.lesson import Lesson, LessonVersion
from app.models.qc import QCReport
from app.schemas.lesson import LessonContent, LessonResponse, LessonVersionResponse
from app.agents.improvement_agent import improvement_agent
from app.services.export_service import export_service
from app.api.lesson_routes import _build_lesson_response, _build_version_response

router = APIRouter(prefix="/api/lessons", tags=["Review, Improvement & Export"])

class ContentEditRequest(BaseModel):
    content: LessonContent
    edit_summary: Optional[str] = Field("Manual instructor edits", description="Summary of changes")

class ApplyRecommendationsRequest(BaseModel):
    accepted_issue_ids: List[str] = Field(..., description="List of issue IDs to apply")
    instructor_notes: Optional[str] = None

class ExportResponse(BaseModel):
    lesson_id: str
    version_number: int
    export_format: str
    file_path: str
    download_url: str
    created_at: datetime

@router.patch("/{lesson_id}/content", response_model=LessonVersionResponse)
def save_instructor_edits(
    lesson_id: str,
    payload: ContentEditRequest,
    db: Session = Depends(get_db)
):
    """
    Saves instructor edits as a NEW LessonVersion.
    Preserves prior AI generations and manual edit history.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson '{lesson_id}' not found")

    # Get latest version number
    latest_ver = (
        db.query(LessonVersion)
        .filter(LessonVersion.lesson_id == lesson_id)
        .order_by(LessonVersion.version_number.desc())
        .first()
    )
    next_ver_num = (latest_ver.version_number + 1) if latest_ver else 1

    new_version = LessonVersion(
        id=str(uuid.uuid4()),
        lesson_id=lesson.id,
        version_number=next_ver_num,
        title=payload.content.title,
        learning_objective=payload.content.learning_objective,
        content_json=payload.content.model_dump(),
        total_duration_minutes=payload.content.total_duration_minutes,
        created_by="instructor",
    )
    db.add(new_version)
    db.flush()

    lesson.current_version_id = new_version.id
    lesson.status = "instructor_review"
    lesson.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(new_version)

    return _build_version_response(new_version)

@router.post("/{lesson_id}/recommendations/apply", response_model=LessonVersionResponse)
def apply_qc_recommendations(
    lesson_id: str,
    payload: ApplyRecommendationsRequest,
    db: Session = Depends(get_db)
):
    """
    Selectively applies accepted QC recommendations to the active lesson version.
    Saves the revised result as a NEW version without disturbing unrelated manual edits.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson or not lesson.current_version_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active lesson version to apply recommendations to.")

    current_ver = db.query(LessonVersion).filter(LessonVersion.id == lesson.current_version_id).first()
    current_content = LessonContent.model_validate(current_ver.content_json)

    # Collect all issues from existing QC reports
    qc_reports = db.query(QCReport).filter(QCReport.lesson_version_id == current_ver.id).all()
    all_issues = []
    for r in qc_reports:
        all_issues.extend(r.report_json.get("issues", []))

    # Apply through improvement agent
    improved_content = improvement_agent.apply_recommendations(
        current_content=current_content,
        accepted_issue_ids=payload.accepted_issue_ids,
        all_qc_issues=all_issues,
        instructor_guidance=payload.instructor_notes
    )

    # Save as new version
    latest_ver = (
        db.query(LessonVersion)
        .filter(LessonVersion.lesson_id == lesson_id)
        .order_by(LessonVersion.version_number.desc())
        .first()
    )
    next_ver_num = (latest_ver.version_number + 1) if latest_ver else 1

    new_version = LessonVersion(
        id=str(uuid.uuid4()),
        lesson_id=lesson.id,
        version_number=next_ver_num,
        title=improved_content.title,
        learning_objective=improved_content.learning_objective,
        content_json=improved_content.model_dump(),
        total_duration_minutes=improved_content.total_duration_minutes,
        created_by="system (applied recommendations)",
    )
    db.add(new_version)
    db.flush()

    lesson.current_version_id = new_version.id
    lesson.status = "review_updated"
    lesson.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(new_version)

    return _build_version_response(new_version)

@router.get("/{lesson_id}/preview")
def get_lesson_preview(lesson_id: str, db: Session = Depends(get_db)):
    """
    Returns full finalized preview data: active lesson content, references,
    videos, and both QC audit reports.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson or not lesson.current_version_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No lesson version found to preview.")

    current_ver = db.query(LessonVersion).filter(LessonVersion.id == lesson.current_version_id).first()
    qc_reports = db.query(QCReport).filter(QCReport.lesson_version_id == current_ver.id).all()

    factual = next((r.report_json for r in qc_reports if r.qc_type == "factual_accuracy"), None)
    instructional = next((r.report_json for r in qc_reports if r.qc_type == "instructional_quality"), None)

    return {
        "lesson_id": lesson.id,
        "version_number": current_ver.version_number,
        "status": lesson.status,
        "content": current_ver.content_json,
        "factual_qc_report": factual,
        "instructional_qc_report": instructional,
    }

@router.post("/{lesson_id}/export", response_model=ExportResponse)
def export_lesson(
    lesson_id: str,
    export_format: str = "markdown",
    db: Session = Depends(get_db)
):
    """
    Exports the finalized approved lesson, complete references, and both QC reports.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson or not lesson.current_version_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No lesson version found to export.")

    current_ver = db.query(LessonVersion).filter(LessonVersion.id == lesson.current_version_id).first()
    content = LessonContent.model_validate(current_ver.content_json)

    qc_reports = db.query(QCReport).filter(QCReport.lesson_version_id == current_ver.id).all()
    factual = next((r.report_json for r in qc_reports if r.qc_type == "factual_accuracy"), None)
    instructional = next((r.report_json for r in qc_reports if r.qc_type == "instructional_quality"), None)

    file_path = export_service.export_lesson_markdown(
        lesson_id=lesson.id,
        version_number=current_ver.version_number,
        content=content,
        factual_qc_rep=factual,
        instructional_qc_rep=instructional
    )

    lesson.status = "approved"
    lesson.updated_at = datetime.now(timezone.utc)
    db.commit()

    return ExportResponse(
        lesson_id=lesson.id,
        version_number=current_ver.version_number,
        export_format=export_format,
        file_path=file_path,
        download_url=f"/api/lessons/{lesson.id}/export/download",
        created_at=datetime.now(timezone.utc),
    )

@router.get("/{lesson_id}/export/download")
def download_export_file(lesson_id: str, db: Session = Depends(get_db)):
    """
    Serves the exported lesson file directly for browser download.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson or not lesson.current_version_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

    current_ver = db.query(LessonVersion).filter(LessonVersion.id == lesson.current_version_id).first()
    filename = f"lesson_{lesson.id[:8]}_v{current_ver.version_number}.md"
    file_path = os.path.join(export_service.export_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file has not been generated yet.")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="text/markdown"
    )
