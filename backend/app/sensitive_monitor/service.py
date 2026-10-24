from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.sensitive_monitor.connectors import LocalMatchCandidate, SensitiveProvider
from app.sensitive_monitor.models import (
    SensitiveAlert,
    SensitiveCheck,
    SensitiveDescriptor,
    SensitiveFinding,
)
from app.sensitive_monitor.types import CheckStatus, FindingStatus, RiskLevel

RECOMMENDATIONS = {
    "payment_card": "Faire opposition auprès de la banque et contrôler les opérations.",
    "iban": "Contacter la banque et surveiller les prélèvements non autorisés.",
    "nir": "Contacter l'organisme compétent et renforcer la vigilance aux fraudes.",
    "phone": "Renforcer la sécurité de l'opérateur et se méfier du hameçonnage.",
    "postal_address": "Vérifier les courriers et signaler toute utilisation frauduleuse.",
    "id_document": "Signaler la perte ou l'usage frauduleux aux autorités compétentes.",
}


class SensitiveMonitorService:
    async def run_local_provider(
        self,
        descriptor: SensitiveDescriptor,
        provider: SensitiveProvider,
        db: Session,
    ) -> SensitiveCheck:
        metadata = provider.metadata
        if metadata.external_transmission:
            raise ValueError("Un fournisseur externe exige un flux de consentement dédié")
        if descriptor.category not in metadata.categories:
            raise ValueError("Catégorie non prise en charge par ce fournisseur")
        check = SensitiveCheck(
            owner_id=descriptor.owner_id,
            descriptor_id=descriptor.id,
            category=descriptor.category,
            provider_id=metadata.identifier,
            external_transmission=False,
        )
        db.add(check)
        db.flush()
        try:
            matched = await provider.check_local(
                LocalMatchCandidate(
                    fingerprint=descriptor.fingerprint,
                    source_label=metadata.identifier,
                )
            )
        except Exception:  # Le détail fournisseur ne doit pas fuiter dans la base ou l'API.
            check.status = CheckStatus.FAILED
            check.error_code = "provider_failure"
            check.completed_at = datetime.now(UTC)
            db.commit()
            return check
        check.status = CheckStatus.COMPLETED
        check.completed_at = datetime.now(UTC)
        if matched:
            recommendation = RECOMMENDATIONS[descriptor.category.value]
            finding = SensitiveFinding(
                owner_id=descriptor.owner_id,
                check_id=check.id,
                category=descriptor.category,
                source_label=metadata.identifier,
                risk_level=RiskLevel.HIGH,
                verification_status=FindingStatus.CONFIRMED,
                recommendation=recommendation,
            )
            db.add(finding)
            db.flush()
            db.add(
                SensitiveAlert(
                    owner_id=descriptor.owner_id,
                    finding_id=finding.id,
                    category=descriptor.category,
                    source_label=metadata.identifier,
                    risk_level=RiskLevel.HIGH,
                    recommendation=recommendation,
                )
            )
        db.commit()
        return check
