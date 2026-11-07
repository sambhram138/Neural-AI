from typing import List, Optional
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.lesson import Lesson, LessonVersion
from app.schemas.lesson import (
    LessonCreateRequest,
    LessonUpdateRequest,
    LessonResponse,
    LessonListResponse,
    LessonVersionResponse,
    LessonContent,
)
from app.services.llm_service import llm_service

router = APIRouter(prefix="/api/lessons", tags=["Lessons"])

def _build_version_response(version: Optional[LessonVersion]) -> Optional[LessonVersionResponse]:
    if not version:
        return None
    return LessonVersionResponse(
        id=version.id,
        lesson_id=version.lesson_id,
        version_number=version.version_number,
        title=version.title,
        learning_objective=version.learning_objective,
        content=LessonContent.model_validate(version.content_json),
        total_duration_minutes=version.total_duration_minutes,
        created_by=version.created_by,
        created_at=version.created_at,
    )

def _build_lesson_response(lesson: Lesson, db: Session) -> LessonResponse:
    current_ver = None
    if lesson.current_version_id:
        v = db.query(LessonVersion).filter(LessonVersion.id == lesson.current_version_id).first()
        current_ver = _build_version_response(v)

    return LessonResponse(
        id=lesson.id,
        title=lesson.title,
        learning_objective=lesson.learning_objective,
        audience=lesson.audience or "General / Undergraduate",
        teaching_mode=lesson.teaching_mode or "self-learning",
        additional_instructions=lesson.additional_instructions,
        status=lesson.status,
        current_version_id=lesson.current_version_id,
        current_version=current_ver,
        created_at=lesson.created_at,
        updated_at=lesson.updated_at,
    )

@router.post("", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
def create_lesson(payload: LessonCreateRequest, db: Session = Depends(get_db)):
    """
    Creates a new lesson draft.
    Validates input parameters (title and learning objective cannot be blank).
    """
    lesson = Lesson(
        id=str(uuid.uuid4()),
        title=payload.title,
        learning_objective=payload.learning_objective,
        audience=payload.audience or "General / Undergraduate",
        teaching_mode=payload.teaching_mode or "self-learning",
        additional_instructions=payload.additional_instructions,
        status="draft",
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return _build_lesson_response(lesson, db)

@router.get("", response_model=LessonListResponse)
def list_lessons(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    List all created lessons with pagination.
    """
    total = db.query(Lesson).count()
    lessons = db.query(Lesson).order_by(Lesson.created_at.desc()).offset(skip).limit(limit).all()
    items = [_build_lesson_response(l, db) for l in lessons]
    return LessonListResponse(items=items, total=total)

@router.get("/{lesson_id}", response_model=LessonResponse)
def get_lesson(lesson_id: str, db: Session = Depends(get_db)):
    """
    Retrieve lesson details by ID.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with ID '{lesson_id}' not found")
    return _build_lesson_response(lesson, db)

@router.patch("/{lesson_id}", response_model=LessonResponse)
def update_lesson_metadata(lesson_id: str, payload: LessonUpdateRequest, db: Session = Depends(get_db)):
    """
    Update lesson metadata.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with ID '{lesson_id}' not found")

    if payload.title is not None:
        lesson.title = payload.title
    if payload.learning_objective is not None:
        lesson.learning_objective = payload.learning_objective
    if payload.audience is not None:
        lesson.audience = payload.audience
    if payload.teaching_mode is not None:
        lesson.teaching_mode = payload.teaching_mode
    if payload.additional_instructions is not None:
        lesson.additional_instructions = payload.additional_instructions
    if payload.status is not None:
        lesson.status = payload.status

    lesson.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lesson)
    return _build_lesson_response(lesson, db)

@router.post("/{lesson_id}/generate", response_model=LessonResponse)
def generate_lesson_content(lesson_id: str, db: Session = Depends(get_db)):
    """
    Generates structured 45-minute lesson content for the given lesson.
    Saves the generated output as a new LessonVersion and updates lesson.current_version_id.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with ID '{lesson_id}' not found")

    lesson.status = "generating"
    db.commit()

    try:
        content: LessonContent = llm_service.generate_basic_lesson(
            title=lesson.title,
            learning_objective=lesson.learning_objective,
            audience=lesson.audience or "General / Undergraduate",
            teaching_mode=lesson.teaching_mode or "self-learning",
            additional_instructions=lesson.additional_instructions,
        )

        # Calculate next version number
        latest_ver = (
            db.query(LessonVersion)
            .filter(LessonVersion.lesson_id == lesson_id)
            .order_by(LessonVersion.version_number.desc())
            .first()
        )
        version_num = (latest_ver.version_number + 1) if latest_ver else 1

        new_version = LessonVersion(
            id=str(uuid.uuid4()),
            lesson_id=lesson.id,
            version_number=version_num,
            title=content.title,
            learning_objective=content.learning_objective,
            content_json=content.model_dump(),
            total_duration_minutes=content.total_duration_minutes,
            created_by="system",
        )
        db.add(new_version)
        db.flush()

        lesson.current_version_id = new_version.id
        lesson.status = "generated"
        lesson.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(lesson)

        return _build_lesson_response(lesson, db)
    except Exception as e:
        db.rollback()
        lesson.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lesson generation failed: {str(e)}"
        )

@router.get("/{lesson_id}/versions", response_model=List[LessonVersionResponse])
def list_lesson_versions(lesson_id: str, db: Session = Depends(get_db)):
    """
    Retrieve all versions for a lesson.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with ID '{lesson_id}' not found")

    versions = db.query(LessonVersion).filter(LessonVersion.lesson_id == lesson_id).order_by(LessonVersion.version_number.asc()).all()
    return [_build_version_response(v) for v in versions]
