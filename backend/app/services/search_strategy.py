from dataclasses import dataclass
from enum import StrEnum

from app.models.entities import IdentityProfile


class SearchMode(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class QueryScope(StrEnum):
    LOCAL = "local"
    SPECIALIZED = "specialized"
    GENERAL = "general"


@dataclass(frozen=True, slots=True)
class PlannedQuery:
    text: str
    kind: str
    priority: int
    scope: QueryScope
    criteria: tuple[str, ...]
    requires_corroboration: bool = False


@dataclass(frozen=True, slots=True)
class SearchPlan:
    mode: SearchMode
    queries: tuple[PlannedQuery, ...]
    budget: int
    truncated: bool
    stages: tuple[str, ...]


MODE_BUDGETS = {
    SearchMode.QUICK: 8,
    SearchMode.STANDARD: 16,
    SearchMode.DEEP: 30,
}

MODE_STAGES = {
    SearchMode.QUICK: ("local_index", "fresh_cache"),
    SearchMode.STANDARD: (
        "local_index",
        "fresh_cache",
        "priority_connectors",
        "targeted_discovery",
    ),
    SearchMode.DEEP: (
        "local_index",
        "fresh_cache",
        "all_enabled_connectors",
        "progressive_discovery",
        "identity_correlation",
    ),
}


def _quoted(value: str) -> str:
    return f'"{value.strip()}"'


def _clean(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _candidate_queries(profile: IdentityProfile, mode: SearchMode) -> list[PlannedQuery]:
    first_name = profile.first_name.strip()
    last_name = profile.last_name.strip()
    full_name = " ".join(value for value in (first_name, last_name) if value)
    names = _clean(([full_name] if full_name else []) + profile.name_variants)
    pseudonyms = _clean(profile.pseudonyms)
    domains = _clean(profile.domains)
    keywords = _clean(profile.keywords)
    queries: list[PlannedQuery] = []

    for email in _clean(profile.emails):
        queries.append(
            PlannedQuery(
                text=email.casefold(),
                kind="exact_email",
                priority=100,
                scope=QueryScope.LOCAL,
                criteria=("email",),
            )
        )
    for pseudonym in pseudonyms:
        queries.append(
            PlannedQuery(
                text=_quoted(pseudonym),
                kind="exact_pseudonym",
                priority=95,
                scope=QueryScope.SPECIALIZED,
                criteria=("pseudonym",),
            )
        )
        for domain in domains[:2]:
            queries.append(
                PlannedQuery(
                    text=f"{_quoted(pseudonym)} site:{domain.casefold()}",
                    kind="pseudonym_domain",
                    priority=98,
                    scope=QueryScope.GENERAL,
                    criteria=("pseudonym", "domain"),
                )
            )
    for name in names:
        for keyword in keywords[:3]:
            queries.append(
                PlannedQuery(
                    text=f"{_quoted(name)} {_quoted(keyword)}",
                    kind="name_keyword",
                    priority=85,
                    scope=QueryScope.GENERAL,
                    criteria=("name", "keyword"),
                )
            )
        for domain in domains[:2]:
            queries.append(
                PlannedQuery(
                    text=f"{_quoted(name)} site:{domain.casefold()}",
                    kind="name_domain",
                    priority=90,
                    scope=QueryScope.GENERAL,
                    criteria=("name", "domain"),
                )
            )
        queries.append(
            PlannedQuery(
                text=_quoted(name),
                kind="name_only",
                priority=40,
                scope=QueryScope.GENERAL,
                criteria=("name",),
                requires_corroboration=True,
            )
        )

    if mode is SearchMode.DEEP:
        for pseudonym in pseudonyms:
            for keyword in keywords[:3]:
                queries.append(
                    PlannedQuery(
                        text=f"{_quoted(pseudonym)} {_quoted(keyword)}",
                        kind="pseudonym_keyword",
                        priority=80,
                        scope=QueryScope.GENERAL,
                        criteria=("pseudonym", "keyword"),
                    )
                )
    return queries


def build_search_plan(profile: IdentityProfile, mode: SearchMode) -> SearchPlan:
    candidates = _candidate_queries(profile, mode)
    if mode is SearchMode.QUICK:
        candidates = [query for query in candidates if query.scope is QueryScope.LOCAL]
    elif mode is SearchMode.STANDARD:
        candidates = [query for query in candidates if query.kind != "name_only"]

    unique: dict[tuple[str, QueryScope], PlannedQuery] = {}
    for query in candidates:
        key = (query.text.casefold(), query.scope)
        current = unique.get(key)
        if current is None or query.priority > current.priority:
            unique[key] = query
    ordered = sorted(unique.values(), key=lambda item: (-item.priority, item.kind, item.text))
    budget = MODE_BUDGETS[mode]
    return SearchPlan(
        mode=mode,
        queries=tuple(ordered[:budget]),
        budget=budget,
        truncated=len(ordered) > budget,
        stages=MODE_STAGES[mode],
    )
