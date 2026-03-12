"""Basic smoke tests for the API service."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with a minimal env so the app can import."""
    import os

    os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
    os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
    os.environ.setdefault("JWT_SECRET", "test-secret")

    from src.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_forecast_run_no_model(client):
    """Forecast endpoint returns mocked data when no model is present."""
    resp = client.post(
        "/forecast/run",
        json={"store_id": "S01", "product_id": "P001", "horizon_days": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["store_id"] == "S01"
    assert len(data["predictions"]) == 5
