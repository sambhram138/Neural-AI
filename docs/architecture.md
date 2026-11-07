# AI-Powered Lesson Creation Tool

## Project Architecture & User Stories (Phase 0 Deliverable)

### 1. User Stories

- **US1: Lesson Intake & Validation**
  As an instructor, I want to input a Lesson Title and Learning Objective (along with optional target audience, teaching mode, and guidelines) and have them validated immediately so that invalid or empty inputs are rejected with clear feedback before any AI operations run.

- **US2: Multi-Source Research (Web, Books, YouTube)**
  As an instructor, I want the system to research credible web pages, uploaded PDF textbooks, and relevant YouTube videos so that the lesson is grounded in real, verifiable evidence rather than model hallucinations.

- **US3: 45-Minute Lesson Synthesis**
  As an instructor, I want the system to generate a structured 45-minute lesson containing explanations, worked examples, practical applications, an interactive activity, knowledge checks with answer guidance, supplementary resources, and reference citations where section times strictly sum to 45 minutes.

- **US4: Independent Quality Control (QC Layer 1 - Factual Accuracy)**
  As an instructor, I want a dedicated factual accuracy audit that checks all major claims against retrieved source evidence, flags unsupported or contradictory assertions, evaluates source reliability, and provides suggested corrections.

- **US5: Independent Quality Control (QC Layer 2 - Instructional Quality)**
  As an instructor, I want a dedicated instructional quality audit that verifies alignment with the learning objective, assesses pedagogical pacing and 45-minute time distribution, and evaluates the clarity of explanations and assessments.

- **US6: Review, Edit & Recommendation Application**
  As an instructor, I want to review both QC audit reports, selectively accept or reject recommendations, edit lesson sections directly, and save updated versions without losing my custom edits.

- **US7: Preview & Multi-Format Export**
  As an instructor, I want to preview the finalized lesson and export it along with its full reference list and both QC audit reports as DOCX, PDF, and Markdown.

- **US8: Error Handling & Step-by-Step Retries**
  As an instructor, I want failed stages (e.g. search failure, generation timeout, single QC failure) to be retriable independently without re-running previous stages or losing saved draft content.

---

### 2. Acceptance Criteria

| ID | Criteria | Validation Method |
|---|---|---|
| AC1 | Empty or whitespace-only title or learning objective returns HTTP 422 with a specific validation error. | Automated API test |
| AC2 | Creating a valid lesson draft creates a persistent database record with status `draft`. | Database query & API test |
| AC3 | Lesson content structure includes: title, objective, prerequisites, sequenced sections, worked examples, practical application, activity, knowledge check, summary, references, and supplementary videos. | Schema validation |
| AC4 | Sum of section duration minutes strictly equals 45 minutes (validated programmatically, not relying on LLM arithmetic). | Assertion logic `sum(durations) == 45` |
| AC5 | QC Layer 1 (Factual Accuracy) and QC Layer 2 (Instructional Quality) produce separate, independent audit reports with clear issue categories and severities (`critical`, `high`, `medium`, `low`). | Schema & isolation test |
| AC6 | Instructor edits create new version records and preserve manual modifications across restarts. | Versioning test |
| AC7 | Each pipeline stage saves intermediate state; retrying a stage does not wipe previously saved research or manual edits. | State transition & retry test |

---

### 3. System Workflow Diagram

```text
+-----------------------------------------------------------------------------------+
|                                 INSTRUCTOR INTERFACE                              |
|   (Lesson Input Form -> Research Inspector -> Editor -> QC Audit View -> Export)  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v  REST API
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND                                    |
|                                                                                   |
|  +--------------------+     +---------------------+     +----------------------+  |
|  | Input Validation   | --> | Research Engine     | --> | Synthesis & Evidence |  |
|  | (Pydantic Schemas) |     | - Web (Tavily/Scrap)|     | Packaging            |  |
|  +--------------------+     | - PDF (PyMuPDF/RAG) |     +----------------------+  |
|                             | - YouTube Data API  |                |              |
|                             +---------------------+                v              |
|                                                         +----------------------+  |
|                                                         | 45-Min Lesson Gen    |  |
|                                                         | Engine (LLM/Gemini)  |  |
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
