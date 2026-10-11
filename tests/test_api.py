"""Small API smoke tests that do not run audio models."""

from fastapi.testclient import TestClient

from studio_api import app


def test_local_studio_shell() -> None:
    client = TestClient(app)

    index = client.get("/")
    assert index.status_code == 200
    assert "My Singing Voice Studio" in index.text

    status = client.get("/api/system")
    assert status.status_code == 200
    assert status.json()["local_only"] is True


def test_persistent_collections_are_available() -> None:
    client = TestClient(app)

    assert client.get("/api/profiles").status_code == 200
    assert client.get("/api/jobs").status_code == 200
