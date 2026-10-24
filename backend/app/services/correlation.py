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
