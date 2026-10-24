from dataclasses import dataclass
from enum import StrEnum

from app.models.entities import Result, VerificationStatus


class ComparisonCategory(StrEnum):
    NEW = "new"
    KNOWN = "known"
    MODIFIED = "modified"
    INACCESSIBLE = "inaccessible"
    NOT_REVERIFIED = "not_reverified"
    EXCLUDED_FALSE_POSITIVE = "excluded_false_positive"


@dataclass(frozen=True)
class ComparisonItem:
    category: ComparisonCategory
    canonical_url: str
    domain: str
    connector_id: str
    title: str
    baseline_result_id: str | None
    current_result_id: str | None
    changed_fields: tuple[str, ...] = ()


_COMPARABLE_FIELDS = ("connector_id", "domain", "title", "snippet", "match_type")


def compare_results(baseline: list[Result], current: list[Result]) -> list[ComparisonItem]:
    """Compare deux instantanés sans déduire une suppression d'une simple absence."""
    baseline_by_url = {result.canonical_url: result for result in baseline}
    current_by_url = {result.canonical_url: result for result in current}
    items: list[ComparisonItem] = []

    for url in sorted(baseline_by_url.keys() | current_by_url.keys()):
        previous = baseline_by_url.get(url)
        latest = current_by_url.get(url)
        representative = latest or previous
        assert representative is not None

        if any(
            result is not None
            and result.verification_status == VerificationStatus.FALSE_POSITIVE
            for result in (previous, latest)
        ):
            category = ComparisonCategory.EXCLUDED_FALSE_POSITIVE
            changed_fields: tuple[str, ...] = ()
        elif previous is None:
            category = ComparisonCategory.NEW
            changed_fields = ()
        elif latest is None:
            # L'absence du résultat ne prouve ni une suppression ni une inaccessibilité.
            category = ComparisonCategory.NOT_REVERIFIED
            changed_fields = ()
        else:
            changed_fields = tuple(
                field
                for field in _COMPARABLE_FIELDS
                if getattr(previous, field) != getattr(latest, field)
            )
            category = (
                ComparisonCategory.MODIFIED if changed_fields else ComparisonCategory.KNOWN
            )

        items.append(
            ComparisonItem(
                category=category,
                canonical_url=url,
                domain=representative.domain,
                connector_id=representative.connector_id,
                title=representative.title,
                baseline_result_id=previous.id if previous else None,
                current_result_id=latest.id if latest else None,
                changed_fields=changed_fields,
            )
        )
    return items
