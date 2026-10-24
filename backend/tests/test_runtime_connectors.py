from app.connectors.runtime import build_runtime_registry
from app.core.config import Settings


def test_mock_connector_is_available_only_in_test_environment() -> None:
    test_registry = build_runtime_registry(Settings(environment="test"))
    development_registry = build_runtime_registry(Settings(environment="development"))
    production_registry = build_runtime_registry(
        Settings(
            environment="production",
            secret_key="production-synthetic-secret-at-least-32-characters",  # noqa: S106
        )
    )

    assert "mock" in test_registry.identifiers()
    assert {"brave", "github", "gitlab", "wayback"}.issubset(
        test_registry.identifiers()
    )
    assert "mock" not in development_registry.identifiers()
    assert "mock" not in production_registry.identifiers()
    assert {"brave", "gitlab", "wayback"}.issubset(production_registry.identifiers())
