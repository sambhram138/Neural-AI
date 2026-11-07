from typing import Optional
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.lesson import Lesson, LessonVersion
from app.models.qc import QCReport
from app.models.workflow import WorkflowJob
from app.schemas.lesson import LessonContent
from app.schemas.qc import (
    CombinedQCResponse,
    QCReportResponse,
    FactualQCReport,
    InstructionalQCReport,
)
from app.agents.factual_qc_agent import factual_qc_agent
from app.agents.instructional_qc_agent import instructional_qc_agent
from app.api.research_routes import get_research_package

router = APIRouter(prefix="/api/lessons", tags=["Quality Control"])

def _qc_db_to_response(q: QCReport) -> QCReportResponse:
    return QCReportResponse(
        id=q.id,
        lesson_version_id=q.lesson_version_id,
        qc_type=q.qc_type,
        status=q.status,
        overall_score=q.overall_score,
        report=q.report_json,
        created_at=q.created_at,
    )

@router.post("/{lesson_id}/qc", response_model=CombinedQCResponse)
def run_qc_evaluation(
    lesson_id: str,
    layer: Optional[str] = Query(None, description="Run 'factual', 'instructional', or both (default)"),
    db: Session = Depends(get_db)
):
    """
    Executes independent Quality Control evaluation on the current lesson version:
    - QC Layer 1: Research and Factual Accuracy
    - QC Layer 2: Instructional Quality
    Both produce separate audit reports with actionable issues and suggested improvements.
    Supports stage-specific retries.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson '{lesson_id}' not found")

    if not lesson.current_version_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot run QC: No lesson content has been generated yet."
        )

    version = db.query(LessonVersion).filter(LessonVersion.id == lesson.current_version_id).first()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LessonVersion not found")

    lesson_content = LessonContent.model_validate(version.content_json)
    
    # Retrieve research package for factual cross-referencing
    research_pkg = None
    try:
        research_pkg = get_research_package(lesson_id=lesson_id, db=db)
    except Exception:
        pass

    run_factual = layer in (None, "both", "factual")
    run_instructional = layer in (None, "both", "instructional")

    # Layer 1: Factual Accuracy
    if run_factual:
        job1 = WorkflowJob(id=str(uuid.uuid4()), lesson_id=lesson.id, stage="qc_factual", status="in_progress")
        db.add(job1)
        db.commit()
        try:
            factual_rep: FactualQCReport = factual_qc_agent.evaluate(lesson_content, research_pkg)
            
            # Remove any older factual QC report for this exact version
            db.query(QCReport).filter(
                QCReport.lesson_version_id == version.id,
                QCReport.qc_type == "factual_accuracy"
            ).delete()

            qc1 = QCReport(
                id=str(uuid.uuid4()),
                lesson_version_id=version.id,
                qc_type="factual_accuracy",
                status=factual_rep.status,
                overall_score=factual_rep.overall_score,
                report_json=factual_rep.model_dump(),
            )
            db.add(qc1)
            job1.status = "completed"
            job1.updated_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as e:
            job1.status = "failed"
            job1.error_message = str(e)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Factual QC failed: {str(e)}")

    # Layer 2: Instructional Quality
    if run_instructional:
        job2 = WorkflowJob(id=str(uuid.uuid4()), lesson_id=lesson.id, stage="qc_instructional", status="in_progress")
        db.add(job2)
        db.commit()
        try:
            instr_rep: InstructionalQCReport = instructional_qc_agent.evaluate(lesson_content)

            # Remove older instructional QC report for this exact version
            db.query(QCReport).filter(
                QCReport.lesson_version_id == version.id,
                QCReport.qc_type == "instructional_quality"
            ).delete()

            qc2 = QCReport(
                id=str(uuid.uuid4()),
                lesson_version_id=version.id,
                qc_type="instructional_quality",
                status=instr_rep.status,
                overall_score=instr_rep.overall_score,
                report_json=instr_rep.model_dump(),
            )
            db.add(qc2)
            job2.status = "completed"
            job2.updated_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as e:
            job2.status = "failed"
            job2.error_message = str(e)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Instructional QC failed: {str(e)}")

    lesson.status = "qc_completed"
    lesson.updated_at = datetime.now(timezone.utc)
    db.commit()

    return get_lesson_qc_reports(lesson_id=lesson_id, db=db)

@router.get("/{lesson_id}/qc", response_model=CombinedQCResponse)
def get_lesson_qc_reports(lesson_id: str, db: Session = Depends(get_db)):
    """
    Retrieve both independent QC reports for the active lesson version.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson or not lesson.current_version_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No generated lesson version found.")

    reports = db.query(QCReport).filter(QCReport.lesson_version_id == lesson.current_version_id).all()

    factual_rep = None
    instr_rep = None
    all_issues = []

    for r in reports:
        rep_resp = _qc_db_to_response(r)
        if r.qc_type == "factual_accuracy":
            factual_rep = rep_resp
            all_issues.extend(r.report_json.get("issues", []))
        elif r.qc_type == "instructional_quality":
            instr_rep = rep_resp
            all_issues.extend(r.report_json.get("issues", []))

    return CombinedQCResponse(
        lesson_version_id=lesson.current_version_id,
        factual_qc=factual_rep,
        instructional_qc=instr_rep,
        all_issues=all_issues,
    )
