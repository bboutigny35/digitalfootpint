from fastapi.testclient import TestClient

from app.models.entities import IdentityProfile
from app.services.search_strategy import QueryScope, SearchMode, build_search_plan


def profile(**overrides: object) -> IdentityProfile:
    values: dict[str, object] = {
        "owner_id": "owner",
        "first_name": "Alice",
        "last_name": "Martin",
        "name_variants": ["Alice Martin", "  Alice Martin  "],
        "pseudonyms": ["alice_dev", "alice_dev"],
        "emails": ["Alice@example.com"],
        "domains": ["Example.com"],
        "websites": [],
        "social_profiles": [],
        "keywords": ["Lyon", "Engineering"],
    }
    values.update(overrides)
    return IdentityProfile(**values)


def test_standard_plan_is_prioritized_deduplicated_and_bounded() -> None:
    plan = build_search_plan(profile(), SearchMode.STANDARD)
    assert plan.budget == 16
    assert plan.stages[0] == "local_index"
    assert len({(query.text.casefold(), query.scope) for query in plan.queries}) == len(
        plan.queries
    )
    assert [query.priority for query in plan.queries] == sorted(
        (query.priority for query in plan.queries), reverse=True
    )
    assert all(query.kind != "name_only" for query in plan.queries)


def test_email_never_targets_a_general_search_engine() -> None:
    for mode in SearchMode:
        plan = build_search_plan(profile(), mode)
        email_queries = [query for query in plan.queries if query.kind == "exact_email"]
        assert email_queries
        assert all(query.scope is QueryScope.LOCAL for query in email_queries)


def test_name_only_requires_corroboration_and_is_deep_only() -> None:
    name_only = profile(keywords=[], domains=[], emails=[], pseudonyms=[])
    standard = build_search_plan(name_only, SearchMode.STANDARD)
    deep = build_search_plan(name_only, SearchMode.DEEP)
    assert not standard.queries
    assert len(deep.queries) == 1
    assert deep.queries[0].kind == "name_only"
    assert deep.queries[0].requires_corroboration is True


def test_quick_mode_uses_only_local_queries() -> None:
    plan = build_search_plan(profile(), SearchMode.QUICK)
    assert plan.stages == ("local_index", "fresh_cache")
    assert plan.queries
    assert all(query.scope is QueryScope.LOCAL for query in plan.queries)


def test_strategy_preview_is_private(authenticated: tuple[TestClient, str]) -> None:
    client, csrf = authenticated
    created = client.post(
        "/api/v1/profiles",
        json={
            "first_name": "Alice",
            "last_name": "Martin",
            "pseudonyms": ["alice_dev"],
            "emails": ["alice@example.com"],
            "domains": ["example.com"],
            "keywords": ["Lyon"],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    profile_id = created.json()["id"]
    response = client.get(f"/api/v1/profiles/{profile_id}/search-strategy?mode=standard")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "standard"
    assert body["queries"][0]["kind"] == "exact_email"
    assert any(query["kind"] == "pseudonym_domain" for query in body["queries"])
    assert client.get("/api/v1/profiles/unknown/search-strategy").status_code == 404
