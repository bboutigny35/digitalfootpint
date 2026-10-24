from app.connectors.base import (
    CandidateResult,
    Connector,
    ConnectorMetadata,
    IdentifierType,
    IdentitySnapshot,
)


class MockConnector(Connector):
    """Connecteur hermétique pour tests uniquement ; jamais enregistré en production."""

    metadata = ConnectorMetadata(
        identifier="mock",
        version="1.0",
        capabilities=("profiles",),
        accepted_identifiers=(IdentifierType.PSEUDONYM,),
    )

    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        if not identity.pseudonyms:
            return []
        pseudonym = identity.pseudonyms[0]
        return [
            CandidateResult(
                url=f"https://public.example.test/users/{pseudonym}",
                title=f"Profil public de {pseudonym}",
                snippet="Résultat simulé réservé aux tests automatisés.",
                match_type="pseudonym",
                signals={"exact_pseudonym": True},
            )
        ]
