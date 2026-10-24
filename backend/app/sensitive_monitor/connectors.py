from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.sensitive_monitor.types import SensitiveCategory


@dataclass(frozen=True, slots=True)
class SensitiveProviderMetadata:
    identifier: str
    version: str
    categories: tuple[SensitiveCategory, ...]
    external_transmission: bool
    requires_explicit_confirmation: bool = True


@dataclass(frozen=True, slots=True)
class LocalMatchCandidate:
    fingerprint: str
    source_label: str


class SensitiveProvider(ABC):
    metadata: SensitiveProviderMetadata

    @abstractmethod
    async def check_local(self, candidate: LocalMatchCandidate) -> bool:
        """Compare localement une empreinte à une source autorisée."""
