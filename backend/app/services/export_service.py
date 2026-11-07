import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.core.config import settings
from app.schemas.lesson import LessonContent

class ExportService:
    def __init__(self):
        self.export_dir = Path(settings.EXPORT_DIR)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_lesson_markdown(
        self,
        lesson_id: str,
        version_number: int,
        content: LessonContent,
        factual_qc_rep: Optional[Dict[str, Any]] = None,
        instructional_qc_rep: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Creates a comprehensive Markdown export including the lesson,
        worked examples, activities, assessments, supplementary videos,
        references, and both Quality Control audit reports.
        """
        lines = []
        lines.append(f"# {content.title}")
        lines.append(f"**Target Audience:** {content.target_audience}  ")
        lines.append(f"**Total Duration:** {content.total_duration_minutes} Minutes  ")
        lines.append(f"**Exported At:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
        lines.append(f"**Lesson Version:** v{version_number} (ID: {lesson_id})\n")

        lines.append("## Learning Objective")
        lines.append(f"{content.learning_objective}\n")

        if content.prerequisites:
            lines.append("## Prerequisites")
            for p in content.prerequisites:
                lines.append(f"- {p}")
            lines.append("")

        lines.append("## Introduction")
        lines.append(f"{content.introduction}\n")

        lines.append("## 45-Minute Lesson Plan & Sections")
        lines.append("| Order | Section Title | Duration | Citations |")
        lines.append("|---|---|---|---|")
        for s in content.sections:
            cits = ", ".join(s.citations) if s.citations else "N/A"
            lines.append(f"| {s.order} | {s.title} | {s.duration_minutes} min | {cits} |")
        lines.append(f"| - | Interactive Activity | {content.interactive_activity.duration_minutes} min | Learner Task |")
        lines.append(f"| - | Knowledge Check | 7 min | Formative Assessment |")
        lines.append(f"| **Total** | | **{content.total_duration_minutes} min** | |\n")

        for s in content.sections:
            lines.append(f"### {s.title} ({s.duration_minutes} min)")
            lines.append(f"{s.content}\n")
            if s.key_points:
                lines.append("**Key Takeaways:**")
                for kp in s.key_points:
                    lines.append(f"- {kp}")
                lines.append("")

        if content.worked_examples:
            lines.append("## Worked Examples")
            for idx, ex in enumerate(content.worked_examples, 1):
                lines.append(f"### Example {idx}: {ex.title}")
                lines.append(f"**Scenario:** {ex.scenario}\n")
                lines.append(f"**Solution:**\n{ex.step_by_step_solution}\n")
                lines.append(f"**Explanation:** {ex.explanation}\n")

        if content.practical_applications:
            lines.append("## Practical Applications")
            for app in content.practical_applications:
                lines.append(f"### Domain: {app.domain}")
                lines.append(f"**Use Case:** {app.use_case}\n")
                if app.best_practices:
                    lines.append("**Best Practices:**")
                    for bp in app.best_practices:
                        lines.append(f"- {bp}")
                    lines.append("")

        lines.append("## Interactive Activity")
        lines.append(f"### {content.interactive_activity.title} ({content.interactive_activity.duration_minutes} min)")
        lines.append(f"{content.interactive_activity.instructions}\n")
        lines.append(f"**Expected Deliverable:** {content.interactive_activity.deliverable}\n")

        if content.knowledge_checks:
            lines.append("## Knowledge Check & Assessment")
            for idx, q in enumerate(content.knowledge_checks, 1):
                lines.append(f"#### Question {idx}: {q.question}")
                if q.options:
                    for opt in q.options:
                        lines.append(f"- {opt}")
                lines.append(f"\n**Correct Answer:** {q.correct_answer}")
                lines.append(f"**Explanation:** {q.explanation}\n")

        lines.append("## Summary")
        lines.append(f"{content.summary}\n")

        if content.supplementary_videos:
            lines.append("## Supplementary Videos")
            for v in content.supplementary_videos:
                lines.append(f"- [{v.title}]({v.url}) ({v.duration or 'Video'}) - *{v.channel or 'YouTube'}*")
                if v.relevance_note:
                    lines.append(f"  *Note: {v.relevance_note}*")
            lines.append("")

        if content.references:
            lines.append("## Bibliographic References")
            for r in content.references:
                url_str = f" - <{r.url_or_identifier}>" if r.url_or_identifier else ""
                lines.append(f"- **[{r.source_id}]** {r.title}{url_str}")
                if r.citation:
                    lines.append(f"  *{r.citation}*")
            lines.append("")

        # Append QC Reports
        lines.append("---\n")
        lines.append("## Quality Control (QC) Audit Reports\n")

        if factual_qc_rep:
            lines.append("### QC Layer 1: Research and Factual Accuracy Audit")
            lines.append(f"- **Overall Status:** `{factual_qc_rep.get('status', 'N/A').upper()}`")
            lines.append(f"- **Factual Score:** {factual_qc_rep.get('overall_score', 'N/A')} / 100")
            lines.append(f"- **Claims Verified:** {factual_qc_rep.get('claims_verified_count', 0)}")
            lines.append(f"- **Summary:** {factual_qc_rep.get('summary', '')}\n")
            issues = factual_qc_rep.get("issues", [])
            if issues:
                lines.append("#### Identified Factual Issues:")
                for iss in issues:
                    lines.append(f"- **[{iss.get('severity', '').upper()}]** {iss.get('explanation')}")
                    lines.append(f"  *Recommendation:* {iss.get('recommendation')}")
            else:
                lines.append("*No factual errors or unsupported claims detected.*\n")

        if instructional_qc_rep:
            lines.append("\n### QC Layer 2: Instructional Quality Audit")
            lines.append(f"- **Overall Status:** `{instructional_qc_rep.get('status', 'N/A').upper()}`")
            lines.append(f"- **Instructional Score:** {instructional_qc_rep.get('overall_score', 'N/A')} / 100")
            lines.append(f"- **Time Budget Assessment:** {instructional_qc_rep.get('time_budget_assessment', '')}")
            lines.append(f"- **Summary:** {instructional_qc_rep.get('summary', '')}\n")
            issues = instructional_qc_rep.get("issues", [])
            if issues:
                lines.append("#### Identified Pedagogical Issues:")
                for iss in issues:
                    lines.append(f"- **[{iss.get('severity', '').upper()}]** {iss.get('explanation')}")
                    lines.append(f"  *Recommendation:* {iss.get('recommendation')}")
            else:
                lines.append("*All instructional design benchmarks met cleanly.*\n")

        full_md = "\n".join(lines)
        
        # Save to disk
        filename = f"lesson_{lesson_id[:8]}_v{version_number}.md"
        file_path = self.export_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_md)

        return str(file_path)

export_service = ExportService()
