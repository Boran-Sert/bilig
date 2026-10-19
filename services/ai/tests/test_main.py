"""HTTP uygulamasının temel uç noktalarını test eder."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_no_content() -> None:
    """Sağlık kontrolü 204 ve boş gövde döner."""
    response = TestClient(app).get("/internal/health")

    assert response.status_code == 204
    assert response.content == b""
