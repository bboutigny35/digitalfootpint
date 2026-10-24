from app.connectors.base import Connector


class ConnectorRegistry:
    def __init__(self, connectors: list[Connector] | None = None) -> None:
        self._connectors = {item.metadata.identifier: item for item in connectors or []}

    def get(self, identifier: str) -> Connector:
        try:
            return self._connectors[identifier]
        except KeyError as exc:
            raise LookupError(f"Connecteur inconnu: {identifier}") from exc

    def identifiers(self) -> tuple[str, ...]:
        return tuple(sorted(self._connectors))

    def all(self) -> tuple[Connector, ...]:
        return tuple(self._connectors[key] for key in sorted(self._connectors))
