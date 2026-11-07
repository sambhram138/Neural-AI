import pytest

def test_create_lesson_validation_empty_title(client):
    """AC1: Empty title or objective must return 422 Unprocessable Entity."""
    response = client.post(
        "/api/lessons",
        json={"title": "   ", "learning_objective": "Explain GET and POST methods"}
    )
    assert response.status_code == 422
    assert "detail" in response.json()

def test_create_lesson_validation_empty_objective(client):
    """AC1: Empty objective must return 422."""
    response = client.post(
        "/api/lessons",
        json={"title": "HTTP Requests and Responses", "learning_objective": "   "}
    )
    assert response.status_code == 422

def test_create_lesson_success(client):
    """AC2: Creating a valid lesson draft creates a persistent record with status 'draft'."""
    payload = {
        "title": "HTTP Requests and Responses",
        "learning_objective": "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.",
        "audience": "Undergraduate Computer Science",
        "teaching_mode": "self-learning",
        "additional_instructions": "Focus on real-world REST examples and status code meanings."
    }
    response = client.post("/api/lessons", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == payload["title"]
    assert data["learning_objective"] == payload["learning_objective"]
    assert data["status"] == "draft"
    assert data["current_version_id"] is None

def test_get_and_list_lessons(client):
    """Test retrieving created lesson by ID and listing lessons."""
    # Create draft
    create_resp = client.post(
        "/api/lessons",
        json={
            "title": "Database Normalization",
            "learning_objective": "Explain 1NF, 2NF, and 3NF and identify how normalization reduces data redundancy and update anomalies."
        }
    )
    assert create_resp.status_code == 201
    lesson_id = create_resp.json()["id"]

    # Get by ID
    get_resp = client.get(f"/api/lessons/{lesson_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == lesson_id

    # List lessons
    list_resp = client.get("/api/lessons")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == lesson_id for item in list_data["items"])

def test_generate_lesson_http_45_min_validation(client):
    """AC3 & AC4: Basic generation generates structured lesson strictly totaling 45 minutes."""
    # Create draft
    create_resp = client.post(
        "/api/lessons",
        json={
            "title": "HTTP Requests and Responses",
            "learning_objective": "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."
        }
    )
    lesson_id = create_resp.json()["id"]

    # Generate lesson
    gen_resp = client.post(f"/api/lessons/{lesson_id}/generate")
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()

    assert gen_data["status"] == "generated"
    assert gen_data["current_version_id"] is not None
    version = gen_data["current_version"]
    assert version is not None
    assert version["total_duration_minutes"] == 45

    content = version["content"]
    assert "sections" in content
    assert len(content["sections"]) >= 4

    # Verify time duration calculation
    section_sum = sum(s["duration_minutes"] for s in content["sections"])
    activity_mins = content["interactive_activity"]["duration_minutes"]
    # 5 sections = 3 + 12 + 8 + 7 + 3 = 33 + 5 activity + 7 knowledge check = 45
    assert content["total_duration_minutes"] == 45
    assert (section_sum + activity_mins + 7) == 45

    # Verify worked examples, activities, and knowledge checks
    assert len(content["worked_examples"]) >= 1
    assert content["interactive_activity"]["title"] is not None
    assert len(content["knowledge_checks"]) >= 2
    assert len(content["references"]) >= 1

def test_generate_lesson_database_normalization(client):
    """Test generation for Database Normalization."""
    create_resp = client.post(
        "/api/lessons",
        json={
            "title": "Database Normalization",
            "learning_objective": "Explain 1NF, 2NF, and 3NF and identify how normalization reduces data redundancy and update anomalies."
        }
    )
    lesson_id = create_resp.json()["id"]

    gen_resp = client.post(f"/api/lessons/{lesson_id}/generate")
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert data["status"] == "generated"
    assert data["current_version"]["total_duration_minutes"] == 45
