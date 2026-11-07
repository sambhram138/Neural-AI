from typing import List
import uuid
import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.lesson import Lesson
from app.models.source import ResearchSource, ResearchChunk
from app.models.workflow import WorkflowJob
from app.schemas.source import (
    ResearchSourceResponse,
    ResearchSourceListResponse,
    ResearchChunkResponse,
    ResearchPackage,
)
from app.research.web_research import perform_web_research
from app.research.book_research import extract_pdf_pages, chunk_pdf_pages, retrieve_relevant_book_chunks
from app.research.youtube_research import search_youtube_videos
from app.research.synthesis import build_research_package

router = APIRouter(prefix="/api/lessons", tags=["Research"])

def _source_to_response(s: ResearchSource) -> ResearchSourceResponse:
    return ResearchSourceResponse(
        id=s.id,
        lesson_id=s.lesson_id,
        source_type=s.source_type,
        title=s.title,
        author_publisher=s.author_publisher,
        url_or_identifier=s.url_or_identifier,
        published_date=s.published_date,
        retrieved_at=s.retrieved_at,
        relevance_score=s.relevance_score,
        source_metadata=s.source_metadata,
        status=s.status,
        chunks=[
            ResearchChunkResponse(
                id=c.id,
                source_id=c.source_id,
                chunk_text=c.chunk_text,
                page_number=c.page_number,
                section_heading=c.section_heading,
                created_at=c.created_at
            )
            for c in s.chunks
        ]
    )

@router.post("/{lesson_id}/research", response_model=ResearchSourceListResponse)
def run_lesson_research(lesson_id: str, db: Session = Depends(get_db)):
    """
    Executes website research for the lesson.
    Stores source metadata, publisher evaluation, and clean excerpt chunks.
    Allows independent retries without resetting other stages.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with ID '{lesson_id}' not found")

    # Log workflow job start
    job = WorkflowJob(
        id=str(uuid.uuid4()),
        lesson_id=lesson.id,
        stage="research",
        status="in_progress",
    )
    db.add(job)
    lesson.status = "researching"
    db.commit()

    try:
        # Perform research
        sources_data = perform_web_research(title=lesson.title, learning_objective=lesson.learning_objective)

        # Clear previously existing website sources for clean retry
        existing = db.query(ResearchSource).filter(
            ResearchSource.lesson_id == lesson_id,
            ResearchSource.source_type == "website"
        ).all()
        for e in existing:
            db.delete(e)
        db.flush()

        persisted_sources = []
        for s_data in sources_data:
            source = ResearchSource(
                id=str(uuid.uuid4()),
                lesson_id=lesson.id,
                source_type=s_data["source_type"],
                title=s_data["title"],
                author_publisher=s_data["author_publisher"],
                url_or_identifier=s_data["url_or_identifier"],
                published_date=s_data.get("published_date"),
                relevance_score=s_data.get("relevance_score", 1.0),
                status=s_data.get("status", "active"),
                source_metadata=s_data.get("source_metadata", {}),
            )
            db.add(source)
            db.flush()

            for c_data in s_data.get("chunks", []):
                chunk = ResearchChunk(
                    id=str(uuid.uuid4()),
                    source_id=source.id,
                    chunk_text=c_data["chunk_text"],
                    page_number=c_data.get("page_number"),
                    section_heading=c_data.get("section_heading"),
                )
                db.add(chunk)

            persisted_sources.append(source)

        job.status = "completed"
        job.updated_at = datetime.now(timezone.utc)
        lesson.status = "research_completed"
        lesson.updated_at = datetime.now(timezone.utc)
        db.commit()

        items = [_source_to_response(s) for s in persisted_sources]
        return ResearchSourceListResponse(items=items, total=len(items))

    except Exception as e:
        db.rollback()
        job.status = "failed"
        job.error_message = str(e)
        job.updated_at = datetime.now(timezone.utc)
        lesson.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research failed: {str(e)}"
        )

@router.post("/{lesson_id}/upload-pdf", response_model=ResearchSourceResponse)
def upload_book_pdf(
    lesson_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts an instructor-uploaded textbook or notes PDF.
    Extracts text page-by-page using PyMuPDF and preserves page numbers for citations.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson '{lesson_id}' not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported.")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_filename = f"{lesson_id}_{uuid.uuid4().hex[:6]}_{file.filename}"
    file_path = upload_dir / saved_filename

    # Read and save bytes
    file_bytes = file.file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded PDF is empty.")

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    try:
        pages_data = extract_pdf_pages(str(file_path))
        chunks_data = chunk_pdf_pages(pages_data)
        
        # Filter top relevant passages for lesson
        relevant_chunks = retrieve_relevant_book_chunks(
            chunks_data,
            title=lesson.title,
            learning_objective=lesson.learning_objective,
            top_k=8
        )

        source = ResearchSource(
            id=str(uuid.uuid4()),
            lesson_id=lesson.id,
            source_type="book_pdf",
            title=file.filename.replace(".pdf", ""),
            author_publisher="Instructor Upload",
            url_or_identifier=str(file_path),
            published_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            relevance_score=0.95,
            status="active",
            source_metadata={
                "page_count": len(pages_data),
                "total_chunks": len(chunks_data),
                "original_filename": file.filename
            }
        )
        db.add(source)
        db.flush()

        for c in relevant_chunks:
            chunk = ResearchChunk(
                id=str(uuid.uuid4()),
                source_id=source.id,
                chunk_text=c["chunk_text"],
                page_number=c.get("page_number"),
                section_heading=c.get("section_heading"),
            )
            db.add(chunk)

        db.commit()
        db.refresh(source)
        return _source_to_response(source)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@router.post("/{lesson_id}/youtube", response_model=ResearchSourceListResponse)
def run_youtube_research(lesson_id: str, db: Session = Depends(get_db)):
    """
    Finds relevant supplementary YouTube videos for the lesson objective.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson '{lesson_id}' not found")

    videos = search_youtube_videos(title=lesson.title, learning_objective=lesson.learning_objective)

    # Remove older youtube sources
    db.query(ResearchSource).filter(
        ResearchSource.lesson_id == lesson_id,
        ResearchSource.source_type == "youtube"
    ).delete()

    persisted_sources = []
    for v in videos:
        s = ResearchSource(
            id=str(uuid.uuid4()),
            lesson_id=lesson.id,
            source_type="youtube",
            title=v["title"],
            author_publisher=v.get("channel", "YouTube"),
            url_or_identifier=v["url"],
            published_date=v.get("published_date"),
            relevance_score=0.88,
            status="active",
            source_metadata={
                "duration": v.get("duration"),
                "relevance_note": v.get("relevance_note"),
                "video_id": v.get("video_id")
            }
        )
        db.add(s)
        persisted_sources.append(s)

    db.commit()
    items = [_source_to_response(s) for s in persisted_sources]
    return ResearchSourceListResponse(items=items, total=len(items))

@router.get("/{lesson_id}/sources", response_model=ResearchSourceListResponse)
def list_lesson_sources(lesson_id: str, db: Session = Depends(get_db)):
    """
    List all researched sources with metadata, evaluation notes, and extracted chunks.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with ID '{lesson_id}' not found")

    sources = db.query(ResearchSource).filter(ResearchSource.lesson_id == lesson_id).all()
    items = [_source_to_response(s) for s in sources]
    return ResearchSourceListResponse(items=items, total=len(items))

@router.get("/{lesson_id}/research/package", response_model=ResearchPackage)
def get_research_package(lesson_id: str, db: Session = Depends(get_db)):
    """
    Returns the normalized, traceable research package prepared for lesson generation and QC.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with ID '{lesson_id}' not found")

    sources = db.query(ResearchSource).filter(ResearchSource.lesson_id == lesson_id).all()
    source_responses = [_source_to_response(s) for s in sources]

    package = build_research_package(
        lesson_id=lesson.id,
        lesson_title=lesson.title,
        learning_objective=lesson.learning_objective,
        sources=source_responses
    )
    return package
