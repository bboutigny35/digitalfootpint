from fastapi.testclient import TestClient


def test_liveness(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
