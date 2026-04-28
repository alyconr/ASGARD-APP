"""CORS tests for browser-driven frontend requests."""

from fastapi.testclient import TestClient

from src.interfaces.http.app import app


def test_program_pdf_upload_preflight_allows_local_frontend() -> None:
    """The PDF upload route must answer browser preflight requests."""
    client = TestClient(app)

    response = client.options(
        "/api/v1/programas/00000000-0000-4000-8000-000000000000/documentos/programa-pdf",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_health_response_allows_127_frontend_origin() -> None:
    """Localhost and 127.0.0.1 frontend URLs should both be accepted."""
    client = TestClient(app)

    response = client.get(
        "/api/v1/health",
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://127.0.0.1:3000"
    )
