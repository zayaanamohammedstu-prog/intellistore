"""Smoke tests for the ETL service."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    import os

    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_etl.db")

    from src.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
