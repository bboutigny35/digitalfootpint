from app.models.entities import RemovalRequest, Result


def prepare_removal_letter(request: RemovalRequest, result: Result | None) -> tuple[str, str]:
    subject = "Demande d'effacement de données personnelles"
    reference = (
        result.canonical_url
        if result
        else "la ressource concernée indiquée dans mon dossier"
    )
    body = (
        f"À l'attention de {request.organization},\n\n"
        "Je vous demande l'effacement des données personnelles me concernant, "
        "conformément à l'article 17 du règlement général sur la protection des données.\n\n"
        f"Ressource concernée : {reference}\n\n"
        "Merci de m'informer des suites données à cette demande dans les délais applicables.\n\n"
        "Cordialement"
    )
    return subject, body
