from fastapi.testclient import TestClient

from merit_assistant.api.main import app


def test_health_endpoint_disables_external_processing() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "external_processing_enabled": False,
    }
