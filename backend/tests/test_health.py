def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_name" in data
    assert "environment" in data

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    # Returns HTML dashboard or JSON API info
    assert "AI Lesson Creation" in response.text or "AI-Powered Lesson Creation" in response.text
