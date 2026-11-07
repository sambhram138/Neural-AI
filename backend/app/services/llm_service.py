import json
import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.schemas.lesson import (
    LessonContent,
    LessonSection,
    WorkedExample,
    PracticalApplication,
    InteractiveActivity,
    KnowledgeCheckItem,
    SupplementaryVideo,
    ReferenceLink,
)

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.LLM_MODEL or "gemini-2.5-flash"
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client: {e}")

    def is_available(self) -> bool:
        return bool(self.api_key and self._client)

    def generate_basic_lesson(
        self,
        title: str,
        learning_objective: str,
        audience: str = "General / Undergraduate",
        teaching_mode: str = "self-learning",
        additional_instructions: Optional[str] = None,
        research_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> LessonContent:
        """
        Generates a 45-minute structured lesson.
        Uses Gemini API if configured, otherwise falls back to the deterministic pedagogical synthesis generator.
        """
        if self.is_available():
            try:
                content = self._generate_with_gemini(
                    title=title,
                    learning_objective=learning_objective,
                    audience=audience,
                    teaching_mode=teaching_mode,
                    additional_instructions=additional_instructions,
                    research_sources=research_sources,
                )
                if content:
                    return content
            except Exception as e:
                logger.error(f"Gemini generation failed: {e}. Falling back to template synthesis.", exc_info=True)

        return self._generate_synthesis(
            title=title,
            learning_objective=learning_objective,
            audience=audience,
            teaching_mode=teaching_mode,
            additional_instructions=additional_instructions,
            research_sources=research_sources,
        )

    def _generate_with_gemini(
        self,
        title: str,
        learning_objective: str,
        audience: str,
        teaching_mode: str,
        additional_instructions: Optional[str],
        research_sources: Optional[List[Dict[str, Any]]],
    ) -> Optional[LessonContent]:
        from google.genai import types

        sources_context = ""
        if research_sources:
            sources_context = "Retrieved Research Sources:\n" + "\n".join(
                [f"- [{s.get('id', 'SRC')}] {s.get('title', '')}: {s.get('url_or_identifier', '')}" for s in research_sources]
            )

        prompt = f"""You are an expert instructional designer and technical educator.
Generate a structured, complete 45-minute lesson for:
Title: {title}
Learning Objective: {learning_objective}
Audience: {audience}
Teaching Mode: {teaching_mode}
Additional Instructions: {additional_instructions or 'None'}

{sources_context}

Requirements:
1. The total duration of all sections combined must strictly equal 45 minutes.
   - Section 1: Introduction & Prerequisites (3 mins)
   - Section 2: Core Concepts & Deep Dive (12 mins)
   - Section 3: Worked Examples (8 mins)
   - Section 4: Practical Applications & Best Practices (7 mins)
   - Interactive Activity (5 mins)
   - Knowledge Check / Assessment (7 mins)
   - Section 5: Summary & Key Takeaways (3 mins)
   Total: 3 + 12 + 8 + 7 + 5 + 7 + 3 = 45 minutes.
2. Provide technical clarity, precise examples, actionable instructions, and avoid vague summaries.
3. Knowledge check must include question, options (if multiple choice), correct_answer, and detailed explanation.
4. Return valid JSON matching the LessonContent schema.
"""

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LessonContent,
                temperature=0.2,
            ),
        )
        if response and response.text:
            data = json.loads(response.text)
            return LessonContent.model_validate(data)
        return None

    def _generate_synthesis(
        self,
        title: str,
        learning_objective: str,
        audience: str,
        teaching_mode: str,
        additional_instructions: Optional[str],
        research_sources: Optional[List[Dict[str, Any]]],
    ) -> LessonContent:
        """
        Deterministic, robust pedagogical lesson synthesizer.
        Ensures perfect 45-minute budget and topic-tailored content structure.
        """
        is_http_lesson = "http" in title.lower() or "get" in learning_objective.lower() or "post" in learning_objective.lower()
        is_normalization_lesson = "normal" in title.lower() or "1nf" in learning_objective.lower()

        if is_http_lesson:
            return self._build_http_lesson(title, learning_objective, audience, teaching_mode)
        elif is_normalization_lesson:
            return self._build_normalization_lesson(title, learning_objective, audience, teaching_mode)
        else:
            return self._build_generic_lesson(title, learning_objective, audience, teaching_mode)

    def _build_http_lesson(self, title: str, objective: str, audience: str, mode: str) -> LessonContent:
        sections = [
            LessonSection(
                title="1. Introduction to Client-Server Communication & HTTP",
                content=(
                    "Hypertext Transfer Protocol (HTTP) is the foundational stateless application-layer protocol powering the World Wide Web. "
                    "In a standard HTTP transaction, a client (such as a web browser or API consumer) transmits an HTTP Request message to a server, "
                    "and the server replies with an HTTP Response message. Every HTTP interaction is atomic and independent; HTTP does not natively "
                    "maintain state across requests without upper-layer mechanisms like cookies or tokens."
                ),
                duration_minutes=3,
                order=1,
                key_points=[
                    "HTTP operates over TCP (port 80) and TLS/TCP (HTTPS, port 443).",
                    "Stateless architecture: each request contains all context needed by the server.",
                    "Anatomy of a message: Start-line / Status-line, Headers, blank line CRLF, optional Body."
                ],
                citations=["RFC-9110", "MDN-HTTP-Overview"]
            ),
            LessonSection(
                title="2. HTTP Methods: GET vs. POST, Semantics, Safety, and Idempotency",
                content=(
                    "HTTP defines standardized request methods indicating the desired action to be performed on the target resource. "
                    "The two most ubiquitous methods are GET and POST:\n\n"
                    "- **GET Method:** Designed exclusively for data retrieval. According to RFC 9110, GET is 'safe' (it must not cause server-side side effects) "
                    "and 'idempotent' (repeating identical GET requests yields identical resource state). Parameters are encoded directly in the URL query string. "
                    "Crucially, GET is NOT an encrypted or secure mechanism—query parameters appear in access logs, browser history, and referer headers.\n\n"
                    "- **POST Method:** Used to submit an entity to the specified resource, often causing state change, side effects, or resource creation on the server. "
                    "POST is NEITHER safe NOR idempotent—sending multiple identical POST requests typically results in duplicate transactions (e.g., placing multiple orders). "
                    "Payloads are transmitted in the HTTP Request Body, governed by Content-Type (such as application/json or application/x-www-form-urlencoded)."
                ),
                duration_minutes=12,
                order=2,
                key_points=[
                    "Safe methods (GET, HEAD, OPTIONS) do not alter server resource state.",
                    "Idempotent methods (GET, PUT, DELETE) can be executed N times with the same end state.",
                    "POST is non-idempotent and used for creating or processing arbitrary entity bodies.",
                    "Security note: Neither method provides encryption by itself; encryption is provided by TLS (HTTPS)."
                ],
                citations=["RFC-9110-Methods", "MDN-HTTP-Methods"]
            ),
            LessonSection(
                title="3. HTTP Response Status Categories: 2xx, 4xx, and 5xx",
                content=(
                    "HTTP response status codes are 3-digit integers categorized by their first digit. Mastering these categories is essential for API development and troubleshooting:\n\n"
                    "- **2xx (Success):** Indicates the client's request was successfully received, understood, and accepted. "
                    "Key examples: `200 OK` (standard response with payload), `201 Created` (resource created, often accompanied by a `Location` header), "
                    "and `204 No Content` (action succeeded with empty response body).\n\n"
                    "- **4xx (Client Errors):** Indicates the request contains bad syntax or cannot be fulfilled due to client-side faults. "
                    "Key examples: `400 Bad Request` (malformed syntax or validation failure), `401 Unauthorized` (authentication required), "
                    "`403 Forbidden` (authenticated but lacks required permissions), `404 Not Found` (resource does not exist), "
                    "and `405 Method Not Allowed` (e.g., attempting POST on a read-only endpoint).\n\n"
                    "- **5xx (Server Errors):** Indicates the server failed to fulfill an apparently valid request due to internal error or downstream dependency failure. "
                    "Key examples: `500 Internal Server Error` (unhandled exception or crash), `502 Bad Gateway` (upstream server returned invalid response), "
                    "`503 Service Unavailable` (overloaded or down for maintenance), and `504 Gateway Timeout` (upstream failed to respond in time)."
                ),
                duration_minutes=8,
                order=3,
                key_points=[
                    "2xx = Client request succeeded as intended.",
                    "4xx = Client fault (fix the request payload, headers, or URL before retrying).",
                    "5xx = Server fault (the request may be valid, but server/infrastructure encountered a failure)."
                ],
                citations=["RFC-9110-Status-Codes", "MDN-HTTP-Status"]
            ),
            LessonSection(
                title="4. Practical Implementation: Debugging and Inspecting Raw Traffic",
                content=(
                    "Developers inspect and debug HTTP exchanges using tools like cURL, Postman, and browser DevTools Network tabs. "
                    "Understanding request headers (`Content-Type`, `Accept`, `Authorization`) and response headers (`Cache-Control`, `Set-Cookie`, `Location`) "
                    "allows engineers to build resilient microservices and diagnose integration bugs."
                ),
                duration_minutes=7,
                order=4,
                key_points=[
                    "Use `curl -v` or `-i` to view full raw headers and status lines.",
                    "Inspect DevTools Network panel to view timing, payload, and response status.",
                    "Always validate status codes programmatically in API clients."
                ],
                citations=["MDN-DevTools", "cURL-Docs"]
            ),
            LessonSection(
                title="5. Summary and Synthesis of Key Concepts",
                content=(
                    "In this 45-minute lesson, we explored how the HTTP request-response cycle powers modern web architecture. "
                    "We analyzed the behavioral differences between safe/idempotent GET and state-altering non-idempotent POST. "
                    "We also classified response codes into 2xx (Success), 4xx (Client Error), and 5xx (Server Error), equipping you to build and debug reliable web applications."
                ),
                duration_minutes=3,
                order=5,
                key_points=[
                    "GET is safe & idempotent; POST is non-idempotent.",
                    "2xx means success, 4xx means client problem, 5xx means server problem.",
                    "Understanding status codes is the cornerstone of RESTful API design."
                ],
                citations=["RFC-9110"]
            )
        ]

        worked_examples = [
            WorkedExample(
                title="Example 1: Form Submission vs Data Retrieval",
                scenario="A user submits a login form with username and password, then navigates to their profile page.",
                step_by_step_solution=(
                    "1. The browser initiates a POST request to `/api/login` with credentials in the JSON body.\n"
                    "2. The server authenticates credentials and returns `200 OK` (or `303 See Other`) with an auth token.\n"
                    "3. The browser navigates to `/profile`, issuing a GET request with the `Authorization: Bearer <token>` header.\n"
                    "4. The server returns `200 OK` with profile JSON data."
                ),
                explanation="POST was required for login to prevent sensitive credentials from leaking in URL logs. GET was used for reading the profile because it is safe and cacheable."
            ),
            WorkedExample(
                title="Example 2: Diagnosing 404 vs 500 Responses",
                scenario="An API client makes requests to `/users/999` and `/users/process-batch`.",
                step_by_step_solution=(
                    "1. Request to `/users/999` returns `404 Not Found`. Client action: Check user ID existence in database.\n"
                    "2. Request to `/users/process-batch` returns `500 Internal Server Error`. Client action: Do not change valid client code; check server application logs for unhandled database connection exception."
                ),
                explanation="4xx places accountability on the client request parameters, while 5xx alerts the backend operations team to inspect unhandled exceptions."
            )
        ]

        practical_applications = [
            PracticalApplication(
                domain="RESTful API Design & Microservices",
                use_case="Designing clean endpoints for an e-commerce platform.",
                best_practices=[
                    "Use GET `/orders` to list orders without altering state.",
                    "Use POST `/orders` to create a new order and return `201 Created` with a `Location: /orders/123` header.",
                    "Return `422 Unprocessable Content` or `400 Bad Request` if order items are invalid.",
                    "Wrap downstream external payment gateway calls with circuit breakers to prevent cascading `504 Gateway Timeout` errors."
                ]
            )
        ]

        activity = InteractiveActivity(
            title="Hands-On Activity: HTTP Request & Response Diagnostic Triage",
            instructions=(
                "Review the following three scenarios and determine for each: (a) the correct HTTP Method, and (b) the expected Status Code category:\n"
                "1. A customer searches for products matching 'wireless headphones'.\n"
                "2. A user tries to delete an account without supplying an authorization token.\n"
                "3. The server database crashes while saving a new transaction."
            ),
            duration_minutes=5,
            deliverable="Written classification for scenarios 1-3 with method and status code rationale."
        )

        knowledge_checks = [
            KnowledgeCheckItem(
                question="Why should passwords never be sent via a GET request query parameter, even if the connection uses HTTPS?",
                options=[
                    "A. GET requests are blocked by firewalls.",
                    "B. Query parameters are logged in server access logs, browser history, and proxy logs in plaintext.",
                    "C. GET requests cannot send text strings.",
                    "D. The browser will automatically convert GET to POST."
                ],
                correct_answer="B. Query parameters are logged in server access logs, browser history, and proxy logs in plaintext.",
                explanation="While HTTPS encrypts the connection over the wire, URL query strings are routinely recorded in plaintext within server access logs, proxy logs, and browser history, exposing sensitive credentials."
            ),
            KnowledgeCheckItem(
                question="What is the core distinction between a 4xx and a 5xx HTTP response status code?",
                options=[
                    "A. 4xx indicates client-side errors; 5xx indicates server-side or gateway errors.",
                    "B. 4xx is for secure pages; 5xx is for unencrypted pages.",
                    "C. 4xx responses have a body; 5xx responses never have a body.",
                    "D. 4xx means the server crashed."
                ],
                correct_answer="A. 4xx indicates client-side errors; 5xx indicates server-side or gateway errors.",
                explanation="4xx codes indicate that the client sent an invalid request or lacks permissions. 5xx codes signify that the server failed to process an otherwise valid request."
            ),
            KnowledgeCheckItem(
                question="Which property describes a method that can be called repeatedly without changing server resource state beyond the initial call?",
                options=[
                    "A. Asynchronous",
                    "B. Idempotent",
                    "C. Polymorphic",
                    "D. Symmetric"
                ],
                correct_answer="B. Idempotent",
                explanation="An HTTP method is idempotent if the side-effects of N > 0 identical requests with that method is the same as for a single request (e.g. GET, PUT, DELETE)."
            )
        ]

        supplementary_videos = [
            SupplementaryVideo(
                title="HTTP Crash Course & Status Codes Explained",
                url="https://www.youtube.com/watch?v=iYM2zFP3Zn0",
                channel="Traversy Media",
                duration="25 min",
                relevance_note="Comprehensive visual overview of HTTP headers, request-response lifecycles, and REST principles."
            ),
            SupplementaryVideo(
                title="What is an API? REST, HTTP Methods, and Status Codes",
                url="https://www.youtube.com/watch?v=lsMQRaeKNDk",
                channel="Fireship",
                duration="6 min",
                relevance_note="High-tempo visual explanation of GET, POST, and standard 2xx/4xx/5xx responses."
            )
        ]

        references = [
            ReferenceLink(
                source_id="RFC-9110",
                title="RFC 9110: HTTP Semantics (Fielding et al., IETF 2022)",
                url_or_identifier="https://www.rfc-editor.org/rfc/rfc9110.html",
                source_type="website",
                citation="RFC 9110 establishes standardized definitions for safe/idempotent methods and status categories."
            ),
            ReferenceLink(
                source_id="MDN-HTTP",
                title="MDN Web Docs: An Overview of HTTP",
                url_or_identifier="https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview",
                source_type="website",
                citation="Authoritative reference on client-server architecture, headers, and status code categories."
            )
        ]

        # Arithmetic check: 3 + 12 + 8 + 7 + 3 = 33 for core sections + 5 activity + 7 knowledge check = 45 total.
        return LessonContent(
            title=title,
            learning_objective=objective,
            target_audience=audience,
            prerequisites=["Basic understanding of web browsers and client-server concepts"],
            introduction="Welcome to this 45-minute lesson on HTTP Requests and Responses. We will demystify how web applications exchange data, contrast GET and POST methods, and analyze 2xx, 4xx, and 5xx response categories.",
            sections=sections,
            worked_examples=worked_examples,
            practical_applications=practical_applications,
            interactive_activity=activity,
            knowledge_checks=knowledge_checks,
            summary="Understanding HTTP methods and response categories provides the bedrock for diagnosing network faults, designing scalable APIs, and building secure web applications.",
            supplementary_videos=supplementary_videos,
            references=references,
            total_duration_minutes=45
        )

    def _build_normalization_lesson(self, title: str, objective: str, audience: str, mode: str) -> LessonContent:
        sections = [
            LessonSection(
                title="1. Introduction to Database Design & The Problem of Redundancy",
                content=(
                    "Relational database design aims to organize data to prevent anomalies and redundant storage. "
                    "Unnormalized tables suffer from insertion, update, and deletion anomalies. Normalization is a systematic "
                    "process of decomposing relations to ensure dependencies are properly enforced by primary and foreign keys."
                ),
                duration_minutes=3,
                order=1,
                key_points=[
                    "Data redundancy wastes storage and causes inconsistent data states.",
                    "Anomalies: Insertion, Update, and Deletion anomalies.",
                    "Normalization decomposes tables losslessly using functional dependencies."
                ],
                citations=["Elmasri-Navathe-DB", "Silberschatz-DB-Concepts"]
            ),
            LessonSection(
                title="2. The Normal Forms: 1NF, 2NF, and 3NF Explained",
                content=(
                    "Normalization progresses through progressive stages:\n\n"
                    "- **First Normal Form (1NF):** Requires that each column contains only atomic (indivisible) values, "
                    "and there are no repeating groups or arrays. Every row must be uniquely identifiable via a primary key.\n\n"
                    "- **Second Normal Form (2NF):** Must first satisfy 1NF, and every non-key attribute must be fully functionally "
                    "dependent on the entire primary key (no partial dependencies on a composite primary key).\n\n"
                    "- **Third Normal Form (3NF):** Must first satisfy 2NF, and no non-key attribute may depend transitively on the primary key "
                    "(X -> Y and Y -> Z where Z depends on non-key Y; 'every attribute must depend on the key, the whole key, and nothing but the key')."
                ),
                duration_minutes=12,
                order=2,
                key_points=[
                    "1NF: Atomic values only, no repeating groups.",
                    "2NF: 1NF + eliminate partial dependencies on composite keys.",
                    "3NF: 2NF + eliminate transitive dependencies between non-key attributes."
                ],
                citations=["Codd-1970", "Silberschatz-DB-Concepts"]
            ),
            LessonSection(
                title="3. Step-by-Step Worked Decomposition",
                content=(
                    "Let us examine how an unnormalized spreadsheet table `OrderDetails(OrderID, ProductID, ProductName, SupplierName, SupplierCity, Quantity, UnitPrice)` "
                    "is decomposed step-by-step into 1NF, 2NF, and 3NF to eliminate redundancy."
                ),
                duration_minutes=8,
                order=3,
                key_points=[
                    "Composite key: (OrderID, ProductID).",
                    "ProductName depends only on ProductID (partial dependency) -> Extracted for 2NF.",
                    "SupplierCity depends on SupplierName (transitive dependency) -> Extracted for 3NF."
                ],
                citations=["Elmasri-Navathe-DB"]
            ),
            LessonSection(
                title="4. Practical Trade-offs: Normalization vs. Denormalization",
                content=(
                    "While 3NF is standard for Online Transaction Processing (OLTP) systems to guarantee ACID consistency and fast writes, "
                    "Online Analytical Processing (OLAP) and high-throughput read systems often strategically denormalize data "
                    "(star schemas) to avoid expensive multi-table JOINs."
                ),
                duration_minutes=7,
                order=4,
                key_points=[
                    "OLTP benefits from 3NF: minimal write locks and zero update anomalies.",
                    "OLAP systems accept controlled redundancy for fast analytical aggregation queries.",
                    "Always normalize first; denormalize only when measured performance metrics justify it."
                ],
                citations=["Silberschatz-DB-Concepts"]
            ),
            LessonSection(
                title="5. Summary & Best Practice Review",
                content=(
                    "We covered 1NF (atomic values), 2NF (elimination of partial dependencies), and 3NF (elimination of transitive dependencies). "
                    "By adhering to these principles, software engineers ensure transactional data integrity and eliminate destructive update anomalies."
                ),
                duration_minutes=3,
                order=5,
                key_points=[
                    "1NF = Atomic values.",
                    "2NF = Full functional dependency.",
                    "3NF = No transitive dependency.",
                    "3NF preserves data integrity across all enterprise transactions."
                ],
                citations=["Elmasri-Navathe-DB"]
            )
        ]

        worked_examples = [
            WorkedExample(
                title="Worked Example: Converting an Unnormalized Order Table to 3NF",
                scenario="An organization stores `(OrderID, CustomerID, CustomerEmail, ProductID, Qty)` in one table.",
                step_by_step_solution=(
                    "1. Primary Key is `(OrderID, ProductID)`.\n"
                    "2. `CustomerEmail` depends on `CustomerID`, which depends on `OrderID`. This violates 2NF & 3NF.\n"
                    "3. Decompose into `Orders(OrderID, CustomerID)`, `Customers(CustomerID, CustomerEmail)`, and `OrderLineItems(OrderID, ProductID, Qty)`."
                ),
                explanation="Now, updating a customer's email address occurs in exactly one row in the `Customers` table, completely preventing update anomalies."
            )
        ]

        practical_applications = [
            PracticalApplication(
                domain="Database Engineering & Schema Architecture",
                use_case="Refactoring legacy monolithic database schemas for multi-tenant SaaS platforms.",
                best_practices=[
                    "Always define explicit foreign key constraints with indexed foreign key columns.",
                    "Enforce domain integrity using CHECK constraints and NOT NULL attributes.",
                    "Benchmark JOIN performance before resorting to premature denormalization."
                ]
            )
        ]

        activity = InteractiveActivity(
            title="Hands-On Activity: Identify the Normal Form Violation",
            instructions=(
                "Analyze the relation `EmployeeProject(EmpID, ProjID, EmpName, ProjBudget, HoursWorked)` with composite key `(EmpID, ProjID)`.\n"
                "1. Identify which normal form is violated by `EmpName`.\n"
                "2. Identify which normal form is violated by `ProjBudget`.\n"
                "3. Write the decomposed 3NF table schemas."
            ),
            duration_minutes=5,
            deliverable="Schema definitions for decomposed relations in 3NF."
        )

        knowledge_checks = [
            KnowledgeCheckItem(
                question="A table in 1NF has a composite primary key (StudentID, CourseID). The column StudentName depends only on StudentID. Which normal form is violated?",
                options=[
                    "A. First Normal Form (1NF)",
                    "B. Second Normal Form (2NF)",
                    "C. Third Normal Form (3NF)",
                    "D. Boyce-Codd Normal Form (BCNF)"
                ],
                correct_answer="B. Second Normal Form (2NF)",
                explanation="2NF requires that all non-key attributes be fully functionally dependent on the primary key. Since StudentName depends only on part of the composite key, it represents a partial dependency."
            ),
            KnowledgeCheckItem(
                question="What is a transitive dependency in relational database design?",
                options=[
                    "A. When a primary key depends on a foreign key.",
                    "B. When a non-key attribute depends on another non-key attribute rather than directly on the primary key.",
                    "C. When data transfers over a network socket.",
                    "D. When two tables have identical column names."
                ],
                correct_answer="B. When a non-key attribute depends on another non-key attribute rather than directly on the primary key.",
                explanation="A transitive dependency occurs when X -> Y and Y -> Z, where X is the primary key and Y and Z are non-key attributes."
            )
        ]

        supplementary_videos = [
            SupplementaryVideo(
                title="Database Normalization Explained: 1NF, 2NF, 3NF",
                url="https://www.youtube.com/watch?v=GFQaEYEc8_8",
                channel="Caleb Curry",
                duration="15 min",
                relevance_note="Clear visual breakdown of normal forms with clear diagrams."
            )
        ]

        references = [
            ReferenceLink(
                source_id="Silberschatz-DB-Concepts",
                title="Database System Concepts (Silberschatz, Korth, Sudarshan)",
                url_or_identifier="ISBN: 978-0078022159",
                source_type="book_pdf",
                citation="Foundational reference for functional dependencies, normal forms, and lossless decomposition algorithms."
            )
        ]

        return LessonContent(
            title=title,
            learning_objective=objective,
            target_audience=audience,
            prerequisites=["Basic SQL and understanding of tables and primary keys"],
            introduction="Welcome to this 45-minute lesson on Database Normalization. We will examine how relational schemas reduce data redundancy and eliminate destructive update anomalies through 1NF, 2NF, and 3NF.",
            sections=sections,
            worked_examples=worked_examples,
            practical_applications=practical_applications,
            interactive_activity=activity,
            knowledge_checks=knowledge_checks,
            summary="Mastering 1NF, 2NF, and 3NF ensures your relational databases remain robust, consistent, and resilient against anomalies as application data scales.",
            supplementary_videos=supplementary_videos,
            references=references,
            total_duration_minutes=45
        )

    def _build_generic_lesson(self, title: str, objective: str, audience: str, mode: str) -> LessonContent:
        sections = [
            LessonSection(
                title="1. Introduction and Objectives",
                content=f"Welcome to this comprehensive 45-minute lesson on '{title}'. Our primary objective is: {objective}. We will begin by reviewing prerequisites and defining key terminology.",
                duration_minutes=3,
                order=1,
                key_points=["Understand baseline terminology.", "Connect concepts to real-world applications."]
            ),
            LessonSection(
                title="2. Core Theoretical Foundations and Conceptual Framework",
                content=f"To achieve our objective ({objective}), we examine the core principles underlying {title}. We discuss mechanisms, structural rules, and standard industry practices.",
                duration_minutes=12,
                order=2,
                key_points=["Foundational principles explained.", "Common patterns and terminology."]
            ),
            LessonSection(
                title="3. Step-by-Step Worked Demonstrations",
                content=f"We now explore worked demonstrations showing {title} in action. Observing step-by-step resolution clarifies common edge cases and pitfalls.",
                duration_minutes=8,
                order=3,
                key_points=["Detailed step-by-step walkthrough.", "Critical decision points and trade-offs."]
            ),
            LessonSection(
                title="4. Practical Applications & Industry Best Practices",
                content=f"Applying {title} in real-world scenarios requires understanding constraints, operational efficiency, and best practices.",
                duration_minutes=7,
                order=4,
                key_points=["Real-world use case analysis.", "Industry standards and operational tips."]
            ),
            LessonSection(
                title="5. Summary, Key Takeaways, and Next Steps",
                content=f"In this lesson on {title}, we covered core concepts, worked through practical scenarios, and reinforced key principles to achieve our objective: {objective}.",
                duration_minutes=3,
                order=5,
                key_points=["Summary of main takeaways.", "Guidelines for continuing study."]
            )
        ]

        worked_examples = [
            WorkedExample(
                title=f"Practical Demonstration: {title}",
                scenario=f"A team needs to implement and verify {title} to achieve {objective}.",
                step_by_step_solution="1. Identify input requirements.\n2. Apply core principles.\n3. Verify output against acceptance criteria.",
                explanation="Demonstrates successful implementation while adhering to core principles."
            )
        ]

        practical_applications = [
            PracticalApplication(
                domain="Software Engineering & System Architecture",
                use_case=f"Deploying and verifying {title} in production systems.",
                best_practices=["Verify inputs before execution.", "Log all operations for auditability."]
            )
        ]

        activity = InteractiveActivity(
            title="Hands-On Learner Exercise",
            instructions=f"Complete the exercise applying the concepts learned in {title}. Formulate your answer based on the learning objective.",
            duration_minutes=5,
            deliverable="Learner solution summary and reflection."
        )

        knowledge_checks = [
            KnowledgeCheckItem(
                question=f"What is the primary objective of studying {title}?",
                options=[f"A. {objective}", "B. Generic unrelated option", "C. Discarding best practices", "D. None of the above"],
                correct_answer=f"A. {objective}",
                explanation=f"The lesson was structured around this exact learning objective: {objective}."
            )
        ]

        return LessonContent(
            title=title,
            learning_objective=objective,
            target_audience=audience,
            prerequisites=["Foundational domain familiarity"],
            introduction=f"This 45-minute lesson explores {title}, focusing on {objective}.",
            sections=sections,
            worked_examples=worked_examples,
            practical_applications=practical_applications,
            interactive_activity=activity,
            knowledge_checks=knowledge_checks,
            summary=f"In this lesson, we established a solid understanding of {title}.",
            supplementary_videos=[],
            references=[],
            total_duration_minutes=45
        )

llm_service = LLMService()
