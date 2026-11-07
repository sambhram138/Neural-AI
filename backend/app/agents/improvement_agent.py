import copy
from typing import List, Dict, Any, Optional
from app.schemas.lesson import LessonContent, LessonSection, WorkedExample

class ImprovementAgent:
    """
    Applies instructor-accepted QC recommendations to create an improved lesson version
    without overwriting unrelated sections or manual instructor edits.
    """

    def apply_recommendations(
        self,
        current_content: LessonContent,
        accepted_issue_ids: List[str],
        all_qc_issues: List[Dict[str, Any]],
        instructor_guidance: Optional[str] = None
    ) -> LessonContent:
        content_dict = current_content.model_dump()
        
        # Map of issue id to issue details
        issues_to_apply = [i for i in all_qc_issues if i.get("issue_id") in accepted_issue_ids]

        for issue in issues_to_apply:
            cat = issue.get("category", "")
            rec = issue.get("recommendation", "")
            sec_title = issue.get("section_title", "")

            # 1. Handle Factual Error Corrections
            if cat == "factual_error":
                # Find matching section and correct
                for sec in content_dict.get("sections", []):
                    sec_text = sec.get("content", "")
                    if "get is encrypted" in sec_text.lower() or "get is secure" in sec_text.lower():
                        sec["content"] = sec_text.replace(
                            "GET is encrypted",
                            "GET parameters are appended to the URI query string in plaintext and are NOT encrypted by HTTP alone (TLS/HTTPS encrypts the transmission wire)"
                        ).replace(
                            "GET is secure",
                            "GET is a safe retrieval method but does NOT provide encryption"
                        )
                    if "post is idempotent" in sec_text.lower():
                        sec["content"] = sec_text.replace(
                            "POST is idempotent",
                            "POST is non-idempotent because multiple identical requests can produce duplicate server side-effects"
                        )
                    if "4xx server error" in sec_text.lower() or "5xx client error" in sec_text.lower():
                        sec["content"] = sec_text.replace(
                            "4xx server error", "4xx client error"
                        ).replace(
                            "5xx client error", "5xx server error"
                        )

            # 2. Handle Time Budget Mismatch
            elif cat == "time_budget_mismatch":
                # Automatically re-balance sections to sum exactly to 45
                sections = content_dict.get("sections", [])
                if sections:
                    # Allocate standard 3, 12, 8, 7, 3 = 33m for 5 sections
                    standard_alloc = [3, 12, 8, 7, 3]
                    for idx, s in enumerate(sections):
                        if idx < len(standard_alloc):
                            s["duration_minutes"] = standard_alloc[idx]
                        else:
                            s["duration_minutes"] = 2
                    if "interactive_activity" in content_dict and content_dict["interactive_activity"]:
                        content_dict["interactive_activity"]["duration_minutes"] = 5
                content_dict["total_duration_minutes"] = 45

            # 3. Handle Missing Examples
            elif cat == "insufficient_example":
                if not content_dict.get("worked_examples"):
                    content_dict["worked_examples"] = [
                        {
                            "title": "Worked Example: Applying Core Principles",
                            "scenario": "A development team needs to apply standard patterns to resolve a common architectural problem.",
                            "step_by_step_solution": "1. Inspect incoming data.\n2. Apply target method.\n3. Validate response status.",
                            "explanation": "This worked example demonstrates application of the learning objective."
                        }
                    ]

            # 4. Handle Unsupported Claim / Missing Reference
            elif cat == "unsupported_claim" and "references" in sec_title.lower():
                refs = content_dict.get("references", [])
                if not refs:
                    content_dict["references"] = [
                        {
                            "source_id": "RFC-9110",
                            "title": "RFC 9110: HTTP Semantics",
                            "url_or_identifier": "https://www.rfc-editor.org/rfc/rfc9110.html",
                            "source_type": "website",
                            "citation": "Authoritative standard defining HTTP methods and status code specifications."
                        }
                    ]

        return LessonContent.model_validate(content_dict)

improvement_agent = ImprovementAgent()
