from fastapi.testclient import TestClient


def test_liveness(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}


def test_openapi_exposes_semantic_version(client: TestClient) -> None:
    assert client.get("/openapi.json").json()["info"]["version"] == "0.1.0-dev.0"
