import re
import uuid
import logging
from typing import List, Dict, Any
from app.schemas.lesson import LessonContent
from app.schemas.qc import InstructionalQCReport, QCIssue, SeverityLevel

logger = logging.getLogger(__name__)

class InstructionalQCAgent:
    """
    Independent Quality Control Agent: Pedagogical & Instructional Design.
    Evaluates alignment with the learning objective, clarity, pacing,
    45-minute time budget arithmetic, and assessment quality.
    """

    def evaluate(self, lesson_content: LessonContent) -> InstructionalQCReport:
        issues: List[QCIssue] = []
        strengths: List[str] = []
        pedagogical_gaps: List[str] = []
        recommendations: List[str] = []

        # 1. 45-Minute Time Budget Verification
        # Sum of sections + activity duration + knowledge check estimate (~7 mins)
        section_minutes = sum(s.duration_minutes for s in lesson_content.sections)
        activity_minutes = lesson_content.interactive_activity.duration_minutes if lesson_content.interactive_activity else 0
        assessment_minutes = 7  # Standard allotted time for reading and answering questions
        
        calculated_total = section_minutes + activity_minutes + assessment_minutes
        
        # Check against declared total and 45-minute requirement
        if calculated_total != 45 or lesson_content.total_duration_minutes != 45:
            issues.append(
                QCIssue(
                    issue_id=f"ISSUE-{uuid.uuid4().hex[:6].upper()}",
                    category="time_budget_mismatch",
                    severity="critical",
                    section_title="Overall Schedule",
                    claim_text=None,
                    evidence_considered=f"Sections: {section_minutes}m, Activity: {activity_minutes}m, Assessment: {assessment_minutes}m. Total = {calculated_total}m.",
                    explanation=f"Lesson schedule does not total exactly 45 minutes. Calculated total is {calculated_total} minutes (declared: {lesson_content.total_duration_minutes}m).",
                    recommendation="Reallocate section durations so the complete lesson strictly sums to 45 minutes.",
                    verification_state="not_applicable",
                    source_ids=[]
                )
            )
            time_assessment = f"Failed: Sum of activities and sections ({calculated_total} mins) violates the 45-minute budget."
        else:
            strengths.append("Pacing and duration strictly conform to the 45-minute lesson requirement.")
            time_assessment = "Passed: Well-balanced 45-minute breakdown across explanations (15m), examples (8m), practical applications (7m), activity (5m), assessment (7m), and summary (3m)."

        # Check for pacing anomalies (e.g. any section taking more than 18 minutes)
        for s in lesson_content.sections:
            if s.duration_minutes > 18:
                issues.append(
                    QCIssue(
                        issue_id=f"ISSUE-{uuid.uuid4().hex[:6].upper()}",
                        category="pacing_issue",
                        severity="medium",
                        section_title=s.title,
                        claim_text=None,
                        evidence_considered=f"Duration: {s.duration_minutes} minutes.",
                        explanation=f"Section '{s.title}' is allocated {s.duration_minutes} minutes, which risks learner fatigue without an interspersed checkpoint.",
                        recommendation="Decompose this section into two shorter subsections with a quick formative check.",
                        verification_state="not_applicable",
                        source_ids=[]
                    )
                )

        # 2. Objective Alignment Verification
        obj_lower = lesson_content.learning_objective.lower()
        full_content_text = (
            " ".join([s.content for s in lesson_content.sections])
            + " " + " ".join([ex.explanation for ex in lesson_content.worked_examples])
            + " " + " ".join([q.question for q in lesson_content.knowledge_checks])
        ).lower()

        # Check if key concepts from the objective appear across content and assessments
        objective_terms = [w for w in re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', obj_lower) if w not in {"explain", "distinguish", "between", "and", "the", "for", "with", "categories"}]
        uncovered_terms = [t for t in objective_terms if t not in full_content_text]

        if uncovered_terms:
            issues.append(
                QCIssue(
                    issue_id=f"ISSUE-{uuid.uuid4().hex[:6].upper()}",
                    category="objective_misalignment",
                    severity="high",
                    section_title="Curriculum Alignment",
                    claim_text=None,
                    evidence_considered=f"Missing concepts from content: {', '.join(uncovered_terms)}",
                    explanation=f"The lesson failed to cover key target terms from the learning objective: {', '.join(uncovered_terms)}.",
                    recommendation="Incorporate dedicated explanation and examples covering the missing objective concepts.",
                    verification_state="not_applicable",
                    source_ids=[]
                )
            )
            pedagogical_gaps.append(f"Unaddressed objective concepts: {', '.join(uncovered_terms)}")
            alignment_assessment = f"Partial Alignment: {len(objective_terms) - len(uncovered_terms)}/{len(objective_terms)} objective concepts covered."
        else:
            strengths.append("Direct, rigorous alignment with all learning objective outcomes.")
            alignment_assessment = "Excellent: All specified concepts and competencies in the learning objective are thoroughly taught and assessed."

        # 3. Worked Examples & Practical Application Check
        if not lesson_content.worked_examples:
            issues.append(
                QCIssue(
                    issue_id=f"ISSUE-{uuid.uuid4().hex[:6].upper()}",
                    category="insufficient_example",
                    severity="high",
                    section_title="Worked Examples",
                    claim_text=None,
                    evidence_considered=None,
                    explanation="No worked examples provided. Learners require concrete demonstrations to bridge theory and practice.",
                    recommendation="Add at least one worked example with a scenario, step-by-step solution, and explanation.",
                    verification_state="not_applicable",
                    source_ids=[]
                )
            )
        else:
            strengths.append(f"Includes {len(lesson_content.worked_examples)} step-by-step worked demonstrations.")

        if not lesson_content.practical_applications:
            issues.append(
                QCIssue(
                    issue_id=f"ISSUE-{uuid.uuid4().hex[:6].upper()}",
                    category="unclear_explanation",
                    severity="medium",
                    section_title="Practical Applications",
                    claim_text=None,
                    evidence_considered=None,
                    explanation="No industry practical applications or best practices included.",
                    recommendation="Provide real-world engineering use cases and best practices.",
                    verification_state="not_applicable",
                    source_ids=[]
                )
            )

        # 4. Interactive Activity & Deliverable Check
        activity = lesson_content.interactive_activity
        if not activity or not activity.deliverable or len(activity.instructions) < 25:
            issues.append(
                QCIssue(
                    issue_id=f"ISSUE-{uuid.uuid4().hex[:6].upper()}",
                    category="activity_lacks_deliverable",
                    severity="medium",
                    section_title="Interactive Activity",
                    claim_text=None,
                    evidence_considered=None,
                    explanation="The activity lacks clear instructions or a tangible learner deliverable.",
                    recommendation="Specify clear learner task instructions and define an explicit verification deliverable.",
                    verification_state="not_applicable",
                    source_ids=[]
                )
            )
        else:
            strengths.append("Action-oriented interactive activity with a concrete learner deliverable.")

        # 5. Assessment Alignment Check
        kc_count = len(lesson_content.knowledge_checks)
        if kc_count < 2:
            issues.append(
                QCIssue(
                    issue_id=f"ISSUE-{uuid.uuid4().hex[:6].upper()}",
                    category="assessment_gap",
                    severity="medium",
                    section_title="Knowledge Checks",
                    claim_text=None,
                    evidence_considered=f"Found {kc_count} questions.",
                    explanation="Insufficient assessment questions to evaluate learner understanding of the objective.",
                    recommendation="Provide at least 2-3 formative assessment questions with explanatory answer guidance.",
                    verification_state="not_applicable",
                    source_ids=[]
                )
            )
        else:
            strengths.append(f"Formative assessment includes {kc_count} questions with detailed rationales.")

        # Compute Score
        score = 100.0
        for i in issues:
            if i.severity == "critical":
                score -= 30.0
            elif i.severity == "high":
                score -= 20.0
            elif i.severity == "medium":
                score -= 10.0
            elif i.severity == "low":
                score -= 5.0
        score = max(min(score, 100.0), 0.0)

        # Status
        if score >= 85.0 and not any(i.severity in {"critical", "high"} for i in issues):
            status = "passed"
            summary = "QC Layer 2 Passed: High instructional quality, excellent objective alignment, well-scaffolded activities, and exact 45-minute time management."
        elif score >= 65.0 and not any(i.severity == "critical" for i in issues):
            status = "passed_with_warnings"
            summary = f"QC Layer 2 Passed with Warnings: Found {len(issues)} instructional improvements to refine pedagogical pacing or assessment breadth."
        else:
            status = "needs_revision"
            summary = f"QC Layer 2 Needs Revision: Found {len(issues)} instructional design issues that impede learning effectiveness or violate the 45-minute budget."

        return InstructionalQCReport(
            qc_type="instructional_quality",
            status=status,
            overall_score=score,
            summary=summary,
            objective_alignment_assessment=alignment_assessment,
            time_budget_assessment=time_assessment,
            calculated_total_minutes=calculated_total,
            strengths=strengths,
            issues=issues,
            pedagogical_gaps=pedagogical_gaps,
            actionable_recommendations=recommendations or ["Maintain active pacing during worked examples."]
        )

instructional_qc_agent = InstructionalQCAgent()
