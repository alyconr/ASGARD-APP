"""Smoke tests for the backend health endpoint."""

from fastapi.testclient import TestClient

from src.interfaces.http.app import app


def test_health_endpoint_returns_ok() -> None:
    """Ensure the base backend responds correctly."""
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
