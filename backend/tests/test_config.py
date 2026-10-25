import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_csv_lists_are_accepted(monkeypatch: object) -> None:
    monkeypatch.setenv("DIGITALFOOTPRINT_ALLOWED_HOSTS", "localhost,127.0.0.1")  # type: ignore[attr-defined]
    monkeypatch.setenv(  # type: ignore[attr-defined]
        "DIGITALFOOTPRINT_CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
    )
    settings = Settings(_env_file=None)
    assert settings.allowed_hosts == ["localhost", "127.0.0.1"]
    assert settings.cors_origins == ["http://127.0.0.1:5173", "http://localhost:5173"]


def test_example_secret_is_rejected_in_production(monkeypatch: object) -> None:
    monkeypatch.setenv("DIGITALFOOTPRINT_ENVIRONMENT", "production")  # type: ignore[attr-defined]
    monkeypatch.setenv(  # type: ignore[attr-defined]
        "DIGITALFOOTPRINT_SECRET_KEY", "replace-with-at-least-32-random-characters"
    )
    with pytest.raises(ValidationError, match="doit être remplacée"):
        Settings(_env_file=None)


def test_searxng_endpoint_is_restricted_to_supported_local_origins() -> None:
    assert Settings(_env_file=None).searxng_url is None
    assert Settings(_env_file=None, searxng_url="").searxng_url is None
    assert (
        Settings(_env_file=None, searxng_url="http://127.0.0.1:8888/search").searxng_url
        == "http://127.0.0.1:8888/search"
    )
    with pytest.raises(ValidationError, match="instance SearXNG locale"):
        Settings(_env_file=None, searxng_url="http://169.254.169.254/latest")


def test_brave_contract_requires_explicit_operator_approval() -> None:
    assert Settings(_env_file=None).brave_contract_approved is False
    assert Settings(_env_file=None, brave_contract_approved=True).brave_contract_approved is True
