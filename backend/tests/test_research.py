from unittest.mock import patch
from app.research.query_generator import generate_research_queries
from app.research.source_evaluator import evaluate_and_rank_source
from app.research.page_extractor import clean_and_extract_page

def test_generate_research_queries():
    queries = generate_research_queries(
        title="HTTP Requests and Responses",
        learning_objective="Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
    )
    assert len(queries) >= 3
    query_text = " ".join(queries).lower()
    assert "get" in query_text
    assert "post" in query_text
    assert "status" in query_text

def test_source_evaluator_authority_and_coverage():
    # Test Tier 1 primary standard
    eval_tier1 = evaluate_and_rank_source(
        url="https://www.rfc-editor.org/rfc/rfc9110.html",
        title="RFC 9110: HTTP Semantics",
        full_text="This document specifies HTTP methods GET and POST, safe and idempotent properties, and 2xx 4xx 5xx status codes.",
        learning_objective="Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
    )
    assert eval_tier1["relevance_score"] >= 0.80
    assert "Tier 1" in eval_tier1["evaluation_notes"]["authority_tier"]
    assert eval_tier1["evaluation_notes"]["concept_coverage_percent"] > 50

    # Test lower tier source
    eval_gen = evaluate_and_rank_source(
        url="https://some-personal-blog.com/post1",
        title="A Quick HTTP Note",
        full_text="Here is a quick blog post about web requests.",
        learning_objective="Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
    )
    assert eval_gen["relevance_score"] < eval_tier1["relevance_score"]
    assert "Tier 4" in eval_gen["evaluation_notes"]["authority_tier"]

def test_clean_and_extract_page():
    raw_html = """
    <html>
        <head>
            <title>HTTP Methods Overview</title>
            <meta property="og:site_name" content="MDN Web Docs" />
            <meta property="article:published_time" content="2024-03-01T12:00:00Z" />
        </head>
        <body>
            <nav><a href="/home">Home</a></nav>
            <script>console.log('tracking');</script>
            <h1>Understanding GET and POST</h1>
            <p>The GET method requests a representation of the specified resource. Requests using GET should only retrieve data.</p>
            <p>The POST method submits an entity to the specified resource, often causing a change in state or side effects on the server.</p>
            <footer><p>Copyright 2024 All rights reserved.</p></footer>
        </body>
    </html>
    """
    extracted = clean_and_extract_page(raw_html, "https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods")
    assert extracted["title"] == "HTTP Methods Overview"
    assert extracted["publisher"] == "MDN Web Docs"
    assert extracted["published_date"] == "2024-03-01"
    assert "tracking" not in extracted["full_text"]
    assert "Home" not in extracted["full_text"]
    assert "GET method requests a representation" in extracted["full_text"]
    assert len(extracted["chunks"]) >= 1

def test_research_api_lifecycle(client):
    """Integration test for POST /api/lessons/{id}/research and package retrieval."""
    # 1. Create draft lesson
    create_resp = client.post(
        "/api/lessons",
        json={
            "title": "HTTP Requests and Responses",
            "learning_objective": "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
        }
    )
    assert create_resp.status_code == 201
    lesson_id = create_resp.json()["id"]

    # Mock fetch_page_html to simulate fast offline responses for deterministic testing
    mock_html = """
    <html>
        <head><title>MDN HTTP Protocol Documentation</title><meta property="og:site_name" content="MDN"/></head>
        <body>
            <h1>HTTP Methods and Statuses</h1>
            <p>GET is safe and idempotent. POST creates resources with body payloads. 2xx indicates success, 4xx client errors like 404, and 5xx server errors like 500.</p>
        </body>
    </html>
    """
    with patch("app.research.web_research.fetch_page_html", return_value=mock_html):
        # 2. Run research
        research_resp = client.post(f"/api/lessons/{lesson_id}/research")
        assert research_resp.status_code == 200
        sources_data = research_resp.json()
        assert sources_data["total"] >= 1
        assert len(sources_data["items"]) >= 1

        first_source = sources_data["items"][0]
        assert first_source["source_type"] == "website"
        assert first_source["relevance_score"] > 0
        assert len(first_source["chunks"]) >= 1

        # 3. Verify lesson status is now research_completed
        lesson_resp = client.get(f"/api/lessons/{lesson_id}")
        assert lesson_resp.json()["status"] == "research_completed"

        # 4. List sources endpoint
        sources_list_resp = client.get(f"/api/lessons/{lesson_id}/sources")
        assert sources_list_resp.status_code == 200
        assert sources_list_resp.json()["total"] == sources_data["total"]

        # 5. Get research package
        pkg_resp = client.get(f"/api/lessons/{lesson_id}/research/package")
        assert pkg_resp.status_code == 200
        pkg = pkg_resp.json()
        assert pkg["lesson_id"] == lesson_id
        assert len(pkg["web_excerpts"]) >= 1

        # 6. Retry research (should refresh cleanly without error)
        retry_resp = client.post(f"/api/lessons/{lesson_id}/research")
        assert retry_resp.status_code == 200
        assert retry_resp.json()["total"] >= 1
