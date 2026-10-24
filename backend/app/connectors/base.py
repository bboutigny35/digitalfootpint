from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class IdentifierType(StrEnum):
    NAME = "name"
    PSEUDONYM = "pseudonym"
    EMAIL = "email"
    DOMAIN = "domain"


@dataclass(frozen=True, slots=True)
class ConnectorMetadata:
    identifier: str
    version: str
    capabilities: tuple[str, ...]
    accepted_identifiers: tuple[IdentifierType, ...]
    requires_api_key: bool = False
    rate_limit_per_minute: int | None = None
    crawl_results: bool = False


@dataclass(frozen=True, slots=True)
class IdentitySnapshot:
    first_name: str
    last_name: str
    name_variants: tuple[str, ...] = ()
    pseudonyms: tuple[str, ...] = ()
    former_pseudonyms: tuple[str, ...] = ()
    emails: tuple[str, ...] = ()
    phone_numbers: tuple[str, ...] = ()
    city_region: str | None = None
    profession: str | None = None
    employers: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    websites: tuple[str, ...] = ()
    confirmed_profiles: tuple[str, ...] = ()
    exact_phrases: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateResult:
    url: str
    title: str
    snippet: str
    match_type: str
    published_at: str | None = None
    signals: dict[str, bool] = field(default_factory=dict)


class Connector(ABC):
    metadata: ConnectorMetadata

    @abstractmethod
    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        """Retourne uniquement des candidats provenant réellement du fournisseur."""
