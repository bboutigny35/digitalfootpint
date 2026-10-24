import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    CrawlResult,
    DiscoveredURL,
    Evidence,
    EvidenceMatch,
    IdentityCorrelation,
    IdentityProfile,
    Result,
    Scan,
    UserValidation,
    VerificationStatus,
)
from app.services.normalization import canonicalize_url, fold_text


@dataclass(frozen=True, slots=True)
class Score:
    value: float
    explanation: dict[str, object]


WEIGHTS: dict[str, float] = {
    "exact_name": 0.35,
    "exact_pseudonym": 0.20,
    "known_domain": 0.25,
    "context_keyword": 0.10,
    "known_profile_url": 0.45,
}


def score_signals(signals: dict[str, bool]) -> Score:
    matched = sorted(key for key, matched in signals.items() if matched and key in WEIGHTS)
    value = min(sum(WEIGHTS[key] for key in matched), 1.0)
    return Score(
        value=round(value, 4),
        explanation={
            "method": "weighted-signals-v1",
            "matched_signals": matched,
            "weights": {key: WEIGHTS[key] for key in matched},
            "warning": "Ce score est un indice, pas une preuve d'identité.",
        },
    )


ATTRIBUTION_WEIGHTS: dict[str, float] = {
    "exact_name": 0.15,
    "exact_pseudonym": 0.25,
    "public_email": 0.35,
    "location": 0.10,
    "profession": 0.10,
    "employer": 0.15,
    "known_domain": 0.25,
    "known_profile_url": 0.45,
    "cross_profile_link": 0.20,
    "approximate_name": 0.08,
}


def score_attribution(signals: dict[str, bool], contradictions: list[str]) -> Score:
    matched = sorted(key for key, value in signals.items() if value and key in ATTRIBUTION_WEIGHTS)
    raw = sum(ATTRIBUTION_WEIGHTS[key] for key in matched)
    if matched == ["exact_name"]:
        raw = min(raw, 0.25)
    penalty = min(len(set(contradictions)) * 0.20, 0.60)
    value = max(0.0, min(raw - penalty, 1.0))
    return Score(
        value=round(value, 4),
        explanation={
            "method": "identity-attribution-signals-v1",
            "matched_signals": matched,
            "weights": {key: ATTRIBUTION_WEIGHTS[key] for key in matched},
            "contradictions": sorted(set(contradictions)),
            "contradiction_penalty": penalty,
            "warning": "Indice heuristique explicable, pas une probabilité statistique.",
        },
    )


ANALYZER_METHOD = "identity-evidence-v2"
MAX_EVIDENCE_EXCERPT_CHARS = 500
MAX_CONTEXT_TEXT_CHARS = 20_000
MAX_CONTEXT_TOKENS = 2_000
APPROXIMATE_NAME_THRESHOLD = 0.90


@dataclass(frozen=True, slots=True)
class _Criterion:
    criterion_type: str
    value: str
    signal: str
    match_kind: str = "exact_text"


@dataclass(frozen=True, slots=True)
class _ContextAssessment:
    page_classification: str
    risk_flags: tuple[str, ...]


def analyze_crawl_evidence(
    db: Session,
    *,
    scan: Scan,
    discovered: DiscoveredURL,
    crawl_result: CrawlResult,
) -> IdentityCorrelation | None:
    """Create minimized evidence for a connector result's root page.

    A secondary page is deliberately not attributed to the connector result merely
    because it was linked from it. The caller owns the surrounding transaction.
    """
    if not discovered.discovery_method.startswith("connector:") or discovered.depth != 0:
        return None
    result = db.scalar(
        select(Result).where(
            Result.scan_id == scan.id,
            Result.canonical_url == discovered.canonical_url,
        )
    )
    if result is None or result.owner_id != scan.owner_id:
        return None
    existing = db.scalar(
        select(IdentityCorrelation).where(IdentityCorrelation.result_id == result.id)
    )
    if existing is not None:
        return existing
    profile = db.get(IdentityProfile, scan.profile_id)
    text = crawl_result.extracted_text or ""
    if profile is None:
        return None

    folded_text = fold_text(text)
    criteria = _profile_criteria(profile)
    matches = [criterion for criterion in criteria if _contains(folded_text, criterion.value)]
    signals = {criterion.signal: True for criterion in matches}
    url_signals, url_matches = _url_criteria(profile, result.canonical_url, result.domain)
    signals.update(url_signals)
    matches.extend(url_matches)
    approximate = _controlled_approximate_name(profile, folded_text, signals)
    if approximate is not None:
        signals[approximate.signal] = True
        matches.append(approximate)
    contradictions = (
        ["profile_exclusion"]
        if any(_contains(folded_text, value) for value in profile.exclusions)
        else []
    )
    if not matches and not contradictions:
        return None

    excerpt = _excerpt_around_first_match(text, matches)
    source_hash = crawl_result.content_hash or hashlib.sha256(
        crawl_result.final_url.encode()
    ).hexdigest()
    duplicate_evidence_id = db.scalar(
        select(Evidence.id)
        .where(
            Evidence.owner_id == scan.owner_id,
            Evidence.source_hash == source_hash,
        )
        .order_by(Evidence.observed_at.asc(), Evidence.id.asc())
        .limit(1)
    )
    evidence = Evidence(
        owner_id=scan.owner_id,
        scan_id=scan.id,
        result_id=result.id,
        crawl_result_id=crawl_result.id,
        evidence_type="identity_criteria",
        excerpt=excerpt,
        source_url=crawl_result.final_url,
        source_hash=source_hash,
        provenance={
            "method": ANALYZER_METHOD,
            "discovery_method": discovered.discovery_method,
            "match_count": len(matches),
            "duplicate_source": duplicate_evidence_id is not None,
            "duplicate_of_evidence_id": duplicate_evidence_id,
        },
        observed_at=crawl_result.fetched_at,
    )
    db.add(evidence)
    db.flush()
    for criterion in _deduplicate_criteria(matches):
        db.add(
            EvidenceMatch(
                evidence_id=evidence.id,
                criterion_type=criterion.criterion_type,
                criterion_hash=_criterion_hash(scan.owner_id, criterion),
                match_kind=criterion.match_kind,
                weight=ATTRIBUTION_WEIGHTS[criterion.signal],
                explanation=_criterion_explanation(criterion),
            )
        )

    attribution = score_attribution(signals, contradictions)
    context = _assess_context(folded_text, signals)
    correlation = IdentityCorrelation(
        owner_id=scan.owner_id,
        result_id=result.id,
        relevance_score=result.relevance_score,
        attribution_score=attribution.value,
        explanation={
            **attribution.explanation,
            "analyzer_method": ANALYZER_METHOD,
            "attribution_scope": "connector_result_root_only",
            "page_classification": context.page_classification,
            "risk_flags": list(context.risk_flags),
        },
        contradictions=contradictions,
        evidence_count=0 if duplicate_evidence_id else 1,
    )
    db.add(correlation)
    db.flush()
    _reuse_prior_validation(db, result, correlation)
    return correlation


def _profile_criteria(profile: IdentityProfile) -> list[_Criterion]:
    full_name = f"{profile.first_name} {profile.last_name}".strip()
    values: list[_Criterion] = []
    values.extend(
        _Criterion("name", item, "exact_name")
        for item in [full_name, *profile.name_variants]
    )
    values.extend(
        _Criterion("pseudonym", item, "exact_pseudonym")
        for item in [*profile.pseudonyms, *profile.former_pseudonyms]
    )
    values.extend(_Criterion("email", item, "public_email") for item in profile.emails)
    if profile.city_region:
        values.append(_Criterion("location", profile.city_region, "location"))
    if profile.profession:
        values.append(_Criterion("profession", profile.profession, "profession"))
    values.extend(_Criterion("employer", item, "employer") for item in profile.employers)
    return [item for item in values if fold_text(item.value)]


def _url_criteria(
    profile: IdentityProfile, result_url: str, result_domain: str
) -> tuple[dict[str, bool], list[_Criterion]]:
    signals: dict[str, bool] = {}
    matches: list[_Criterion] = []
    normalized_domains = {
        (urlsplit(value if "://" in value else f"https://{value}").hostname or "")
        .casefold()
        .rstrip(".")
        for value in profile.domains
    }
    if result_domain.casefold().rstrip(".") in normalized_domains:
        signals["known_domain"] = True
        matches.append(_Criterion("domain", result_domain, "known_domain", "exact_url_host"))
    known_urls: set[str] = set()
    for value in [*profile.websites, *profile.social_profiles, *profile.confirmed_profiles]:
        try:
            known_urls.add(canonicalize_url(value))
        except ValueError:
            continue
    if result_url in known_urls:
        signals["known_profile_url"] = True
        matches.append(
            _Criterion("profile_url", result_url, "known_profile_url", "exact_canonical_url")
        )
    return signals, matches


def _contains(folded_text: str, raw_value: str) -> bool:
    folded_value = fold_text(raw_value)
    if not folded_value:
        return False
    # Avoid partial matches such as a short pseudonym embedded in a larger word,
    # while accepting punctuation around an otherwise exact value.
    return re.search(rf"(?<!\w){re.escape(folded_value)}(?!\w)", folded_text) is not None


def _controlled_approximate_name(
    profile: IdentityProfile,
    folded_text: str,
    signals: dict[str, bool],
) -> _Criterion | None:
    corroborating = {
        "exact_pseudonym",
        "public_email",
        "employer",
        "known_domain",
        "known_profile_url",
    }
    if signals.get("exact_name") or not corroborating.intersection(signals):
        return None
    tokens = re.findall(r"[\w'-]+", folded_text[:MAX_CONTEXT_TEXT_CHARS])[
        :MAX_CONTEXT_TOKENS
    ]
    names = [
        f"{profile.first_name} {profile.last_name}".strip(),
        *(profile.name_variants or []),
    ]
    for raw_name in names:
        target = fold_text(raw_name)
        target_parts = target.split()
        if len(target) < 5 or not target_parts:
            continue
        width = len(target_parts)
        for index in range(len(tokens) - width + 1):
            candidate = " ".join(tokens[index : index + width])
            if candidate == target:
                continue
            if SequenceMatcher(None, target, candidate).ratio() >= APPROXIMATE_NAME_THRESHOLD:
                return _Criterion(
                    "name",
                    raw_name,
                    "approximate_name",
                    "controlled_approximate_text",
                )
    return None


def _assess_context(folded_text: str, signals: dict[str, bool]) -> _ContextAssessment:
    classifications = {
        "organization": (
            "entreprise",
            "societe",
            "association",
            "organization",
            "company",
        ),
        "place_or_street": (
            "commune",
            "municipalite",
            "mairie",
            "rue ",
            "avenue ",
            "street ",
        ),
        "creative_work": ("roman", "film", "livre", "oeuvre", "novel", "painting"),
        "person_profile": ("biographie", "biography", "profil", "profile", "about me"),
    }
    scores = {
        category: sum(folded_text.count(marker) for marker in markers)
        for category, markers in classifications.items()
    }
    page_classification = (
        max(scores, key=lambda category: scores[category])
        if any(scores.values())
        else "unknown"
    )
    risk_flags: list[str] = []
    identity_signals = {key for key, value in signals.items() if value}
    if identity_signals == {"exact_name"}:
        risk_flags.extend(["name_only", "possible_homonym"])
    if page_classification in {"organization", "place_or_street", "creative_work"}:
        risk_flags.append(f"non_person_context:{page_classification}")
    return _ContextAssessment(page_classification, tuple(sorted(risk_flags)))


def _excerpt_around_first_match(text: str, matches: list[_Criterion]) -> str:
    folded = fold_text(text)
    positions = [folded.find(fold_text(item.value)) for item in matches]
    positions = [position for position in positions if position >= 0]
    center = min(positions) if positions else 0
    start = max(center - MAX_EVIDENCE_EXCERPT_CHARS // 2, 0)
    return text[start : start + MAX_EVIDENCE_EXCERPT_CHARS]


def _deduplicate_criteria(criteria: list[_Criterion]) -> list[_Criterion]:
    unique: dict[tuple[str, str], _Criterion] = {}
    for criterion in criteria:
        unique[(criterion.criterion_type, fold_text(criterion.value))] = criterion
    return list(unique.values())


def _criterion_hash(owner_id: str, criterion: _Criterion) -> str:
    material = f"{owner_id}\0{criterion.criterion_type}\0{fold_text(criterion.value)}"
    return hashlib.sha256(material.encode()).hexdigest()


def _criterion_explanation(criterion: _Criterion) -> str:
    labels = {
        "name": "Nom exact présent dans la page",
        "pseudonym": "Pseudonyme exact présent dans la page",
        "email": "Adresse publique exacte présente dans la page",
        "location": "Localisation exacte présente dans la page",
        "profession": "Profession exacte présente dans la page",
        "employer": "Employeur exact présent dans la page",
        "domain": "Domaine du résultat présent dans le profil",
        "profile_url": "URL canonique déjà connue dans le profil",
    }
    if criterion.match_kind == "controlled_approximate_text":
        return "Nom proche détecté avec un autre critère corroborant"
    return labels[criterion.criterion_type]


def _reuse_prior_validation(
    db: Session, result: Result, correlation: IdentityCorrelation
) -> UserValidation | None:
    previous = db.scalar(
        select(UserValidation)
        .join(
            IdentityCorrelation,
            UserValidation.correlation_id == IdentityCorrelation.id,
        )
        .join(Result, IdentityCorrelation.result_id == Result.id)
        .where(
            UserValidation.owner_id == result.owner_id,
            Result.canonical_url == result.canonical_url,
            IdentityCorrelation.id != correlation.id,
        )
        .order_by(UserValidation.updated_at.desc(), UserValidation.id.desc())
        .limit(1)
    )
    if previous is None:
        return None
    reused = UserValidation(
        owner_id=result.owner_id,
        correlation_id=correlation.id,
        decision=previous.decision,
        exclusion_kind=previous.exclusion_kind,
        attributed_profile_id=previous.attributed_profile_id,
        reused_from_validation_id=previous.id,
    )
    db.add(reused)
    apply_validation_status(result, previous.decision)
    return reused


def apply_validation_status(result: Result, decision: str) -> None:
    statuses = {
        "confirmed": VerificationStatus.CONFIRMED,
        "rejected": VerificationStatus.FALSE_POSITIVE,
        "uncertain": VerificationStatus.UNCERTAIN,
    }
    result.verification_status = statuses[decision]
