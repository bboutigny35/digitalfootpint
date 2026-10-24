from dataclasses import dataclass


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
