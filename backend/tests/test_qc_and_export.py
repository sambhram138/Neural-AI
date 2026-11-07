import os
import io
from app.schemas.lesson import LessonContent
from app.agents.factual_qc_agent import factual_qc_agent
from app.agents.instructional_qc_agent import instructional_qc_agent

def test_independent_qc_layers_clean_pass(client):
    """AC5: Both QC layers evaluate the generated lesson and return independent reports."""
    # 1. Create and generate lesson
    create_resp = client.post(
        "/api/lessons",
        json={
            "title": "HTTP Requests and Responses",
            "learning_objective": "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
        }
    )
    lesson_id = create_resp.json()["id"]
    client.post(f"/api/lessons/{lesson_id}/generate")

    # 2. Run both QC layers
    qc_resp = client.post(f"/api/lessons/{lesson_id}/qc")
    assert qc_resp.status_code == 200
    qc_data = qc_resp.json()

    assert qc_data["factual_qc"] is not None
    assert qc_data["instructional_qc"] is not None

    factual_rep = qc_data["factual_qc"]["report"]
    instr_rep = qc_data["instructional_qc"]["report"]

    # Verify Factual QC
    assert factual_rep["qc_type"] == "factual_accuracy"
    assert factual_rep["overall_score"] >= 80.0
    assert factual_rep["status"] in ("passed", "passed_with_warnings")
    assert len(factual_rep["strengths"]) >= 1

    # Verify Instructional QC
    assert instr_rep["qc_type"] == "instructional_quality"
    assert instr_rep["calculated_total_minutes"] == 45
    assert instr_rep["status"] in ("passed", "passed_with_warnings")
    assert "Passed" in instr_rep["time_budget_assessment"]

def test_qc_factual_detects_deliberate_defect_and_recommends_fix(client):
    """
    Step 15.6: Introduce a known factual defect (claiming GET is encrypted),
    verify QC Layer 1 catches it with critical severity and RFC 9110 citation,
    apply recommendation, and verify the new version fixes it.
    """
    create_resp = client.post(
        "/api/lessons",
        json={
            "title": "HTTP Requests and Responses",
            "learning_objective": "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
        }
    )
    lesson_id = create_resp.json()["id"]
    gen_resp = client.post(f"/api/lessons/{lesson_id}/generate")
    content = gen_resp.json()["current_version"]["content"]

    # Deliberately introduce factual defect into section 2
    content["sections"][1]["content"] += " Note: GET is encrypted and completely protects passwords from inspection."

    # Save as manual edit
    edit_resp = client.patch(
        f"/api/lessons/{lesson_id}/content",
        json={"content": content, "edit_summary": "Test defect injection"}
    )
    assert edit_resp.status_code == 200
    ver2_id = edit_resp.json()["id"]

    # Run QC on defective version
    qc_resp = client.post(f"/api/lessons/{lesson_id}/qc")
    assert qc_resp.status_code == 200
    factual_data = qc_resp.json()["factual_qc"]["report"]

    assert factual_data["status"] == "needs_revision"
    assert factual_data["overall_score"] < 70.0
    
    # Verify the specific issue was flagged
    critical_issues = [i for i in factual_data["issues"] if i["category"] == "factual_error"]
    assert len(critical_issues) >= 1
    defect_issue = critical_issues[0]
    assert "RFC 9110" in defect_issue["evidence_considered"]
    assert defect_issue["severity"] == "critical"

    # Apply the recommendation
    apply_resp = client.post(
        f"/api/lessons/{lesson_id}/recommendations/apply",
        json={"accepted_issue_ids": [defect_issue["issue_id"]]}
    )
    assert apply_resp.status_code == 200
    ver3_data = apply_resp.json()
    assert ver3_data["version_number"] == 3

    # Rerun QC on fixed version
    rerun_qc_resp = client.post(f"/api/lessons/{lesson_id}/qc")
    assert rerun_qc_resp.status_code == 200
    rerun_factual = rerun_qc_resp.json()["factual_qc"]["report"]
    assert rerun_factual["status"] in ("passed", "passed_with_warnings")
    assert rerun_factual["overall_score"] >= 80.0

def test_preview_and_export_lifecycle(client):
    """Test preview and export of approved lesson and QC reports."""
    create_resp = client.post(
        "/api/lessons",
        json={
            "title": "HTTP Requests and Responses",
            "learning_objective": "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
        }
    )
    lesson_id = create_resp.json()["id"]
    client.post(f"/api/lessons/{lesson_id}/generate")
    client.post(f"/api/lessons/{lesson_id}/qc")

    # 1. Preview
    preview_resp = client.get(f"/api/lessons/{lesson_id}/preview")
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    assert preview_data["lesson_id"] == lesson_id
    assert "factual_qc_report" in preview_data
    assert "instructional_qc_report" in preview_data

    # 2. Export
    export_resp = client.post(f"/api/lessons/{lesson_id}/export")
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["export_format"] == "markdown"
    assert os.path.exists(export_data["file_path"])

    # 3. Download export file
    dl_resp = client.get(f"/api/lessons/{lesson_id}/export/download")
    assert dl_resp.status_code == 200
    content_text = dl_resp.text
    assert "# HTTP Requests and Responses" in content_text
    assert "Quality Control (QC) Audit Reports" in content_text
    assert "QC Layer 1" in content_text
    assert "QC Layer 2" in content_text

def test_youtube_research_endpoint(client):
    """Test discovering and cataloging supplementary YouTube videos."""
    create_resp = client.post(
        "/api/lessons",
        json={
            "title": "HTTP Requests and Responses",
            "learning_objective": "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
        }
    )
    lesson_id = create_resp.json()["id"]

    yt_resp = client.post(f"/api/lessons/{lesson_id}/youtube")
    assert yt_resp.status_code == 200
    yt_data = yt_resp.json()
    assert yt_data["total"] >= 1
    first_video = yt_data["items"][0]
    assert first_video["source_type"] == "youtube"
    assert "youtube.com" in first_video["url_or_identifier"]

def test_pdf_upload_and_extraction(client, tmp_path):
    """Test uploading an instructor reference PDF and extracting page-numbered chunks."""
    create_resp = client.post(
        "/api/lessons",
        json={
            "title": "HTTP Requests and Responses",
            "learning_objective": "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
        }
    )
    lesson_id = create_resp.json()["id"]

    # Generate a small sample PDF using PyMuPDF
    import pymupdf
    pdf_doc = pymupdf.open()
    page1 = pdf_doc.new_page()
    page1.insert_text((50, 72), "Chapter 1: The HTTP Protocol. GET requests are safe and idempotent. They must never cause server side effects.")
    page2 = pdf_doc.new_page()
    page2.insert_text((50, 72), "Chapter 2: Status Categories. 2xx codes represent successful responses, 4xx client errors, and 5xx server faults.")
    
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    # Upload PDF via multipart/form-data
    upload_resp = client.post(
        f"/api/lessons/{lesson_id}/upload-pdf",
        files={"file": ("http_networking_textbook.pdf", pdf_bytes, "application/pdf")}
    )
    assert upload_resp.status_code == 200
    source_data = upload_resp.json()
    assert source_data["source_type"] == "book_pdf"
    assert source_data["title"] == "http_networking_textbook"
    assert len(source_data["chunks"]) >= 1
    
    # Verify page numbers were preserved
    all_chunks_text = " ".join(c["chunk_text"] for c in source_data["chunks"])
    assert "HTTP" in all_chunks_text
    assert any(c["page_number"] in (1, 2) for c in source_data["chunks"])
