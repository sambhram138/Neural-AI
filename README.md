# AI-Powered Lesson Creation Tool

An enterprise-grade, locally runnable instructional design system that accepts a **Lesson Title** and **Learning Objective**, conducts multi-source research across authoritative websites, instructor-uploaded PDF books, and supplementary YouTube videos, synthesizes structured **45-minute lessons**, and validates them through **two independent Quality Control (QC) layers** before export.

---

## 1. Project Overview

Preparing a pedagogically sound, factually accurate lesson manually takes hours of researching primary standards, cross-referencing textbooks, drafting worked examples, pacing activities, and checking technical accuracy.

This application automates research and synthesis while keeping the instructor in full control:
- **Intake & Validation**: Rejects empty, whitespace-only, or invalid inputs before running AI pipelines.
- **Multi-Source Research**:
  - **Web**: Queries targeted conceptual keywords, fetches live HTML, parses with BeautifulSoup, and applies transparent publisher tier ranking (e.g. Tier 1 IETF RFCs, Tier 2 MDN, Tier 3 educational).
  - **Books (PDF)**: Allows instructors to upload textbook PDFs, extracts text page-by-page with **PyMuPDF**, chunks passages, and preserves exact page citations.
  - **YouTube**: Discovers supplementary visual learning resources via YouTube Data API v3 and curated channels.
- **Grounded 45-Minute Lesson Synthesis**:
  - Allocates time strictly across: Introduction (3m), Deep Dive (12m), Worked Examples (8m), Practical Application (7m), Interactive Activity (5m), Knowledge Check (7m), and Summary (3m) = **strictly 45 minutes**.
  - Programmatically validates duration in backend code (`validate_duration`).
- **Two Independent Quality Control (QC) Layers**:
  - **QC Layer 1 (Research & Factual Accuracy)**: Audits factual correctness against IETF/MDN/textbook evidence, flags unsupported claims, detects contradictions (e.g. GET described as encrypted or POST as idempotent), and assigns severity (`CRITICAL`, `HIGH`, `MEDIUM`).
  - **QC Layer 2 (Instructional Quality)**: Audits objective alignment, 45-minute time budget arithmetic, pacing balance, worked example clarity, deliverable clarity, and assessment coverage.
- **Review, Edit & Selective Recommendation Application**:
  - Version-safe: Manual instructor edits and accepted recommendations spawn new immutable `LessonVersion` records (never overwriting prior work).
- **Preview & Export**:
  - Exports approved lesson, bibliographic citations, and both QC audit reports as clean Markdown.

---

## 2. System Architecture

```text
+-----------------------------------------------------------------------------------+
|                        INSTRUCTOR DASHBOARD (UI / Web Browser)                    |
|   (Lesson Input Form -> Research Inspector -> Editor -> QC Audit View -> Export)  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v  REST API (FastAPI)
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND                                    |
|                                                                                   |
|  +--------------------+     +---------------------+     +----------------------+  |
|  | Input Validation   | --> | Research Engine     | --> | Synthesis & Evidence |  |
|  | (Pydantic Schemas) |     | - Web (Tavily/Scrap)|     | Packaging            |  |
|  +--------------------+     | - PDF (PyMuPDF)     |     +----------------------+  |
|                             | - YouTube Data API  |                |              |
|                             +---------------------+                v              |
|                                                         +----------------------+  |
|                                                         | 45-Min Lesson Gen    |  |
|                                                         | Engine (Gemini / AI) |  |
|                                                         +----------------------+  |
|                                                                    |              |
|                                     +------------------------------+              |
|                                     |                              |              |
|                                     v                              v              |
|                          +--------------------+         +--------------------+    |
|                          | QC Layer 1:        |         | QC Layer 2:        |    |
|                          | Factual Accuracy   |         | Instructional Qual |    |
|                          | Audit Report       |         | Audit Report       |    |
|                          +--------------------+         +--------------------+    |
|                                     \                              /              |
|                                      +--------------+-------------+               |
|                                                     |                             |
|                                                     v                             |
|                          +----------------------------------------------------+   |
|                          | Instructor Review & Recommendation Application     |   |
|                          | (Versioning, Manual Edits, Preview & Export)       |   |
|                          +----------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         PERSISTENCE & STORAGE (SQLite / SQLAlchemy)               |
|   Lessons | Versions | Research Sources | Chunks | QC Reports | Workflow Jobs     |
+-----------------------------------------------------------------------------------+
```

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | Python 3.12 + FastAPI | High-performance asynchronous REST API |
| **Data Validation** | Pydantic V2 + Pydantic-Settings | Strict request/response validation and duration checking |
| **Relational Database** | SQLite + SQLAlchemy 2.0 | Persistent lessons, versions, sources, QC reports, and jobs |
| **LLM & Synthesis** | Google Gemini (`google-genai` SDK) | Research synthesis and lesson generation with offline fallback |
| **Web Research** | HTTPX + BeautifulSoup4 | Search query generator, HTML retrieval, and text cleaning |
| **PDF Processing** | PyMuPDF (`pymupdf`) | Page-by-page text extraction and chunking preserving page numbers |
| **Video Discovery** | YouTube Data API v3 | Supplementary video resource retrieval |
| **Testing** | Pytest + Starlette TestClient | 17 comprehensive unit, integration, and QC failure tests |
| **Frontend UI** | HTML5 + Tailwind CSS + Vanilla JS | Single-page instructor interface served directly by FastAPI |

---

## 4. Directory Structure

```text
kalassignment/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── factual_qc_agent.py        # QC Layer 1 Fact Checker
│   │   │   ├── instructional_qc_agent.py  # QC Layer 2 Pedagogy Auditor
│   │   │   └── improvement_agent.py       # Recommendation Fix Engine
│   │   ├── api/
│   │   │   ├── lesson_routes.py           # Intake, metadata, generation, versions
│   │   │   ├── research_routes.py         # Web research, PDF upload, YouTube
│   │   │   ├── qc_routes.py               # Dual independent QC evaluations
│   │   │   └── export_routes.py           # Content edits, recommendations, export
│   │   ├── core/
│   │   │   ├── config.py                  # Pydantic BaseSettings (.env loader)
│   │   │   └── database.py                # SQLAlchemy engine & session factory
│   │   ├── models/
│   │   │   ├── lesson.py                  # Lesson & LessonVersion tables
│   │   │   ├── source.py                  # ResearchSource & ResearchChunk tables
│   │   │   ├── qc.py                      # QCReport table
│   │   │   └── workflow.py                # WorkflowJob stage tracking table
│   │   ├── research/
│   │   │   ├── query_generator.py         # Concept-specific query generator
│   │   │   ├── page_extractor.py          # HTML cleaner & paragraph chunker
│   │   │   ├── source_evaluator.py        # Publisher tier & relevance ranking
│   │   │   ├── web_research.py            # Web search & live page retrieval
│   │   │   ├── book_research.py           # PyMuPDF PDF reader & passage chunker
│   │   │   ├── youtube_research.py        # YouTube video discovery
│   │   │   └── synthesis.py               # Evidence packaging & gap analysis
│   │   ├── schemas/
│   │   │   ├── lesson.py                  # 45-min validated Lesson schema
│   │   │   ├── source.py                  # ResearchSource & Package schema
│   │   │   └── qc.py                      # Factual & Instructional QC schemas
│   │   ├── services/
│   │   │   ├── llm_service.py             # Gemini API client & pedagogical synthesizer
│   │   │   └── export_service.py          # Markdown & report export generator
│   │   └── main.py                        # FastAPI entry point & CORS
│   ├── tests/
│   │   ├── conftest.py                    # In-memory SQLite fixtures
│   │   ├── test_health.py                 # API health & root tests
│   │   ├── test_lessons.py                # Input validation & 45-min generation
│   │   ├── test_research.py               # Search queries, evaluation & extraction
│   │   └── test_qc_and_export.py          # Dual QC audits, defect detection & export
│   ├── pytest.ini                         # Pytest configuration
│   ├── requirements.txt                   # Locked dependencies
│   └── .env.example                       # Environment configuration template
├── frontend/
│   └── index.html                         # Full-featured responsive instructor dashboard
├── docs/
│   └── architecture.md                    # User stories & acceptance criteria
├── uploads/                               # Instructor uploaded book PDFs
├── exports/                               # Generated lesson & QC report exports
└── README.md
```

---

## 5. Setup & Running Instructions

### 5.1 Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Git

### 5.2 Local Installation

1. **Clone or navigate to the repository:**
   ```bash
   cd e:\kalassignment
   ```

2. **Set up the virtual environment:**
   ```powershell
   python -m venv backend\.venv
   backend\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r backend\requirements.txt
   ```

4. **Configure environment variables (optional):**
   Copy `backend/.env.example` to `backend/.env`:
   ```powershell
   cp backend\.env.example backend\.env
   ```
   *Note: If you have a Google Gemini API key or Tavily API key, paste them into `.env`. If left empty, the application runs its built-in pedagogical synthesizer and authoritative live retrieval seamlessly.*

5. **Start the FastAPI server:**
   ```powershell
   cd backend
   .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

6. **Open the Instructor Dashboard in your browser:**
   - **Interactive Web UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - **Interactive API Documentation (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - **API Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 6. Running Automated Tests

Run the full automated test suite containing 17 unit and integration tests:

```powershell
cd backend
.venv\Scripts\pytest.exe -v
```

All 17 tests verify:
- Health and status endpoints
- Rejection of blank / whitespace titles and objectives (HTTP 422)
- Lesson draft creation and database persistence
- Programmatic 45-minute duration validation
- Research query generation and publisher tier ranking
- Page cleaning and paragraph chunking
- PDF book upload and page number preservation using PyMuPDF
- Supplementary YouTube video cataloging
- **QC Layer 1 (Factual Accuracy)** clean pass and deliberate defect detection
- **QC Layer 2 (Instructional Quality)** 45-min budget validation
- Recommendation application spawning clean new versions
- Full Markdown export generation and download

---

## 7. End-to-End Workflow Demonstration

### Test Case 1: HTTP Requests and Responses
- **Lesson Title:** `HTTP Requests and Responses`
- **Learning Objective:** `Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.`
- **Verified Outcomes:**
  - Explains GET (safe, idempotent, parameters in URL query string) vs. POST (non-idempotent, payload in request body).
  - Explicitly notes that neither GET nor POST provides encryption by itself; encryption is provided by TLS/HTTPS.
  - Distinguishes 2xx (Success), 4xx (Client Errors), and 5xx (Server Faults).
  - Validates exact 45-minute breakdown (3m intro + 12m core concepts + 8m examples + 7m practical applications + 5m activity + 7m assessment + 3m summary).
  - QC Layer 1 verified 49 claims against RFC 9110 and MDN standards (Score: 100/100, `PASSED`).
  - QC Layer 2 verified pedagogical pacing and assessment alignment (Score: 100/100, `PASSED`).

### Test Case 2: Database Normalization
- **Lesson Title:** `Database Normalization`
- **Learning Objective:** `Explain 1NF, 2NF, and 3NF and identify how normalization reduces data redundancy and update anomalies.`
- **Verified Outcomes:**
  - Explains 1NF (atomic values, no repeating groups), 2NF (eliminate partial dependencies), and 3NF (eliminate transitive dependencies).
  - Step-by-step worked table decomposition from unnormalized orders table to 3NF.
  - Explains insertion, update, and deletion anomalies.
  - Exact 45-minute pacing schedule.
  - Both QC layers executed independently with traceable evidence.

### Demonstrating Deliberate Defect Detection & Recommendation Application
1. An instructor deliberately edits Section 2 to introduce a defect: *"GET is encrypted and completely protects passwords from inspection."*
2. **QC Layer 1 executes**:
   - Status changes to `NEEDS_REVISION` (Score drops to 65/100).
   - Identifies `CRITICAL` severity issue: `factual_error`.
   - Cites counter-evidence: *RFC 9110 specifies GET parameters are appended to the URI query string in plaintext and logged in server access logs.*
   - Provides recommended correction.
3. Instructor clicks **"Apply Fix"** (`POST /api/lessons/{id}/recommendations/apply`):
   - Corrects the defective statement.
   - Spawns Version 3 without overwriting earlier drafts or unrelated manual edits.
4. **QC Layer 1 automatically re-runs on Version 3**:
   - Status returns to `PASSED` (Score: 100/100).

---

## 8. API Endpoint Reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service health status |
| `POST` | `/api/lessons` | Create lesson draft with input validation |
| `GET` | `/api/lessons` | List all lessons |
| `GET` | `/api/lessons/{id}` | Retrieve lesson details & current active version |
| `PATCH` | `/api/lessons/{id}` | Update lesson metadata |
| `POST` | `/api/lessons/{id}/research` | Execute or retry website research |
| `POST` | `/api/lessons/{id}/upload-pdf` | Upload book PDF with PyMuPDF text extraction |
| `POST` | `/api/lessons/{id}/youtube` | Discover supplementary YouTube video resources |
| `GET` | `/api/lessons/{id}/sources` | List all collected sources with chunks and scores |
| `GET` | `/api/lessons/{id}/research/package` | Retrieve normalized traceable research package |
| `POST` | `/api/lessons/{id}/generate` | Synthesize structured 45-minute lesson |
| `POST` | `/api/lessons/{id}/qc` | Run independent QC Layer 1 and QC Layer 2 audits |
| `GET` | `/api/lessons/{id}/qc` | Retrieve latest QC audit reports |
| `PATCH` | `/api/lessons/{id}/content` | Save instructor manual edits as a new version |
| `POST` | `/api/lessons/{id}/recommendations/apply` | Selectively apply accepted QC recommendations |
| `GET` | `/api/lessons/{id}/preview` | Preview finalized lesson with QC reports |
| `POST` | `/api/lessons/{id}/export` | Export finalized lesson & QC reports to Markdown |
| `GET` | `/api/lessons/{id}/export/download` | Download exported Markdown file |
