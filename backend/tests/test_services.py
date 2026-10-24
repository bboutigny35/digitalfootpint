from app.models.entities import IdentityProfile
from app.services.correlation import (
    _assess_context,
    _controlled_approximate_name,
    score_attribution,
    score_signals,
)
from app.services.normalization import canonicalize_url, fold_text, normalize_phone, normalize_text


def test_canonical_url_removes_tracking_and_fragment() -> None:
    assert (
        canonicalize_url("HTTPS://Example.COM:443/path?utm_source=x&b=2&a=1#section")
        == "https://example.com/path?a=1&b=2"
    )


def test_correlation_is_deterministic_and_explainable() -> None:
    score = score_signals({"exact_pseudonym": True, "known_domain": True, "unknown": True})
    assert score.value == 0.45
    assert score.explanation["matched_signals"] == ["exact_pseudonym", "known_domain"]
    assert "pas une preuve" in str(score.explanation["warning"])


def test_identity_text_and_phone_normalization() -> None:
    assert normalize_text("  Alice\u00a0  Martin ") == "Alice Martin"
    assert fold_text("Élodie-Dupré") == "elodie-dupre"
    assert normalize_phone("+33 (0) 6 12 34 56 78") == "+330612345678"
    assert normalize_phone("06 12 34 56 78") == "0612345678"


def test_attribution_score_separates_identity_confidence_and_contradictions() -> None:
    name_only = score_attribution({"exact_name": True}, [])
    corroborated = score_attribution(
        {"exact_name": True, "known_domain": True, "employer": True}, []
    )
    contradicted = score_attribution(
        {"exact_name": True, "known_domain": True, "employer": True}, ["location"]
    )
    assert name_only.value <= 0.25
    assert corroborated.value > name_only.value
    assert contradicted.value < corroborated.value
    assert "pas une probabilité" in str(contradicted.explanation["warning"])


def test_context_flags_name_only_and_non_person_page() -> None:
    assessment = _assess_context(
        "alice martin est le nom d'une rue de cette commune et de sa mairie",
        {"exact_name": True},
    )
    assert assessment.page_classification == "place_or_street"
    assert assessment.risk_flags == (
        "name_only",
        "non_person_context:place_or_street",
        "possible_homonym",
    )


def test_approximate_name_requires_a_corroborating_signal() -> None:
    profile = IdentityProfile(
        owner_id="owner",
        first_name="Alice",
        last_name="Martin",
    )
    text = "public profile for alyce martin, also known as processfox"
    assert _controlled_approximate_name(profile, text, {}) is None
    matched = _controlled_approximate_name(profile, text, {"exact_pseudonym": True})
    assert matched is not None
    assert matched.signal == "approximate_name"
    assert matched.match_kind == "controlled_approximate_text"
